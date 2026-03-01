"""Skills engine - evaluates jobs and generates proposals."""

import logging
from config import OUR_SKILLS, AVOID_TAGS, MIN_BID_AMOUNT, MAX_BID_AMOUNT

logger = logging.getLogger("skills")


def score_job(job: dict) -> float:
    """Score a job from 0.0 to 1.0 based on skill match. Returns 0.0 to skip."""
    tags = [t.lower() for t in job.get("tags", []) if len(t) < 30]
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()

    # Hard filters
    for tag in tags:
        if tag in AVOID_TAGS:
            return 0.0
    if job.get("budget_token", "NEAR") not in ("NEAR", "USDC"):
        return 0.0
    if "test1" in title or len(description) < 20:
        return 0.0

    score = 0.0
    text = f"{title} {description}"

    # Tag matching (0 to 0.5)
    if tags:
        matching = sum(1 for t in tags if t in OUR_SKILLS)
        score += min(matching / max(len(tags), 1), 1.0) * 0.5

    # Keyword matching (0 to 0.3)
    keywords = [
        "solidity", "smart contract", "defi", "uniswap", "hook",
        "erc20", "erc1155", "audit", "security", "review",
        "foundry", "hardhat", "ethereum", "token", "swap",
        "nextjs", "react", "frontend", "web3", "dapp", "wagmi",
        "typescript", "code review", "development",
    ]
    matches = sum(1 for kw in keywords if kw in text)
    score += min(matches / 5, 1.0) * 0.3

    # Budget attractiveness (0 to 0.2)
    budget = float(job.get("budget_amount") or 0)
    if budget >= 5:
        score += 0.2
    elif budget >= 1:
        score += 0.1

    return round(score, 2)


def calculate_bid_amount(job: dict) -> str:
    """Calculate a competitive bid amount."""
    budget = float(job.get("budget_amount") or 0)
    bid = budget * 0.85 if budget > 0 else 3.0
    bid = max(MIN_BID_AMOUNT, min(bid, MAX_BID_AMOUNT))
    return f"{bid:.1f}"


def estimate_eta(job: dict) -> int:
    """Estimate time to complete in seconds."""
    desc = job.get("description", "")
    text = f"{job.get('title', '')} {desc}".lower()

    if "audit" in text or "security" in text:
        return 7200
    if "fullstack" in text or "dapp" in text:
        return 14400
    if len(desc) > 2000:
        return 10800
    return 3600


def generate_proposal(job: dict) -> str:
    """Generate a tailored proposal for a job."""
    title = job.get("title", "").lower()
    desc = job.get("description", "").lower()
    text = f"{title} {desc}"

    is_security = any(kw in text for kw in ["audit", "security", "vulnerability"])
    is_defi = any(kw in text for kw in ["defi", "uniswap", "swap", "liquidity", "hook"])
    is_solidity = any(kw in text for kw in ["solidity", "smart contract", "erc"])
    is_frontend = any(kw in text for kw in ["frontend", "nextjs", "react", "dashboard"])

    if is_defi and is_solidity:
        intro = (
            "DeFi specialist with deployed Uniswap V4 hooks on Sepolia. "
            "Experienced with custom swap fees, referral systems, and ERC-1155 rewards."
        )
    elif is_security:
        intro = (
            "Security-focused Solidity developer. I analyze for reentrancy, "
            "access control, overflow, front-running, and DeFi attack vectors. "
            "Foundry-based testing included."
        )
    elif is_solidity:
        intro = (
            "Solidity developer with production experience: ERC-20, ERC-1155, "
            "Uniswap V4 hooks, DeFi protocols. Foundry for testing."
        )
    elif is_frontend:
        intro = (
            "Full-stack Web3 dev: Next.js, TypeScript, wagmi, RainbowKit. "
            "Built DeFi dashboards and token swap interfaces."
        )
    else:
        intro = (
            "Web3 developer specializing in Solidity and full-stack DeFi apps. "
            "Foundry testing, Next.js frontends, wallet integration."
        )

    return f"{intro} Will deliver clean, documented, tested code."
