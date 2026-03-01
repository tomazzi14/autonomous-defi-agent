"""Sniper Mode - Real-time SSE listener for instant job bidding."""

import logging
import threading
import time

from market_client import MarketClient
from skills import score_job, calculate_bid_amount, estimate_eta, generate_proposal

logger = logging.getLogger("sniper")


class Sniper:
    """Listens to the SSE feed and bids on matching jobs in real-time."""

    def __init__(self, client: MarketClient, jobs_bid_on: set):
        self.client = client
        self.jobs_bid_on = jobs_bid_on
        self._running = False
        self._thread = None

    def start(self):
        """Start the sniper in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info("Sniper started - listening for new jobs in real-time...")

    def stop(self):
        """Stop the sniper."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Sniper stopped.")

    def _listen(self):
        """Main SSE listener loop with auto-reconnect."""
        while self._running:
            try:
                logger.info("Connecting to SSE feed...")
                for event in self.client.stream_feed():
                    if not self._running:
                        break
                    self._handle_event(event)
            except Exception as e:
                logger.warning("SSE connection lost: %s. Reconnecting in 10s...", e)
                time.sleep(10)

    def _handle_event(self, event: dict):
        """Process an SSE event."""
        event_type = event.get("event_type", "")

        if event_type == "job_created":
            job_id = event.get("job_id")
            title = event.get("job_title", "?")
            budget = event.get("budget", "?")
            logger.info("[SSE] New job: '%s' (%s) - id=%s", title, budget, job_id)
            self._snipe_job(job_id)

        elif event_type == "job_awarded":
            worker = event.get("worker_account_id", "?")
            title = event.get("job_title", "?")
            logger.info("[SSE] Job awarded: '%s' to %s", title, worker[:16])

        elif event_type == "job_completed":
            title = event.get("job_title", "?")
            logger.info("[SSE] Job completed: '%s'", title)

    def _snipe_job(self, job_id: str):
        """Evaluate and instantly bid on a new job."""
        if not job_id or job_id in self.jobs_bid_on:
            return

        try:
            job = self.client.get_job(job_id)
        except Exception as e:
            logger.warning("Could not fetch job %s: %s", job_id, e)
            return

        score = score_job(job)
        if score < 0.2:
            logger.info("  -> Score %.2f too low, skipping.", score)
            return

        bid_amount = calculate_bid_amount(job)
        eta = estimate_eta(job)
        proposal = generate_proposal(job)

        try:
            result = self.client.place_bid(
                job_id=job_id,
                amount=bid_amount,
                eta_seconds=eta,
                proposal=proposal,
            )
            self.jobs_bid_on.add(job_id)
            logger.info(
                "  -> SNIPED! Bid %s NEAR on '%s' (score=%.2f) | bid_id=%s",
                bid_amount, job.get("title", "?")[:40], score, result.get("bid_id", "?"),
            )
        except Exception as e:
            logger.warning("  -> Failed to snipe: %s", e)
