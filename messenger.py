"""Messenger module - Auto-revision and client communication.

Monitors assignment messages and responds automatically:
  - Revision requests -> generates updated deliverable with AI
  - Questions -> answers using AI
  - Thanks/approval -> responds professionally

Tracks which messages have been processed to avoid duplicate responses.
"""

import logging
from typing import Optional

from market_client import MarketClient
from brain import generate_revision_response, is_ai_enabled

logger = logging.getLogger("messenger")

# Track processed messages to avoid duplicate responses
_processed_messages: set[str] = set()


def check_and_respond(client: MarketClient, job: dict) -> Optional[str]:
    """Check for new client messages on a job and respond if needed.

    Returns the response text if a reply was sent, None otherwise.
    """
    assignments = job.get("my_assignments", [])
    if not assignments:
        return None

    for assignment in assignments:
        aid = assignment.get("assignment_id")
        if not aid:
            continue

        # Only respond on active assignments
        status = assignment.get("status", "")
        if status not in ("in_progress", "submitted", "accepted"):
            continue

        try:
            messages = client.read_assignment_messages(aid)
        except Exception as e:
            logger.warning("Failed to read messages for %s: %s", aid, e)
            continue

        if not messages:
            continue

        # Find unprocessed messages from the client (not from us)
        our_agent_id = job.get("worker_agent_id", "")
        new_messages = []
        for msg in messages:
            msg_id = msg.get("message_id", "")
            sender = msg.get("sender_agent_id", "")

            if msg_id in _processed_messages:
                continue
            if sender == our_agent_id:
                _processed_messages.add(msg_id)
                continue

            new_messages.append(msg)
            _processed_messages.add(msg_id)

        if not new_messages:
            continue

        # Process the latest client message
        latest = new_messages[-1]
        client_msg = latest.get("body", "")
        if not client_msg.strip():
            continue

        logger.info(
            "New message on '%s': %s",
            job.get("title", "?")[:40],
            client_msg[:100],
        )

        # Generate a response
        response = _generate_response(job, client_msg, assignment)
        if not response:
            continue

        # Send the response
        try:
            client.send_assignment_message(aid, response)
            logger.info(
                "Auto-replied on '%s' (%d chars)",
                job.get("title", "?")[:40],
                len(response),
            )
            return response
        except Exception as e:
            logger.error("Failed to send reply: %s", e)

    return None


def _generate_response(
    job: dict, client_message: str, assignment: dict
) -> Optional[str]:
    """Generate an appropriate response to a client message."""
    # Use AI if available
    if is_ai_enabled():
        deliverable = assignment.get("deliverable", "")
        response = generate_revision_response(job, client_message, deliverable)
        if response:
            return response

    # Template fallback for common patterns
    msg_lower = client_message.lower()

    if any(w in msg_lower for w in ["revision", "change", "update", "modify", "fix"]):
        return (
            f"Got your revision request. I'm working on the updates now and "
            f"will resubmit shortly. Thanks for the feedback!"
        )
    elif any(w in msg_lower for w in ["thank", "great", "perfect", "approved", "love"]):
        return (
            "Thanks! Glad the deliverable meets your expectations. "
            "Let me know if you need anything else."
        )
    elif "?" in client_message:
        return (
            "Good question — let me look into this and get back to you "
            "with a detailed answer shortly."
        )
    else:
        return (
            "Thanks for the message. I've noted your feedback and will "
            "incorporate it. Let me know if there's anything specific "
            "you'd like me to prioritize."
        )
