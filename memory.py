"""Memory module - Persistent job tracking and learning.

Tracks:
  - Jobs bid on, won, lost, delivered
  - Which proposals/approaches worked
  - Earnings over time
  - Client feedback patterns

Stores everything in a local JSON file for persistence across restarts.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger("memory")

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "agent_memory.json")


def _load() -> dict:
    """Load memory from disk."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Memory file corrupted, starting fresh")
    return {
        "bids": {},
        "wins": [],
        "losses": [],
        "deliveries": [],
        "earnings": 0.0,
        "stats": {
            "total_bids": 0,
            "total_wins": 0,
            "total_deliveries": 0,
            "win_rate": 0.0,
        },
        "tag_performance": {},
    }


def _save(data: dict):
    """Save memory to disk."""
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
    except IOError as e:
        logger.error("Failed to save memory: %s", e)


def record_bid(job_id: str, job: dict, bid_amount: str, proposal: str):
    """Record a bid we placed."""
    data = _load()
    data["bids"][job_id] = {
        "title": job.get("title", ""),
        "tags": job.get("tags", []),
        "budget": job.get("budget_amount"),
        "bid_amount": bid_amount,
        "proposal_snippet": proposal[:200],
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
    }
    data["stats"]["total_bids"] += 1
    _save(data)


def record_win(job_id: str, job: dict):
    """Record a won bid."""
    data = _load()
    data["wins"].append({
        "job_id": job_id,
        "title": job.get("title", ""),
        "tags": job.get("tags", []),
        "budget": job.get("budget_amount"),
        "timestamp": datetime.now().isoformat(),
    })
    data["stats"]["total_wins"] += 1

    # Update bid status
    if job_id in data["bids"]:
        data["bids"][job_id]["status"] = "won"

    # Track winning tags
    for tag in job.get("tags", []):
        tag = tag.lower()
        if tag not in data["tag_performance"]:
            data["tag_performance"][tag] = {"bids": 0, "wins": 0}
        data["tag_performance"][tag]["wins"] += 1

    _update_win_rate(data)
    _save(data)
    logger.info("Memory: Recorded WIN for '%s'", job.get("title", "?")[:50])


def record_delivery(job_id: str, job: dict, earning: float):
    """Record a successful delivery."""
    data = _load()
    data["deliveries"].append({
        "job_id": job_id,
        "title": job.get("title", ""),
        "earning": earning,
        "timestamp": datetime.now().isoformat(),
    })
    data["earnings"] += earning
    data["stats"]["total_deliveries"] += 1

    if job_id in data["bids"]:
        data["bids"][job_id]["status"] = "delivered"

    _save(data)
    logger.info(
        "Memory: Delivered '%s' (+%.1f NEAR, total: %.1f NEAR)",
        job.get("title", "?")[:50], earning, data["earnings"],
    )


def record_loss(job_id: str):
    """Record a lost/expired bid."""
    data = _load()
    if job_id in data["bids"]:
        data["bids"][job_id]["status"] = "lost"
        data["losses"].append({
            "job_id": job_id,
            "title": data["bids"][job_id].get("title", ""),
            "timestamp": datetime.now().isoformat(),
        })

    # Track losing tags
    bid_info = data["bids"].get(job_id, {})
    for tag in bid_info.get("tags", []):
        tag = tag.lower()
        if tag not in data["tag_performance"]:
            data["tag_performance"][tag] = {"bids": 0, "wins": 0}
        data["tag_performance"][tag]["bids"] += 1

    _update_win_rate(data)
    _save(data)


def get_stats() -> dict:
    """Get current agent statistics."""
    data = _load()
    return {
        "total_bids": data["stats"]["total_bids"],
        "total_wins": data["stats"]["total_wins"],
        "total_deliveries": data["stats"]["total_deliveries"],
        "win_rate": data["stats"]["win_rate"],
        "earnings": data["earnings"],
        "top_tags": _get_top_tags(data),
    }


def was_bid_on(job_id: str) -> bool:
    """Check if we already bid on this job (persistent check)."""
    data = _load()
    return job_id in data["bids"]


def get_winning_tags() -> list[str]:
    """Return tags sorted by win rate — helps prioritize future bids."""
    data = _load()
    tag_perf = data.get("tag_performance", {})
    scored = []
    for tag, stats in tag_perf.items():
        if stats["bids"] > 0:
            rate = stats["wins"] / stats["bids"]
            scored.append((rate, tag))
    scored.sort(reverse=True)
    return [tag for _, tag in scored[:10]]


def _get_top_tags(data: dict) -> list[dict]:
    """Get top performing tags."""
    tag_perf = data.get("tag_performance", {})
    scored = []
    for tag, stats in tag_perf.items():
        total = stats.get("bids", 0) + stats.get("wins", 0)
        if total > 0:
            scored.append({
                "tag": tag,
                "wins": stats.get("wins", 0),
                "bids": stats.get("bids", 0),
            })
    scored.sort(key=lambda x: x["wins"], reverse=True)
    return scored[:5]


def _update_win_rate(data: dict):
    """Recalculate win rate."""
    total = data["stats"]["total_bids"]
    wins = data["stats"]["total_wins"]
    data["stats"]["win_rate"] = round(wins / total, 2) if total > 0 else 0.0
