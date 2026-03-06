import os
from dotenv import load_dotenv

load_dotenv(override=True)

API_KEY = os.getenv("AGENT_MARKET_API_KEY")
AGENT_ID = os.getenv("AGENT_MARKET_ID")
BASE_URL = "https://market.near.ai/v1"
SSE_URL = "https://market.near.ai/feed/events"

# ── AI Brain (Claude API) ────────────────────────────
# Optional: enables AI-powered proposals, code gen, and auto-revision
# Get your key at https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ── Skills ────────────────────────────────────────────
OUR_SKILLS = [
    # Core DeFi/Solidity
    "solidity", "smart-contracts", "defi", "uniswap", "hooks",
    "security", "audit", "code-review", "foundry",
    "erc20", "erc1155", "development", "programming",
    # Frontend/Web3
    "nextjs", "react", "typescript", "wagmi", "web3", "dapp", "frontend",
    # Broadened capabilities
    "research", "analysis", "technical", "writing", "data",
    "python", "bot", "automation", "api", "integration",
    "documentation", "tutorial", "github", "testing",
    "ai-agents", "tools", "infrastructure",
]

AVOID_TAGS = [
    "pixel_art", "berry", "drawing",
    "animation", "logo", "graphics",
]

# ── Bidding ───────────────────────────────────────────
MIN_BID_AMOUNT = 0.5
MAX_BID_AMOUNT = 50.0
MAX_BIDS_PER_CYCLE = 15
SNIPER_RESPONSE_TIME = 5  # seconds to respond after SSE event

# ── Team Lead ─────────────────────────────────────────
# Minimum budget to consider delegating sub-tasks
DELEGATION_MIN_BUDGET = 8.0
# Percentage of budget to allocate to sub-tasks
DELEGATION_BUDGET_RATIO = 0.4

# ── Polling (fallback) ────────────────────────────────
POLL_INTERVAL = 1800  # 30 minutes
