# DeFi Project Setup Guide

This guide walks you through setting up the DeFi Multi-Chain Analytics project for local development.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [Environment Configuration](#environment-configuration)
- [API Keys Setup](#api-keys-setup)
- [Running the Project](#running-the-project)
- [Testing](#testing)
- [Optional: Subgraph Deployment](#optional-subgraph-deployment)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have the following installed:

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.10+ | `python --version` |
| uv | Latest | `uv --version` |
| Git | Latest | `git --version` |
| Node.js (optional) | 18+ | `node --version` |

### Installing Prerequisites

**Python 3.10+:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3.10 python3.10-venv

# macOS (using Homebrew)
brew install python@3.10
```

**uv (Python package & project manager):**
```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

**Node.js (only needed for subgraph development):**
```bash
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
```

---

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd defi_project_main

# 2. Install dependencies and create virtual environment
uv sync

# 3. Setup environment
cp .env.example .env
# Edit .env with your API keys (see API Keys Setup section)

# 4. Verify installation
uv run make unittest

# 5. Run the example
uv run python examples/multichain_example.py
```

---

## Detailed Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd defi_project_main
```

### Step 2: Install Python Dependencies

The project uses uv for dependency management:

```bash
# Install all dependencies (including dev dependencies)
uv sync

# Or install only production dependencies
uv sync --no-dev
```

This installs:
- **Data processing:** pandas, polars, pyarrow
- **Blockchain:** web3 (EVM), solana, solders
- **APIs:** requests, gql (GraphQL)
- **Database:** sqlalchemy, psycopg2-binary
- **Visualization:** plotly, matplotlib
- **Testing:** pytest, pytest-asyncio

### Step 3: Setup Pre-commit Hooks (Recommended)

```bash
uv run pre-commit install
```

This enables automatic code linting with `ruff` on each commit.

---

## Environment Configuration

### Create Environment File

```bash
cp .env.example .env
```

### Required Environment Variables

Edit `.env` and configure the following:

```bash
# ===========================================
# RPC Endpoints
# ===========================================

# Ethereum RPC (required for ETH queries)
ETH_RPC=https://mainnet.infura.io/v3/YOUR_KEY

# BSC RPC (can use public endpoint for basic usage)
BSC_RPC=https://bsc-dataseed.binance.org/

# Solana RPC (use Helius for best performance)
SOLANA_RPC=https://mainnet.helius-rpc.com/?api-key=YOUR_HELIUS_KEY

# ===========================================
# API Keys
# ===========================================

# Etherscan API (required for ETH analysis)
ETHERSCAN_API_TOKEN=YOUR_ETHERSCAN_KEY

# BSCscan API (required for BSC analysis)
BSCSCAN_API_TOKEN=YOUR_BSCSCAN_KEY

# The Graph API (required for subgraph queries)
THEGRAPH_API_KEY=YOUR_GRAPH_KEY

# Helius API (required for Solana)
HELIUS_API_KEY=YOUR_HELIUS_KEY

# CoinMarketCap API (for market data)
CMC_API_KEY=YOUR_CMC_KEY

# ===========================================
# Database (Optional)
# ===========================================

# PostgreSQL (for caching - uncomment if needed)
# DATABASE_URL=postgresql://user:password@localhost:5432/defi_db
```

---

## API Keys Setup

### Free Tier Services

| Service | Purpose | Free Tier | Signup Link |
|---------|---------|-----------|-------------|
| **The Graph** | Query blockchain data via subgraphs | 100k queries/month | [thegraph.com/studio](https://thegraph.com/studio/) |
| **Helius** | Solana RPC & DAS API | 1M credits/month | [dev.helius.xyz](https://dev.helius.xyz/) |
| **Etherscan** | Ethereum block explorer API | 5 calls/sec | [etherscan.io/apis](https://etherscan.io/apis) |
| **BSCscan** | BSC block explorer API | 5 calls/sec | [bscscan.com/apis](https://bscscan.com/apis) |
| **CoinMarketCap** | Market data | Limited | [coinmarketcap.com/api](https://coinmarketcap.com/api/) |
| **DeFiLlama** | Historical prices | Unlimited | No signup required |

### Step-by-Step API Setup

#### 1. The Graph (Required for EVM chains)

1. Go to [thegraph.com/studio](https://thegraph.com/studio/)
2. Connect your wallet and create an account
3. Navigate to "API Keys" in the dashboard
4. Create a new API key
5. Copy the key to `THEGRAPH_API_KEY` in `.env`

#### 2. Helius (Required for Solana)

1. Go to [dev.helius.xyz](https://dev.helius.xyz/)
2. Sign up for a free account
3. Create a new project
4. Copy the API key to `HELIUS_API_KEY` in `.env`
5. Update `SOLANA_RPC` with: `https://mainnet.helius-rpc.com/?api-key=YOUR_KEY`

#### 3. Etherscan / BSCscan

1. Create accounts at [etherscan.io](https://etherscan.io/) and [bscscan.com](https://bscscan.com/)
2. Go to "API Keys" in your profile
3. Generate new API keys
4. Copy to `ETHERSCAN_API_TOKEN` and `BSCSCAN_API_TOKEN`

#### 4. CoinMarketCap (Optional)

1. Go to [coinmarketcap.com/api](https://coinmarketcap.com/api/)
2. Sign up for a Basic (free) plan
3. Copy the API key to `CMC_API_KEY`

---

## Running the Project

### Multi-Chain Example Script

Run the demo script to test all chain integrations:

```bash
uv run python examples/multichain_example.py
```

This script demonstrates:
- Ethereum token queries via The Graph
- BSC data fetching
- Solana queries via Helius

### Streamlit Dashboard

Launch the interactive web dashboard:

```bash
uv run streamlit run front/streamlit/main.py
```

The dashboard will be available at: **http://localhost:5000**

Features:
- Token analysis
- Holder distribution charts
- Multi-chain data visualization

### Using the Library Directly

```python
from defi_library.blocks_scraping.dev.thegraph import GraphClient
from defi_library.common.historical_price_fetcher import HistoricalPriceFetcher

# Initialize The Graph client
client = GraphClient()

# Query token data
transfers = client.get_token_transfers(
    token_address="0x...",
    chain="ethereum"
)

# Fetch historical prices (no API key needed)
fetcher = HistoricalPriceFetcher()
prices = fetcher.get_historical_prices(
    chain="ethereum",
    token_address="0x...",
    start_timestamp=1704067200  # Jan 1, 2024
)
```

---

## Testing

### Run All Tests

```bash
# Using make
uv run make unittest

# Using pytest
uv run pytest defi_library/unitary/ -v

# Using unittest
uv run python -m unittest discover defi_library/unitary -v
```

### Run Specific Test Files

```bash
# Historical price tests
uv run pytest defi_library/unitary/test_historical_prices.py -v

# Etherscan integration tests
uv run pytest defi_library/unitary/test_etherscan_methods.py -v
```

### Test Coverage

```bash
uv run pytest defi_library/unitary/ --cov=defi_library --cov-report=html
```

---

## Optional: Subgraph Deployment

If you need to deploy custom subgraphs to The Graph:

### Setup

```bash
cd defi_library/subgraphs/erc20-tracker
npm install
```

### Authenticate

```bash
graph auth --studio YOUR_DEPLOY_KEY
```

### Build and Deploy

```bash
# Generate types
graph codegen

# Build
graph build

# Deploy to Subgraph Studio
graph deploy --studio erc20-tracker-eth
```

### Run Subgraph Tests

```bash
npm run test
```

---

## Optional: PostgreSQL Setup

For production caching, you can use PostgreSQL:

### Start PostgreSQL

```bash
make start_postgres
```

### Configure Connection

Add to `.env`:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/defi_db
```

### Stop PostgreSQL

```bash
make stop_postgres
```

---

## Troubleshooting

### Common Issues

#### 1. uv sync fails

```bash
# Clear cache and retry
uv cache clean
uv sync
```

#### 2. Web3 connection errors

- Verify your RPC URLs are correct
- Check API key validity
- Try alternative RPC endpoints (e.g., Chainstack, Alchemy)

#### 3. The Graph rate limiting

- Check your query count in Subgraph Studio dashboard
- Upgrade plan if needed (free tier: 100k/month)

#### 4. Helius errors (Solana)

- Verify API key is correct
- Check credit balance at dev.helius.xyz
- Ensure RPC URL includes your API key

#### 5. Import errors

```bash
# Run commands with uv run to use the virtual environment
uv run python your_script.py

# Or activate the virtual environment manually
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

#### 6. Pre-commit hook failures

```bash
# Run ruff manually to see issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
uv run ruff format .
```

### Getting Help

- Check existing issues in the repository
- Review `MIGRATION_PLAN.md` for architecture decisions
- Examine `examples/` for usage patterns

---

## Project Structure

```
defi_project_main/
├── defi_library/           # Main Python library
│   ├── blocks_scraping/    # Data scraping modules
│   │   └── dev/
│   │       ├── thegraph/   # The Graph client
│   │       ├── solana/     # Helius/Solana client
│   │       ├── etherscan/  # Etherscan API
│   │       └── web3/       # Direct RPC calls
│   ├── common/             # Shared utilities
│   ├── subgraphs/          # The Graph subgraph code
│   └── unitary/            # Unit tests
├── front/
│   └── streamlit/          # Dashboard UI
├── examples/               # Example scripts
├── data/                   # Data storage
├── .env.example            # Environment template
├── pyproject.toml          # Python dependencies
└── makefile                # Build commands
```

---

## Cost Estimation

Running this project with free tier APIs:

| Service | Monthly Limit | Typical Usage | Cost |
|---------|--------------|---------------|------|
| The Graph | 100k queries | ~50k queries | $0 |
| Helius | 1M credits | ~200k credits | $0 |
| Etherscan | Unlimited (rate limited) | Variable | $0 |
| BSCscan | Unlimited (rate limited) | Variable | $0 |
| DeFiLlama | Unlimited | Variable | $0 |

**Estimated monthly cost: $0 - $20** (depending on usage)

---

## Next Steps

1. Complete the [Quick Start](#quick-start) setup
2. Run `uv run python examples/multichain_example.py` to verify everything works
3. Launch the dashboard with `uv run streamlit run front/streamlit/main.py`
4. Explore the API in `defi_library/` for custom integrations
