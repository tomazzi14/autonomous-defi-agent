"""Skills engine - evaluates jobs and generates proposals.

Uses Claude AI for intelligent scoring and proposal generation when available.
Broadened to handle ANY job type — not just DeFi/Solidity.
"""

import logging
from config import OUR_SKILLS, AVOID_TAGS, MIN_BID_AMOUNT, MAX_BID_AMOUNT
from brain import generate_smart_proposal, analyze_job_fit, is_ai_enabled

logger = logging.getLogger("skills")

# Expanded keyword categories for broader matching
CORE_KEYWORDS = [
    "solidity", "smart contract", "defi", "uniswap", "hook",
    "erc20", "erc1155", "audit", "security", "review",
    "foundry", "hardhat", "ethereum", "token", "swap",
    "nextjs", "react", "frontend", "web3", "dapp", "wagmi",
    "typescript", "code review", "development",
]

GENERAL_KEYWORDS = [
    "research", "analysis", "data", "technical", "writing",
    "blog", "documentation", "tutorial", "python", "bot",
    "api", "integration", "automation", "script", "tool",
    "github", "open source", "testing", "benchmark",
    "report", "summary", "deep-dive", "comparison",
]

# Hard skip — jobs we literally cannot do
HARD_SKIP_TAGS = [
    "pixel_art", "drawing", "animation", "design", "branding",
    "logo", "graphics", "video", "tiktok", "instagram",
]


def score_job(job: dict) -> float:
    """Score a job from 0.0 to 1.0. AI-first, heuristic fallback."""
    tags = [t.lower() for t in job.get("tags", []) if len(t) < 30]
    title = job.get("title", "").lower()
    description = job.get("description", "").lower()

    # Hard filters
    if job.get("budget_token", "NEAR") not in ("NEAR", "USDC"):
        return 0.0
    if "test1" in title or len(description) < 20:
        return 0.0

    # Skip visual/design jobs we can't do
    for tag in tags:
        if tag in HARD_SKIP_TAGS:
            return 0.0

    # Try AI scoring first — much smarter than keyword matching
    if is_ai_enabled():
        analysis = analyze_job_fit(job)
        if analysis and "score" in analysis:
            ai_score = min(max(analysis["score"], 0.0), 1.0)
            logger.debug(
                "AI score %.2f for '%s': %s",
                ai_score, title[:40], analysis.get("reason", ""),
            )
            return round(ai_score, 2)

    # Heuristic fallback
    return _heuristic_score(job, tags, title, description)


def _heuristic_score(job: dict, tags: list, title: str, description: str) -> float:
    """Keyword-based scoring fallback."""
    score = 0.0
    text = f"{title} {description}"

    # Core skill tag matching (0 to 0.35)
    if tags:
        matching = sum(1 for t in tags if t in OUR_SKILLS)
        score += min(matching / max(len(tags), 1), 1.0) * 0.35

    # Core keyword matching (0 to 0.25)
    core_matches = sum(1 for kw in CORE_KEYWORDS if kw in text)
    score += min(core_matches / 5, 1.0) * 0.25

    # General keyword matching (0 to 0.15) — broadens our reach
    general_matches = sum(1 for kw in GENERAL_KEYWORDS if kw in text)
    score += min(general_matches / 3, 1.0) * 0.15

    # Budget attractiveness (0 to 0.15)
    budget = float(job.get("budget_amount") or 0)
    if budget >= 5:
        score += 0.15
    elif budget >= 2:
        score += 0.10
    elif budget >= 1:
        score += 0.05

    # Competition factor (0 to 0.10) — fewer bids = better odds
    bid_count = job.get("bid_count", 0)
    if bid_count < 10:
        score += 0.10
    elif bid_count < 30:
        score += 0.05

    return round(score, 2)


def calculate_bid_amount(job: dict) -> str:
    """Calculate a competitive bid amount."""
    budget = float(job.get("budget_amount") or 0)
    bid_count = job.get("bid_count", 0)

    if budget <= 0:
        return "1.0"

    # More aggressive pricing when there's heavy competition
    if bid_count > 50:
        ratio = 0.75
    elif bid_count > 20:
        ratio = 0.80
    else:
        ratio = 0.85

    bid = budget * ratio
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
    if "research" in text or "dataset" in text or "analysis" in text:
        return 5400
    if "blog" in text or "write" in text or "article" in text:
        return 3600
    if len(desc) > 2000:
        return 10800
    return 3600


def generate_proposal(job: dict) -> str:
    """Generate a tailored proposal for a job. AI-first, template fallback."""
    # Try AI-powered proposal first
    if is_ai_enabled():
        logger.info("Using AI brain for proposal...")
        ai_proposal = generate_smart_proposal(job)
        if ai_proposal:
            return ai_proposal
        logger.warning("AI proposal failed, falling back to template")

    # Template fallback
    title = job.get("title", "").lower()
    desc = job.get("description", "").lower()
    text = f"{title} {desc}"

    is_security = any(kw in text for kw in ["audit", "security", "vulnerability"])
    is_defi = any(kw in text for kw in ["defi", "uniswap", "swap", "liquidity", "hook"])
    is_solidity = any(kw in text for kw in ["solidity", "smart contract", "erc"])
    is_frontend = any(kw in text for kw in ["frontend", "nextjs", "react", "dashboard"])
    is_research = any(kw in text for kw in ["research", "analysis", "data", "report", "summarize"])
    is_writing = any(kw in text for kw in ["write", "blog", "article", "tutorial", "deep-dive"])

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
    elif is_research:
        intro = (
            "Technical researcher with deep knowledge of DeFi, AI agents, "
            "and Web3 infrastructure. I deliver structured, data-backed analysis."
        )
    elif is_writing:
        intro = (
            "Technical writer with hands-on blockchain experience. "
            "I write clear, accurate content backed by real development expertise."
        )
    else:
        intro = (
            "Autonomous AI agent with expertise in Web3, DeFi, and technical analysis. "
            "I deliver fast, thorough, and well-documented work."
        )

    return f"{intro} Will deliver clean, documented, high-quality work."
