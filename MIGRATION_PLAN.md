# Migration Plan: Cryo to The Graph + Helius

## Overview

This document outlines the migration from Cryo (unmaintained) to:
- **The Graph** for ETH + BSC (EVM chains)
- **Helius + solana-py** for Solana

**Budget Target:** < 50 EUR/month
**Actual Cost:** 0-20 EUR/month

---

## 1. Current State (What We're Replacing)

### Cryo Usage (`blocks_scraping/dev/cryo/rpc_queries.py`)

| Method | Purpose | Replacement |
|--------|---------|-------------|
| `fetch_erc20_balances()` | Get ERC-20 balances across block ranges | The Graph subgraph |
| `get_token_value_blocks()` | Calculate token value from pool balances | The Graph subgraph |

### Key Data Being Fetched
- ERC-20 token balances at specific blocks
- Balance history over block ranges
- Token valuations from liquidity pool ratios

---

## 2. New Architecture

```
defi_library/
├── blocks_scraping/
│   ├── dev/
│   │   ├── web3/              # KEEP - Direct RPC calls
│   │   ├── etherscan/         # KEEP - Explorer API
│   │   ├── cmc/               # KEEP - Market data
│   │   ├── cryo/              # DEPRECATE - Remove after migration
│   │   ├── thegraph/          # NEW - The Graph client
│   │   │   ├── __init__.py
│   │   │   ├── graph_client.py
│   │   │   └── queries.py
│   │   └── solana/            # NEW - Solana via Helius
│   │       ├── __init__.py
│   │       ├── helius_client.py
│   │       └── solana_queries.py
├── subgraphs/                  # NEW - Subgraph definitions
│   └── erc20-tracker/
│       ├── subgraph.yaml
│       ├── schema.graphql
│       ├── src/
│       │   └── mapping.ts
│       └── abis/
│           └── ERC20.json
```

---

## 3. The Graph Setup (ETH + BSC)

### 3.1 Prerequisites

```bash
# Install Graph CLI globally
npm install -g @graphprotocol/graph-cli

# Or use npx (no install needed)
npx @graphprotocol/graph-cli --version
```

### 3.2 Subgraph Development Flow

1. **Define Schema** (`schema.graphql`)
   - Token entities
   - Balance entities
   - Transfer events

2. **Create Mappings** (`src/mapping.ts`)
   - Handle Transfer events
   - Update balance snapshots

3. **Deploy Options:**

| Option | Cost | Rate Limits | Best For |
|--------|------|-------------|----------|
| **Subgraph Studio (Hosted)** | FREE | 100k queries/month | Development |
| **Self-hosted Graph Node** | ~15 EUR/month VPS | Unlimited | Production |
| **Decentralized Network** | Pay GRT | Unlimited | Not recommended for budget |

### 3.3 Deployment Commands

```bash
# Authenticate with Subgraph Studio (free)
graph auth --studio <DEPLOY_KEY>

# Create subgraph
graph create --node https://api.studio.thegraph.com/deploy/ erc20-tracker

# Deploy to Ethereum
graph deploy --studio erc20-tracker-eth

# Deploy to BSC (requires BSC-compatible indexer)
graph deploy --studio erc20-tracker-bsc
```

### 3.4 Self-Hosted Option (Recommended for Production)

```bash
# Using Docker Compose
git clone https://github.com/graphprotocol/graph-node
cd graph-node/docker

# Edit docker-compose.yml to point to your RPC
# ethereum: 'mainnet:https://your-rpc-url'

docker-compose up -d
```

**VPS Requirements:**
- 4GB RAM minimum
- 50GB SSD
- Cost: ~10-20 EUR/month (Hetzner, Contabo)

---

## 4. Helius Setup (Solana)

### 4.1 Account Setup

1. Go to https://dev.helius.xyz/
2. Create free account
3. Get API key (1M credits/month FREE)

### 4.2 Environment Variables

Add to `.env`:
```
HELIUS_API_KEY=your_helius_api_key
SOLANA_RPC_URL=https://mainnet.helius-rpc.com/?api-key=your_key
```

### 4.3 Key Endpoints

| Endpoint | Purpose | Credits |
|----------|---------|---------|
| `getAssetsByOwner` | Get all tokens for wallet | 100 |
| `getTokenAccounts` | SPL token balances | 50 |
| `getSignaturesForAsset` | Transaction history | 100 |
| Enhanced RPC | Standard Solana RPC | 1-10 |

---

## 5. Migration Steps

### Phase 1: Setup (Day 1)

- [x] Create migration plan
- [ ] Install dependencies (`gql`, `solana`, `solders`)
- [ ] Set up environment variables
- [ ] Create new directory structure

### Phase 2: The Graph Integration (Day 2-3)

- [ ] Create subgraph schema
- [ ] Write event mappings
- [ ] Deploy to Subgraph Studio (ETH)
- [ ] Deploy BSC version
- [ ] Create Python client wrapper
- [ ] Test queries match Cryo output

### Phase 3: Solana Integration (Day 4-5)

- [ ] Set up Helius account
- [ ] Implement `helius_client.py`
- [ ] Implement `solana_queries.py`
- [ ] Test SPL token queries
- [ ] Test transaction history

### Phase 4: Testing & Cleanup (Day 6-7)

- [ ] Compare outputs with Cryo
- [ ] Update frontend to use new APIs
- [ ] Remove Cryo dependency
- [ ] Update documentation

---

## 6. API Comparison

### Cryo (Old) vs The Graph (New)

```python
# OLD (Cryo)
data = cryo.collect(
    "erc20_balances",
    blocks=["1000:2000"],
    address=addresses,
    contract=token,
    rpc=rpc_url
)

# NEW (The Graph)
query = """
{
  balanceSnapshots(
    where: {
      token: "0x...",
      blockNumber_gte: 1000,
      blockNumber_lte: 2000
    }
  ) {
    account { id }
    balance
    blockNumber
  }
}
"""
data = graph_client.query(query)
```

### Direct RPC vs Helius (Solana)

```python
# Standard RPC (slow, no indexing)
balance = client.get_token_accounts_by_owner(wallet)

# Helius (fast, indexed)
assets = helius.get_assets_by_owner(wallet)
```

---

## 7. Cost Analysis

| Service | Monthly Cost | Notes |
|---------|--------------|-------|
| The Graph (Studio) | 0 EUR | 100k queries free |
| The Graph (Self-hosted) | 10-20 EUR | VPS costs |
| Helius | 0 EUR | 1M credits free |
| Chainstack RPC (backup) | 0 EUR | 3M requests free |
| **Total** | **0-20 EUR** | Under budget |

---

## 8. Rollback Plan

If migration fails:
1. Keep Cryo code in `deprecated/` folder
2. Cryo can still work with existing RPC endpoints
3. Gradual migration: run both systems in parallel

---

## 9. Files Changed

### New Files
- `defi_library/blocks_scraping/dev/thegraph/__init__.py`
- `defi_library/blocks_scraping/dev/thegraph/graph_client.py`
- `defi_library/blocks_scraping/dev/thegraph/queries.py`
- `defi_library/blocks_scraping/dev/solana/__init__.py`
- `defi_library/blocks_scraping/dev/solana/helius_client.py`
- `defi_library/blocks_scraping/dev/solana/solana_queries.py`
- `defi_library/subgraphs/erc20-tracker/` (entire folder)

### Modified Files
- `defi_library/config.py` - Add new env variables
- `pyproject.toml` - Update dependencies

### Deprecated Files
- `defi_library/blocks_scraping/dev/cryo/rpc_queries.py`
- `front/streamlit/utils/cryo_helper.py`

---

## 10. Next Steps

After this migration:
1. Add more subgraphs for specific protocols (Uniswap, Aave)
2. Implement caching layer for Graph queries
3. Add Solana DeFi protocol support (Raydium, Orca)
4. Consider multi-chain abstraction layer
