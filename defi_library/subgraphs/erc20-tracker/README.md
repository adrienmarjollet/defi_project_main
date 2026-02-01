# ERC-20 Token Tracker Subgraph

A subgraph for tracking ERC-20 token balances, transfers, and price data on Ethereum and BSC.

## Features

- **Balance Tracking**: Real-time token balances for all accounts
- **Historical Snapshots**: Balance history at every block
- **Transfer Events**: Complete transfer history with parsed amounts
- **Holder Analytics**: Holder count and distribution
- **Price Data**: Pool-based token pricing

## Prerequisites

```bash
# Install Graph CLI
npm install -g @graphprotocol/graph-cli

# Or use npx (no global install)
npx @graphprotocol/graph-cli --version
```

## Quick Start

### 1. Install Dependencies

```bash
cd defi_library/subgraphs/erc20-tracker
npm install
```

### 2. Configure Tokens

Edit `subgraph.yaml` to add your tokens:

```yaml
dataSources:
  - kind: ethereum/contract
    name: MyToken
    network: mainnet  # or 'bsc' for BSC
    source:
      address: "0xYourTokenAddress"
      abi: ERC20
      startBlock: 12345678  # Deployment block
    mapping:
      # ... (copy from WETH example)
```

### 3. Generate Types

```bash
npm run codegen
# or: graph codegen
```

### 4. Build

```bash
npm run build
# or: graph build
```

### 5. Deploy

#### Option A: Subgraph Studio (Recommended - FREE)

```bash
# Authenticate
graph auth --studio YOUR_DEPLOY_KEY

# Deploy to Ethereum
graph deploy --studio erc20-tracker-eth

# Deploy to BSC
# (Change network in subgraph.yaml first)
graph deploy --studio erc20-tracker-bsc
```

#### Option B: Self-Hosted Graph Node

```bash
# Create subgraph
npm run create:local
# or: graph create --node http://localhost:8020/ erc20-tracker

# Deploy
npm run deploy:local
# or: graph deploy --node http://localhost:8020/ --ipfs http://localhost:5001 erc20-tracker
```

## Querying

### GraphQL Playground

After deployment, access the GraphQL playground at your subgraph URL.

### Python Client

```python
from blocks_scraping.dev.thegraph import ERC20Queries

queries = ERC20Queries(
    subgraph_url="https://api.studio.thegraph.com/query/YOUR_ID/erc20-tracker-eth/version/latest"
)

# Get top holders
holders = queries.get_token_balances(
    token_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    limit=100
)

# Get historical balances
history = queries.get_balance_snapshots(
    token_address="0x...",
    account_address="0x...",
    from_block=18000000,
    to_block=18100000
)
```

### Example Queries

```graphql
# Get token info
{
  token(id: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2") {
    name
    symbol
    decimals
    totalSupply
    holderCount
  }
}

# Get top holders
{
  accountBalances(
    first: 100
    where: { token: "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2" }
    orderBy: balance
    orderDirection: desc
  ) {
    account { id }
    balance
    blockNumber
  }
}

# Get balance history
{
  balanceSnapshots(
    where: {
      token: "0x..."
      account: "0x..."
      blockNumber_gte: 18000000
      blockNumber_lte: 18100000
    }
    orderBy: blockNumber
  ) {
    blockNumber
    balance
    timestamp
  }
}

# Get recent transfers
{
  transfers(
    first: 100
    where: { token: "0x..." }
    orderBy: blockNumber
    orderDirection: desc
  ) {
    from { id }
    to { id }
    amount
    blockNumber
    transactionHash
  }
}
```

## Schema

| Entity | Description |
|--------|-------------|
| `Token` | ERC-20 token metadata |
| `Account` | Wallet/contract addresses |
| `AccountBalance` | Current token balances |
| `BalanceSnapshot` | Historical balance at each block |
| `Transfer` | Transfer events |
| `LiquidityPool` | DEX pool reserves |
| `PriceSnapshot` | Token prices over time |

## Multi-Chain Deployment

To deploy on multiple chains:

1. **Ethereum**: Keep `network: mainnet` in subgraph.yaml
2. **BSC**: Change to `network: bsc`
3. **Polygon**: Change to `network: matic`
4. **Arbitrum**: Change to `network: arbitrum-one`

Deploy each as a separate subgraph with chain-specific naming:
- `erc20-tracker-eth`
- `erc20-tracker-bsc`
- `erc20-tracker-polygon`

## Self-Hosting Guide

For unlimited free queries, self-host a Graph Node:

```bash
# Clone graph-node
git clone https://github.com/graphprotocol/graph-node
cd graph-node/docker

# Configure ethereum endpoint in docker-compose.yml
# ethereum: 'mainnet:https://your-rpc-url'

# Start Graph Node
docker-compose up -d

# Deploy your subgraph
graph create --node http://localhost:8020/ erc20-tracker
graph deploy --node http://localhost:8020/ --ipfs http://localhost:5001 erc20-tracker
```

**VPS Requirements:**
- 4GB RAM minimum
- 50GB SSD
- Estimated cost: ~10-20 EUR/month

## Troubleshooting

### "Failed to start indexing"
- Check that startBlock is correct (should be deployment block or earlier)
- Verify RPC endpoint is working

### "Mapping terminated"
- Check for null/undefined values in mapping.ts
- Use try_ variants for contract calls (e.g., `try_name()`)

### Slow indexing
- Reduce startBlock to only necessary blocks
- Consider using multiple data sources for different time periods

## License

MIT
