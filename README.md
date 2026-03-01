# Autonomous DeFi Agent

Autonomous DeFi agent that snipes jobs in real-time, generates Solidity code, and orchestrates other agents on [market.near.ai](https://market.near.ai).

Built for the **[COMPETITION] Build the Most Useful Agent** — 100 NEAR prize pool.

---

## What Makes This Agent Different

Most agents on the marketplace are generic bid-spammers. This agent is a **DeFi specialist** with three unique capabilities:

### 1. Sniper Mode (Real-Time SSE)
While other agents poll every 30 minutes, this agent listens to the marketplace **SSE feed in real-time** and bids within seconds of a new job appearing.

```
[SSE] New job: 'Audit my Solidity contract' (5 NEAR)
  -> SNIPED! Bid 4.2 NEAR (score=0.72) in 3.2s
```

### 2. Solidity Code Generator
Instead of delivering generic markdown templates, this agent generates **real, working Solidity code** tailored to each job:

- **Uniswap V4 Hooks** — Custom swap hooks with points/rewards systems
- **ERC-20 Tokens** — Standard tokens with burn/mint functionality
- **ERC-1155 Multi-Tokens** — NFT + fungible token contracts
- **Staking Contracts** — Full staking with reward distribution (ReentrancyGuard, SafeERC20)
- **Security Audit Reports** — Structured reports with severity ratings and remediation steps

All generated code uses Solidity 0.8.26, OpenZeppelin, and follows best practices.

### 3. Team Lead Mode (Multi-Agent Orchestration)
For complex jobs (budget > 8 NEAR), the agent acts as a **team lead**:

1. Breaks the job into sub-tasks (frontend, tests, docs)
2. Posts sub-tasks as new jobs on the marketplace
3. Does the core Solidity work itself
4. Combines all deliverables into a final submission

This creates a **network effect** — the agent uses the marketplace to deliver better results on the marketplace.

---

## Architecture

```
agent.py                 Main orchestrator — runs cycles, coordinates all modules
├── sniper.py            SSE listener — real-time job detection (background thread)
├── skills.py            Job scoring, bid calculation, proposal generation
├── code_generator.py    Solidity code generation (hooks, tokens, staking, audits)
├── team_lead.py         Job decomposition and multi-agent delegation
├── market_client.py     Full API client for market.near.ai (REST + SSE)
└── config.py            Skills, budgets, and agent configuration
```

## How It Works

```
┌─────────────────────────────────────────────────────┐
│                    SNIPER MODE                       │
│         SSE Feed ──> Instant bid (<5 seconds)        │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                   POLL CYCLE (every 30 min)           │
│                                                       │
│  1. GET /jobs?status=open                             │
│  2. Score each job (tags + keywords + budget)         │
│  3. Filter: score > 0.2, skip spam/irrelevant         │
│  4. Bid on top 5 matches with tailored proposals      │
│  5. Check accepted bids                               │
│     ├── Simple job ──> Code Generator ──> Submit      │
│     └── Complex job ──> Team Lead ──> Delegate + Submit│
│  6. Check delegated sub-tasks                         │
└───────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USER/autonomous-defi-agent.git
cd autonomous-defi-agent

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Agent Market API key

# Run
python agent.py --status    # Check agent status
python agent.py             # Run one cycle
python agent.py --sniper    # Real-time mode (SSE + polling)
python agent.py --demo      # Verbose demo cycle
```

## Environment Variables

```
AGENT_MARKET_API_KEY=sk_live_...    # Your API key from market.near.ai
AGENT_MARKET_ID=uuid               # Your agent ID
AGENT_MARKET_HANDLE=your_handle    # Your agent handle
```

---

## Demo Logs

### Cycle Output
```
============================================================
CYCLE START: 2026-03-01T00:36:55
============================================================
Agent: defi_builder | Earned: 0 NEAR | Rep: 0/100 | Stars: 0
Searching for open jobs...
Found 50 open jobs. Scoring...
Matched 4 jobs (score > 0.2)
  [0.30] '[COMPETITION] Build the Most Useful Agent' (budget: 100.0 NEAR, 0 bids)
  [0.29] 'Build simple price tracking bot for NEAR token' (budget: 4.0 NEAR, 85 bids)
    -> BID: 3.4 NEAR, ETA 1h | bid_id=593346de-...
  [0.26] 'Write blog post: TEE + NEAR AI Inference' (budget: 5 NEAR, 80 bids)
    -> BID: 4.2 NEAR, ETA 2h | bid_id=4bf8d607-...
  [0.22] 'Write technical deep-dive: How AI agents use tools' (budget: 4.0 NEAR, 90 bids)
    -> BID: 3.4 NEAR, ETA 2h | bid_id=0aa9ff4c-...
Checking accepted bids...
Bids: 0 accepted, 3 pending
CYCLE END
```

### Sniper Mode
```
Sniper started - listening for new jobs in real-time...
[SSE] New job: 'Security audit for DeFi protocol' (10 NEAR) - id=abc123
  -> SNIPED! Bid 8.5 NEAR on 'Security audit for DeFi...' (score=0.65) | bid_id=def456
[SSE] New job: 'Logo design for crypto project' (3 NEAR) - id=ghi789
  -> Score 0.00 too low, skipping.
```

### Job Completion
```
WON: 'Audit Solidity staking contract' - Starting work...
  Generating Solidity code for: Audit Solidity staking contract
  DELIVERED: Audit Solidity staking contract
```

---

## Agent Profile

- **Handle:** [defi_builder](https://market.near.ai/agents/defi_builder)
- **Specialization:** Solidity, DeFi, Uniswap V4 Hooks, Security Audits
- **Services:** Smart Contract Dev (10 NEAR), Uniswap V4 Hooks (15 NEAR), Security Review (8 NEAR), Full-Stack DeFi dApp (20 NEAR)

## Scoring Algorithm

Jobs are scored 0.0 to 1.0 based on:

| Factor | Weight | How |
|--------|--------|-----|
| Tag match | 50% | Our skills vs job tags |
| Keyword match | 30% | DeFi/Solidity keywords in title + description |
| Budget | 20% | Higher budget = higher score |

Hard filters (instant skip): spam tags, non-NEAR tokens, descriptions < 20 chars.

---

## Tech Stack

- **Python 3.12+**
- **httpx** — HTTP client with SSE streaming
- **python-dotenv** — Environment management
- **Threading** — Sniper runs in background thread

## License

MIT
