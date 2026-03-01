"""Full API client for market.near.ai with SSE support."""

import httpx
import json
import logging
from typing import Optional, Generator

from config import API_KEY, BASE_URL, SSE_URL

logger = logging.getLogger("market_client")


class MarketClient:
    """Handles all API communication with market.near.ai."""

    def __init__(self):
        self.client = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30.0,
        )

    def close(self):
        self.client.close()

    # ── Jobs ──────────────────────────────────────────────

    def list_jobs(
        self,
        status: str = "open",
        tags: Optional[str] = None,
        search: Optional[str] = None,
        sort: str = "created_at",
        order: str = "desc",
        limit: int = 50,
    ) -> list[dict]:
        params = {"status": status, "sort": sort, "order": order, "limit": limit}
        if tags:
            params["tags"] = tags
        if search:
            params["search"] = search
        resp = self.client.get("/jobs", params=params)
        resp.raise_for_status()
        return resp.json()

    def get_job(self, job_id: str) -> dict:
        resp = self.client.get(f"/jobs/{job_id}")
        resp.raise_for_status()
        return resp.json()

    def create_job(
        self,
        title: str,
        description: str,
        tags: list[str],
        budget_amount: Optional[str] = None,
        deadline_seconds: int = 86400,
    ) -> dict:
        body = {
            "title": title,
            "description": description,
            "tags": tags,
            "deadline_seconds": deadline_seconds,
        }
        if budget_amount:
            body["budget_amount"] = budget_amount
            body["budget_token"] = "NEAR"
        resp = self.client.post("/jobs", json=body)
        resp.raise_for_status()
        return resp.json()

    def cancel_job(self, job_id: str) -> dict:
        resp = self.client.post(f"/jobs/{job_id}/cancel")
        resp.raise_for_status()
        return resp.json()

    def award_job(self, job_id: str, bid_id: str) -> dict:
        resp = self.client.post(f"/jobs/{job_id}/award", json={"bid_id": bid_id})
        resp.raise_for_status()
        return resp.json()

    def accept_work(self, job_id: str) -> dict:
        resp = self.client.post(f"/jobs/{job_id}/accept")
        resp.raise_for_status()
        return resp.json()

    # ── Bids ──────────────────────────────────────────────

    def place_bid(
        self, job_id: str, amount: str, eta_seconds: int, proposal: str
    ) -> dict:
        resp = self.client.post(
            f"/jobs/{job_id}/bids",
            json={
                "amount": amount,
                "eta_seconds": eta_seconds,
                "proposal": proposal,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def my_bids(self) -> list[dict]:
        resp = self.client.get("/agents/me/bids")
        resp.raise_for_status()
        return resp.json()

    def list_job_bids(self, job_id: str) -> list[dict]:
        resp = self.client.get(f"/jobs/{job_id}/bids")
        resp.raise_for_status()
        return resp.json()

    # ── Work ──────────────────────────────────────────────

    def submit_deliverable(
        self, job_id: str, deliverable: str, deliverable_hash: str = ""
    ) -> dict:
        body = {"deliverable": deliverable}
        if deliverable_hash:
            body["deliverable_hash"] = deliverable_hash
        resp = self.client.post(f"/jobs/{job_id}/submit", json=body)
        resp.raise_for_status()
        return resp.json()

    # ── Messaging ─────────────────────────────────────────

    def send_assignment_message(self, assignment_id: str, body: str) -> dict:
        resp = self.client.post(
            f"/assignments/{assignment_id}/messages", json={"body": body}
        )
        resp.raise_for_status()
        return resp.json()

    def read_assignment_messages(self, assignment_id: str) -> list[dict]:
        resp = self.client.get(f"/assignments/{assignment_id}/messages")
        resp.raise_for_status()
        return resp.json()

    # ── Profile & Wallet ──────────────────────────────────

    def my_profile(self) -> dict:
        resp = self.client.get("/agents/me")
        resp.raise_for_status()
        return resp.json()

    def wallet_balance(self) -> dict:
        resp = self.client.get("/wallet/balance")
        resp.raise_for_status()
        return resp.json()

    # ── SSE Feed ──────────────────────────────────────────

    def stream_feed(self) -> Generator[dict, None, None]:
        """Connect to the SSE feed and yield events in real-time."""
        with httpx.stream("GET", SSE_URL, timeout=None) as response:
            buffer = ""
            for chunk in response.iter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)
                    event = self._parse_sse(event_block)
                    if event:
                        yield event

    @staticmethod
    def _parse_sse(block: str) -> Optional[dict]:
        """Parse a single SSE event block."""
        data_lines = []
        for line in block.strip().split("\n"):
            if line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            raw = "\n".join(data_lines)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None
