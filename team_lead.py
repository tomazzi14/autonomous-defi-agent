"""Team Lead Engine - Delegates complex jobs to other agents on the marketplace."""

import logging
from config import DELEGATION_MIN_BUDGET, DELEGATION_BUDGET_RATIO

logger = logging.getLogger("team_lead")


def should_delegate(job: dict) -> bool:
    """Decide if a job is complex enough to warrant delegation."""
    budget = float(job.get("budget_amount") or 0)
    if budget < DELEGATION_MIN_BUDGET:
        return False

    desc = job.get("description", "").lower()
    tags = [t.lower() for t in job.get("tags", [])]

    # Complex jobs that benefit from delegation
    complexity_signals = [
        "full-stack" in desc or "fullstack" in desc,
        "frontend" in desc and "backend" in desc,
        "smart contract" in desc and ("frontend" in desc or "ui" in desc),
        "audit" in desc and "fix" in desc,
        len(desc) > 3000,  # Very detailed spec = complex job
        any(t in tags for t in ["fullstack", "dapp"]) and budget >= 10,
    ]

    return sum(complexity_signals) >= 2


def plan_subtasks(job: dict) -> list[dict]:
    """Break a complex job into sub-tasks for delegation.

    Returns a list of sub-task definitions that can be posted as new jobs.
    """
    title = job.get("title", "")
    desc = job.get("description", "")
    budget = float(job.get("budget_amount") or 0)
    text = f"{title} {desc}".lower()

    subtasks = []
    sub_budget = budget * DELEGATION_BUDGET_RATIO

    # Detect what components the job needs
    needs_contract = any(kw in text for kw in ["solidity", "smart contract", "erc", "token", "hook"])
    needs_frontend = any(kw in text for kw in ["frontend", "nextjs", "react", "ui", "dashboard"])
    needs_tests = any(kw in text for kw in ["test", "foundry", "coverage"])
    needs_audit = any(kw in text for kw in ["audit", "security", "review"])
    needs_docs = any(kw in text for kw in ["documentation", "readme", "docs"])

    task_count = sum([needs_contract, needs_frontend, needs_tests, needs_audit, needs_docs])
    if task_count == 0:
        return []

    per_task_budget = sub_budget / max(task_count, 1)

    if needs_frontend:
        subtasks.append({
            "title": f"[Sub-task] Frontend for: {title[:80]}",
            "description": (
                f"Build the frontend component for this project.\n\n"
                f"Parent job context: {desc[:500]}\n\n"
                f"Requirements:\n"
                f"- Next.js + TypeScript\n"
                f"- Responsive design (Tailwind CSS)\n"
                f"- Wallet connection (wagmi/RainbowKit)\n"
                f"- Clean, documented code\n\n"
                f"Deliverable: GitHub gist or repo with source code."
            ),
            "tags": ["frontend", "nextjs", "react", "typescript", "web3"],
            "budget_amount": f"{per_task_budget:.1f}",
            "deadline_seconds": 43200,  # 12 hours
            "type": "delegate",
        })

    if needs_tests:
        subtasks.append({
            "title": f"[Sub-task] Test suite for: {title[:80]}",
            "description": (
                f"Write comprehensive Foundry tests for this contract.\n\n"
                f"Parent job context: {desc[:500]}\n\n"
                f"Requirements:\n"
                f"- Foundry test suite (forge test)\n"
                f"- Edge case coverage\n"
                f"- Gas benchmarks\n\n"
                f"Deliverable: Test file(s) ready to run with `forge test`."
            ),
            "tags": ["foundry", "testing", "solidity", "smart-contracts"],
            "budget_amount": f"{per_task_budget:.1f}",
            "deadline_seconds": 43200,
            "type": "delegate",
        })

    if needs_docs:
        subtasks.append({
            "title": f"[Sub-task] Documentation for: {title[:80]}",
            "description": (
                f"Write technical documentation for this project.\n\n"
                f"Parent job context: {desc[:500]}\n\n"
                f"Requirements:\n"
                f"- README.md with setup instructions\n"
                f"- API/function documentation\n"
                f"- Architecture overview\n\n"
                f"Deliverable: Markdown documentation."
            ),
            "tags": ["documentation", "technical-writing", "markdown"],
            "budget_amount": f"{per_task_budget:.1f}",
            "deadline_seconds": 43200,
            "type": "delegate",
        })

    logger.info(
        "Planned %d sub-tasks for job '%s' (sub-budget: %.1f NEAR)",
        len(subtasks), title[:40], sub_budget,
    )

    return subtasks


def format_combined_deliverable(
    main_work: str, subtask_results: list[dict]
) -> str:
    """Combine main work with delegated sub-task results."""
    parts = [main_work, "\n\n---\n\n## Delegated Components\n"]

    for i, result in enumerate(subtask_results, 1):
        parts.append(f"\n### Sub-task {i}: {result.get('title', 'Untitled')}\n")
        parts.append(f"**Worker:** {result.get('worker', 'agent')}\n")
        parts.append(f"**Status:** {result.get('status', 'pending')}\n")
        if result.get("deliverable"):
            parts.append(f"\n{result['deliverable'][:2000]}\n")

    parts.append(
        "\n---\n*Orchestrated by defi_builder - "
        "DeFi Agent with Team Lead capabilities*\n"
    )

    return "\n".join(parts)
