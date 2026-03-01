#!/usr/bin/env python3
"""Test script for the upgraded agent modules.

Tests each module independently without touching the real marketplace API.

Usage:
    python test_brain.py              # Test all modules
    python test_brain.py --brain      # Test AI brain only
    python test_brain.py --memory     # Test memory only
    python test_brain.py --templates  # Test template fallback only
"""

import argparse
import json
import sys

# ── Sample jobs for testing ──────────────────────────────

SAMPLE_JOBS = [
    {
        "job_id": "test-001",
        "title": "Build a Uniswap V4 Hook for dynamic fees",
        "description": "I need a custom Uniswap V4 hook that implements dynamic swap fees based on volatility. The hook should track price movements and adjust fees between 0.1% and 1% based on a TWAP oracle. Must include Foundry tests.",
        "tags": ["solidity", "uniswap", "defi", "hooks"],
        "budget_amount": "15",
        "budget_token": "NEAR",
        "bid_count": 3,
        "status": "open",
    },
    {
        "job_id": "test-002",
        "title": "Security audit for staking contract",
        "description": "Need a thorough security review of our ERC-20 staking contract. The contract handles ~$2M TVL. Check for reentrancy, flash loan attacks, and access control issues. Provide a report with severity ratings.",
        "tags": ["security", "audit", "solidity", "smart-contracts"],
        "budget_amount": "10",
        "budget_token": "NEAR",
        "bid_count": 5,
        "status": "open",
    },
    {
        "job_id": "test-003",
        "title": "Build simple price tracking bot for NEAR token",
        "description": "Create a bot that tracks NEAR token price on multiple exchanges and alerts when price deviates more than 2% between exchanges. Python preferred.",
        "tags": ["python", "trading", "near", "bot"],
        "budget_amount": "4",
        "budget_token": "NEAR",
        "bid_count": 12,
        "status": "open",
    },
    {
        "job_id": "test-004",
        "title": "Write blog post about DeFi governance",
        "description": "Write a technical blog post about DeFi governance mechanisms. Cover token voting, quadratic voting, and conviction voting. 2000 words.",
        "tags": ["content", "writing", "defi"],
        "budget_amount": "3",
        "budget_token": "NEAR",
        "bid_count": 20,
        "status": "open",
    },
]


def test_scoring():
    """Test the job scoring engine."""
    print("\n" + "=" * 50)
    print("  TEST: Job Scoring Engine")
    print("=" * 50)

    from skills import score_job, calculate_bid_amount, estimate_eta

    for job in SAMPLE_JOBS:
        score = score_job(job)
        bid = calculate_bid_amount(job)
        eta = estimate_eta(job)
        print(f"\n  [{score:.2f}] '{job['title'][:50]}'")
        print(f"         Budget: {job['budget_amount']} NEAR | Bid: {bid} NEAR | ETA: {eta//3600}h")
        print(f"         Tags: {', '.join(job['tags'])}")

    print("\n  OK - Scoring works")
    return True


def test_templates():
    """Test template-based proposal and code generation (no AI needed)."""
    print("\n" + "=" * 50)
    print("  TEST: Template Fallback (no AI)")
    print("=" * 50)

    # Temporarily disable AI
    import brain
    original = brain.ANTHROPIC_API_KEY
    brain.ANTHROPIC_API_KEY = None

    from skills import generate_proposal
    from code_generator import generate_solidity

    for job in SAMPLE_JOBS[:2]:
        print(f"\n  Job: '{job['title'][:50]}'")

        proposal = generate_proposal(job)
        print(f"  Proposal ({len(proposal)} chars): {proposal[:100]}...")

        code = generate_solidity(job)
        print(f"  Code ({len(code)} chars): {code[:80]}...")

    brain.ANTHROPIC_API_KEY = original
    print("\n  OK - Templates work")
    return True


def test_brain():
    """Test AI-powered brain (requires ANTHROPIC_API_KEY)."""
    print("\n" + "=" * 50)
    print("  TEST: AI Brain (Claude API)")
    print("=" * 50)

    from brain import is_ai_enabled, generate_smart_proposal, generate_smart_code, analyze_job_fit

    if not is_ai_enabled():
        print("\n  SKIP - No ANTHROPIC_API_KEY configured")
        print("  Add ANTHROPIC_API_KEY to .env to enable AI features")
        return False

    print("  AI is enabled!")

    # Test proposal generation
    job = SAMPLE_JOBS[0]
    print(f"\n  Generating AI proposal for: '{job['title'][:50]}'")
    proposal = generate_smart_proposal(job)
    if proposal:
        print(f"  Proposal ({len(proposal)} chars):")
        print(f"    {proposal[:200]}...")
        print("  OK")
    else:
        print("  FAILED - No proposal generated")

    # Test code generation
    print(f"\n  Generating AI code for: '{job['title'][:50]}'")
    code = generate_smart_code(job)
    if code:
        print(f"  Code ({len(code)} chars):")
        for line in code.split("\n")[:5]:
            print(f"    {line}")
        print("    ...")
        print("  OK")
    else:
        print("  FAILED - No code generated")

    # Test job analysis
    print(f"\n  Analyzing job fit: '{job['title'][:50]}'")
    analysis = analyze_job_fit(job)
    if analysis:
        print(f"  Score: {analysis.get('score', '?')}")
        print(f"  Reason: {analysis.get('reason', '?')}")
        print(f"  Approach: {analysis.get('approach', '?')}")
        print("  OK")
    else:
        print("  FAILED - No analysis generated")

    return True


def test_memory():
    """Test the memory/learning system."""
    print("\n" + "=" * 50)
    print("  TEST: Memory System")
    print("=" * 50)

    from memory import record_bid, record_win, record_delivery, get_stats, was_bid_on

    job = SAMPLE_JOBS[0]

    # Test recording a bid
    record_bid("test-memory-001", job, "12.8", "Test proposal")
    print("  Recorded bid: OK")

    # Test persistent check
    assert was_bid_on("test-memory-001"), "Should find bid"
    assert not was_bid_on("nonexistent"), "Should not find bid"
    print("  Bid lookup: OK")

    # Test recording a win
    record_win("test-memory-001", job)
    print("  Recorded win: OK")

    # Test recording delivery
    record_delivery("test-memory-001", job, 12.8)
    print("  Recorded delivery: OK")

    # Test stats
    stats = get_stats()
    print(f"  Stats: {json.dumps(stats, indent=4)}")

    print("\n  OK - Memory works")

    # Clean up test data
    import os
    from memory import MEMORY_FILE
    if os.path.exists(MEMORY_FILE):
        print(f"  Note: Memory saved to {MEMORY_FILE}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Test agent modules")
    parser.add_argument("--brain", action="store_true", help="Test AI brain only")
    parser.add_argument("--memory", action="store_true", help="Test memory only")
    parser.add_argument("--templates", action="store_true", help="Test templates only")
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("  defi_builder - Module Tests")
    print("=" * 50)

    results = {}

    if args.brain:
        results["brain"] = test_brain()
    elif args.memory:
        results["memory"] = test_memory()
    elif args.templates:
        results["templates"] = test_templates()
    else:
        # Run all tests
        results["scoring"] = test_scoring()
        results["templates"] = test_templates()
        results["brain"] = test_brain()
        results["memory"] = test_memory()

    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)
    for name, passed in results.items():
        status = "PASS" if passed else "SKIP/FAIL"
        print(f"  {name}: {status}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
