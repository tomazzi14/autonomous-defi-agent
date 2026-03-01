"""
NEAR Agent Market - Autonomous DeFi Agent
==========================================
An agent that combines three strategies:
  1. SNIPER  - Real-time SSE listener, bids in < 5 seconds
  2. CODE GEN - Generates real Solidity contracts as deliverables
  3. TEAM LEAD - Delegates complex jobs to other agents

Usage:
    python agent.py              # Run one cycle (poll + deliver)
    python agent.py --sniper     # Real-time SSE mode + polling
    python agent.py --status     # Check current status
    python agent.py --demo       # Run a demo cycle with verbose logging
"""

import argparse
import logging
import time
from datetime import datetime

from market_client import MarketClient
from skills import score_job, calculate_bid_amount, estimate_eta, generate_proposal
from code_generator import generate_solidity
from team_lead import should_delegate, plan_subtasks, format_combined_deliverable
from sniper import Sniper
from config import POLL_INTERVAL, MAX_BIDS_PER_CYCLE

# ── Logging ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent.log"),
    ],
)
logger = logging.getLogger("agent")


class DeFiAgent:
    """Autonomous DeFi agent with Sniper, Code Gen, and Team Lead modes."""

    def __init__(self):
        self.client = MarketClient()
        self.jobs_bid_on: set[str] = set()
        self.sniper = Sniper(self.client, self.jobs_bid_on)
        self.delegated_jobs: dict[str, dict] = {}

    # ── Main Cycle ────────────────────────────────────────

    def run_cycle(self):
        """One full cycle: status -> find -> bid -> check wins -> deliver."""
        logger.info("=" * 60)
        logger.info("CYCLE START: %s", datetime.now().isoformat())
        logger.info("=" * 60)

        self._log_status()
        self._find_and_bid()
        self._check_accepted_bids()
        self._check_delegated_work()

        logger.info("CYCLE END\n")

    # ── Status ────────────────────────────────────────────

    def _log_status(self):
        try:
            profile = self.client.my_profile()
            balance = self.client.wallet_balance()
            logger.info(
                "Agent: %s | Earned: %s NEAR | Rep: %s/100 | Stars: %s",
                profile.get("handle", "?"),
                profile.get("total_earned", "0"),
                profile.get("reputation_score", 0),
                profile.get("reputation_stars", 0),
            )
            logger.info("Balance: %s", balance)
        except Exception as e:
            logger.warning("Status check failed: %s", e)

    # ── Find & Bid ────────────────────────────────────────

    def _find_and_bid(self):
        logger.info("Searching for open jobs...")
        try:
            jobs = self.client.list_jobs(status="open", limit=50)
        except Exception as e:
            logger.error("Failed to fetch jobs: %s", e)
            return

        logger.info("Found %d open jobs. Scoring...", len(jobs))

        scored = []
        for job in jobs:
            if job["job_id"] in self.jobs_bid_on:
                continue
            score = score_job(job)
            if score > 0.2:
                scored.append((score, job))

        scored.sort(key=lambda x: x[0], reverse=True)
        logger.info("Matched %d jobs (score > 0.2)", len(scored))

        bids_placed = 0
        for score, job in scored:
            if bids_placed >= MAX_BIDS_PER_CYCLE:
                break

            job_id = job["job_id"]
            title = job.get("title", "?")[:60]
            budget = job.get("budget_amount", "?")

            logger.info(
                "  [%.2f] '%s' (budget: %s NEAR, %d bids)",
                score, title, budget, job.get("bid_count", 0),
            )

            bid_amount = calculate_bid_amount(job)
            eta = estimate_eta(job)
            proposal = generate_proposal(job)

            if should_delegate(job):
                proposal += (
                    " For complex projects, I can orchestrate sub-tasks "
                    "across the marketplace for parallel delivery."
                )

            try:
                result = self.client.place_bid(
                    job_id=job_id,
                    amount=bid_amount,
                    eta_seconds=eta,
                    proposal=proposal,
                )
                self.jobs_bid_on.add(job_id)
                bids_placed += 1
                logger.info(
                    "    -> BID: %s NEAR, ETA %dh | bid_id=%s",
                    bid_amount, eta // 3600, result.get("bid_id", "?"),
                )
            except Exception as e:
                logger.warning("    -> Bid failed: %s", e)

        if bids_placed == 0:
            logger.info("No new bids this cycle.")

    # ── Check Wins & Deliver ──────────────────────────────

    def _check_accepted_bids(self):
        logger.info("Checking accepted bids...")
        try:
            bids = self.client.my_bids()
        except Exception as e:
            logger.error("Failed to fetch bids: %s", e)
            return

        accepted = [b for b in bids if b.get("status") == "accepted"]
        pending = [b for b in bids if b.get("status") == "pending"]
        logger.info("Bids: %d accepted, %d pending", len(accepted), len(pending))

        for bid in accepted:
            job_id = bid["job_id"]
            try:
                job = self.client.get_job(job_id)
            except Exception as e:
                logger.error("Failed to fetch job %s: %s", job_id, e)
                continue

            my_assignments = job.get("my_assignments", [])
            if any(a.get("status") in ("submitted", "accepted") for a in my_assignments):
                continue

            title = job.get("title", "?")
            logger.info("WON: '%s' - Starting work...", title)

            if should_delegate(job):
                self._delegate_job(job)
            else:
                self._complete_job(job)

    def _complete_job(self, job: dict):
        """Generate code and submit deliverable."""
        job_id = job["job_id"]
        title = job.get("title", "?")

        logger.info("  Generating Solidity code for: %s", title[:50])
        deliverable = generate_solidity(job)

        try:
            self.client.submit_deliverable(job_id=job_id, deliverable=deliverable)
            logger.info("  DELIVERED: %s", title[:50])
        except Exception as e:
            logger.error("  Delivery failed: %s", e)
            return

        my_assignments = job.get("my_assignments", [])
        if my_assignments:
            aid = my_assignments[0].get("assignment_id")
            if aid:
                try:
                    self.client.send_assignment_message(
                        aid,
                        f"Deliverable submitted for '{title}'. "
                        f"Includes working Solidity code with docs. "
                        f"Let me know if you need revisions!",
                    )
                except Exception:
                    pass

    # ── Team Lead: Delegation ─────────────────────────────

    def _delegate_job(self, job: dict):
        """Break a complex job into sub-tasks and post them."""
        job_id = job["job_id"]
        title = job.get("title", "?")
        logger.info("  TEAM LEAD: Delegating sub-tasks for '%s'", title[:50])

        subtasks = plan_subtasks(job)
        if not subtasks:
            self._complete_job(job)
            return

        logger.info("  Generating core deliverable ourselves...")
        main_work = generate_solidity(job)

        posted = []
        for task in subtasks:
            try:
                result = self.client.create_job(
                    title=task["title"],
                    description=task["description"],
                    tags=task["tags"],
                    budget_amount=task.get("budget_amount"),
                    deadline_seconds=task.get("deadline_seconds", 43200),
                )
                posted.append({
                    "job_id": result["job_id"],
                    "title": task["title"],
                    "status": "open",
                })
                logger.info(
                    "  Posted sub-task: '%s' (%s NEAR)",
                    task["title"][:50], task.get("budget_amount", "?"),
                )
            except Exception as e:
                logger.warning("  Failed to post sub-task: %s", e)

        self.delegated_jobs[job_id] = {
            "main_work": main_work,
            "subtasks": posted,
            "parent_job": job,
        }

        if not posted:
            self._complete_job(job)

    def _check_delegated_work(self):
        """Check if delegated sub-tasks are complete."""
        if not self.delegated_jobs:
            return

        logger.info("Checking %d delegated job(s)...", len(self.delegated_jobs))

        for parent_id, info in list(self.delegated_jobs.items()):
            all_done = True
            results = []

            for subtask in info["subtasks"]:
                try:
                    sub_job = self.client.get_job(subtask["job_id"])
                    status = sub_job.get("status", "open")
                    subtask["status"] = status

                    if status == "completed":
                        results.append({
                            "title": subtask["title"],
                            "status": "completed",
                            "deliverable": sub_job.get("deliverable", ""),
                            "worker": sub_job.get("worker_agent_id", "agent"),
                        })
                    elif status in ("open", "filling", "in_progress"):
                        all_done = False
                except Exception:
                    all_done = False

            if all_done:
                combined = format_combined_deliverable(info["main_work"], results)
                try:
                    self.client.submit_deliverable(
                        job_id=parent_id, deliverable=combined
                    )
                    logger.info(
                        "  DELIVERED (with team): '%s'",
                        info["parent_job"].get("title", "?")[:50],
                    )
                except Exception as e:
                    logger.error("  Combined delivery failed: %s", e)
                del self.delegated_jobs[parent_id]

    # ── Status Display ────────────────────────────────────

    def print_status(self):
        profile = self.client.my_profile()
        balance = self.client.wallet_balance()
        bids = self.client.my_bids()

        accepted = [b for b in bids if b["status"] == "accepted"]
        pending = [b for b in bids if b["status"] == "pending"]

        print("\n" + "=" * 55)
        print("  defi_builder - Autonomous DeFi Agent")
        print("=" * 55)
        print(f"  Handle:      {profile.get('handle', '?')}")
        print(f"  Earned:      {profile.get('total_earned', '0')} NEAR")
        print(f"  Reputation:  {profile.get('reputation_score', 0)}/100")
        print(f"  Stars:       {profile.get('reputation_stars', 0)}/5.0")
        print(f"  Balance:     {balance}")
        print(f"  Bids:        {len(pending)} pending, {len(accepted)} accepted")
        print(f"  Total bids:  {profile.get('bids_placed', 0)}")
        print(f"  Jobs done:   {profile.get('jobs_completed', 0)}")
        print(f"  Features:    Sniper + Code Gen + Team Lead")
        print("=" * 55 + "\n")

    def run_with_sniper(self):
        """Run in sniper mode: SSE real-time + periodic polling."""
        logger.info("Starting in SNIPER mode (SSE + polling every %ds)", POLL_INTERVAL)
        self.sniper.start()
        try:
            while True:
                self.run_cycle()
                logger.info("Next poll in %d seconds...\n", POLL_INTERVAL)
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.sniper.stop()
            self.client.close()


def main():
    parser = argparse.ArgumentParser(description="defi_builder - NEAR Agent Market")
    parser.add_argument("--sniper", action="store_true", help="SSE real-time + polling")
    parser.add_argument("--status", action="store_true", help="Show agent status")
    parser.add_argument("--demo", action="store_true", help="Run demo cycle (verbose)")
    args = parser.parse_args()

    agent = DeFiAgent()

    if args.status:
        agent.print_status()
    elif args.demo:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("DEMO MODE - Running one verbose cycle...")
        agent.run_cycle()
        agent.print_status()
    elif args.sniper:
        agent.run_with_sniper()
    else:
        agent.run_cycle()

    agent.client.close()


if __name__ == "__main__":
    main()
