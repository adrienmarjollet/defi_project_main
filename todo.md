# Token Holder Analytics - Feature Roadmap

## Priority Features

### 1. Holder Count Over Time [COMPLETED]
**Priority:** High | **Effort:** Low | **Status:** Done

Track unique holder count evolution to detect growth/decline trends.

**Implementation approach:**
- Query The Graph's `Token.holderCount` at different block intervals
- Store snapshots in a time series
- Visualize as line chart showing holder growth/decline
- Calculate holder growth rate (daily/weekly)

**Use cases:**
- Detect organic vs. artificial growth
- Identify pump phases
- Compare growth rates across tokens

**Implemented files:**
- `defi_library/blocks_scraping/dev/thegraph/holder_count_queries.py` - Core query logic
- `defi_library/common/models.py` - Added `HolderCountSnapshot` model
- `front/streamlit/pages/3_Holder_Count_Analytics.py` - Streamlit dashboard
- `front/streamlit/utils/data_analysis.py` - Growth rate utilities

---

### 2. Whale Tracking Dashboard [COMPLETED]
**Priority:** High | **Effort:** Medium | **Status:** Done

Follow top N holders' balances over time.

**Implementation approach:**
- Identify top 20-50 holders at a starting point
- Track their `BalanceSnapshots` across blocks
- Alert system for large movements (>5% of their holdings)
- Show accumulation/distribution patterns

**Visualizations:**
- Stacked area chart (show how whale composition changes)
- Individual whale balance sparklines
- "Whale activity feed" showing recent large movements

**Implemented files:**
- `defi_library/blocks_scraping/dev/thegraph/whale_tracking_queries.py` - Core query and tracking logic
- `defi_library/common/models.py` - Added `WhaleTrackingSnapshot` model
- `front/streamlit/pages/5_Whale_Tracking_Dashboard.py` - Streamlit dashboard
- `front/streamlit/utils/data_analysis.py` - Added whale tracking utilities

---

### 3. Bubble Map Visualization [COMPLETED]
**Priority:** High | **Effort:** Medium | **Status:** Done

Interactive bubble chart of all holders.

**Implementation approach:**
- Use Plotly scatter plot with size = balance
- Color coding: contracts (blue), EOAs (green), exchanges (orange)
- Click to drill down into holder details
- Zoom levels: whales → medium → retail

**Enhancements:**
- Force-directed graph showing transfers between holders
- Cluster detection (wallets that move together)

**Implemented files:**
- `defi_library/blocks_scraping/dev/thegraph/bubble_map_queries.py` - Core query and wallet classification logic
- `front/streamlit/pages/6_Bubble_Map_Visualization.py` - Streamlit dashboard with bubble map, treemap, sunburst
- `front/streamlit/utils/data_analysis.py` - Added bubble map visualization utilities

---

### 4. Holder Distribution Analysis [COMPLETED]
**Priority:** Medium | **Effort:** Low | **Status:** Done

Analyze the shape of holder distribution.

**New metrics:**
- Gini coefficient (inequality measure)
- Holder tiers: Whales (>1%), Dolphins (0.1-1%), Fish (<0.1%)
- Distribution histogram with log scale
- Lorenz curve visualization

**Implemented files:**
- `defi_library/blocks_scraping/dev/thegraph/holder_distribution_queries.py` - Core query and calculation logic
- `defi_library/common/models.py` - Added `HolderDistributionSnapshot` model
- `front/streamlit/pages/4_Holder_Distribution_Analytics.py` - Streamlit dashboard
- `front/streamlit/utils/data_analysis.py` - Added distribution analysis utilities

---

### 5. Token Health Score [COMPLETED]
**Priority:** High | **Effort:** Medium | **Status:** Done

Composite risk/quality indicator based on holder metrics.

**Factors to include:**
- Holder count (more = healthier)
- Concentration (lower = healthier)
- Holder growth trend (positive = healthier)
- Whale stability (less movement = healthier)
- Contract vs EOA ratio

**Output:**
- Score from 0-100
- Breakdown by category
- Historical score tracking

**Implemented files:**
- `defi_library/blocks_scraping/dev/thegraph/token_health_score_queries.py` - Core query and calculation logic
- `defi_library/common/models.py` - Added `TokenHealthScoreSnapshot` model
- `front/streamlit/pages/7_Token_Health_Score.py` - Streamlit dashboard with gauge chart, radar chart, component breakdown
- `front/streamlit/utils/data_analysis.py` - Added health score utilities

---

### 6. Suspicious Activity Detection [COMPLETED]
**Priority:** High | **Effort:** High | **Status:** Done

Flag potential scam/manipulation patterns.

**Red flags to detect:**
- Circular transfers (wash trading)
- Sudden concentration increases
- Many wallets funded from same source
- Coordinated dump patterns
- Single entity split across wallets (cluster analysis)

**Output:**
- Risk flags with severity levels
- Visual highlighting of suspicious wallets
- Transaction flow diagrams

**Implemented files:**
- `defi_library/blocks_scraping/dev/thegraph/suspicious_activity_queries.py` - Core detection logic
- `defi_library/common/models.py` - Added `SuspiciousActivitySnapshot` model
- `front/streamlit/pages/8_Suspicious_Activity_Detection.py` - Streamlit dashboard
- `front/streamlit/utils/data_analysis.py` - Added suspicious activity utilities

---

## Additional Features

### 7. Smart Money Tracking
**Priority:** Medium | **Effort:** High

Identify and follow "smart money" wallets.

**Features:**
- Track wallets that bought early and held
- Detect wallets with consistent profitable trades
- Cross-token analysis (what else do top holders own?)
- Alert when smart money enters/exits positions

---

### 8. Holder Cohort Analysis
**Priority:** Medium | **Effort:** Medium

Group holders by when they first acquired tokens.

**Visualizations:**
- Cohort retention chart (how many early holders still hold?)
- Average hold duration per cohort
- Cohort behavior comparison (early vs late buyers)

---

### 9. Comparative Token Analysis
**Priority:** Medium | **Effort:** Medium

Compare holder metrics across multiple tokens.

**Features:**
- Side-by-side holder distribution comparison
- Benchmark against similar tokens (memecoins vs DeFi vs NFT)
- Holder overlap analysis (shared whales between tokens)

---

### 10. Real-time Alert System
**Priority:** Medium | **Effort:** High

Notifications for significant holder events.

**Alert types:**
- Whale accumulation/distribution
- Holder count milestones (100, 1000, 10000)
- Concentration threshold breaches
- New top 10 holder entry
- Large transfer events

**Delivery methods:**
- Telegram bot
- Discord webhook
- Email notifications

---

## Implementation Order

| Phase | Features | Timeline |
|-------|----------|----------|
| Phase 1 | ~~Holder count over time~~, ~~Holder distribution analysis~~ | Completed |
| Phase 2 | ~~Whale tracking dashboard~~, ~~Bubble map visualization~~ | Completed |
| Phase 3 | ~~Token health score~~, ~~Suspicious activity detection~~ | Completed |
| Phase 4 | Smart money tracking, Cohort analysis | - |
| Phase 5 | Comparative analysis, Alert system | - |

---

## Technical Notes

### Existing Infrastructure to Leverage
- The Graph's `BalanceSnapshot` entity for historical data
- `ERC20Queries.get_balance_snapshots()` for time series
- `SolanaQueries.get_token_concentration()` for Solana
- Plotly for interactive visualizations
- Streamlit for dashboard pages

### New Dependencies to Consider
- `networkx` for graph analysis (bubble map, cluster detection)
- `scipy` for statistical calculations (Gini coefficient)
- `python-telegram-bot` or `discord.py` for alerts

### Data Storage Considerations
- Consider adding SQLite/PostgreSQL tables for:
  - Historical holder counts
  - Whale watchlist
  - Alert configurations
  - Cached health scores

---

# Advanced Token Analysis Features

## On-Chain Behavioral Analysis

### 11. Wallet Personality Profiling
**Priority:** High | **Effort:** High

Classify wallets by behavior patterns.

**Wallet types to identify:**
- HODLer (long-term holder, rarely sells)
- Trader (frequent buy/sell activity)
- Flipper (quick in-and-out, <24h holds)
- Bot (inhuman patterns)
- Yield Farmer (moves between protocols)

**Metrics to calculate:**
- "Diamond hands" score (hold through dips)
- Panic seller vs. strategic seller classification
- Wallet reputation score based on history
- Average hold duration

---

### 12. Entry/Exit Pattern Analysis
**Priority:** Medium | **Effort:** Medium

Understand how wallets accumulate and distribute.

**Patterns to detect:**
- DCA (Dollar Cost Averaging) wallets
- "Buy the dip" vs "FOMO buy" behavior
- Selling at psychological price barriers
- Wallets that consistently buy bottoms or sell tops

**Visualizations:**
- Entry price distribution histogram
- Exit timing relative to price peaks
- Accumulation curves per wallet

---

### 13. Wallet Age & Activity Correlation
**Priority:** Medium | **Effort:** Low

Analyze wallet lifecycle and activity patterns.

**Metrics:**
- First transaction date of each holder
- Activity frequency (daily/weekly active wallets)
- Dormant wallet reactivation alerts
- "Zombie wallet" detection (no activity in X months)
- Wallet age distribution of holders

---

## Market Microstructure

### 14. Order Flow Toxicity
**Priority:** High | **Effort:** High

Analyze buy vs. sell pressure dynamics.

**Metrics:**
- Buy/sell pressure over time
- Absorption detection (large orders without price impact)
- Volume-weighted buy/sell ratio
- "Stealth accumulation" detection (many small buys, same entity)

**Visualizations:**
- Cumulative delta chart
- Buy/sell imbalance heatmap
- Pressure divergence indicators

---

### 15. Price Impact Analysis
**Priority:** High | **Effort:** Medium

Understand liquidity and slippage.

**Features:**
- Calculate slippage for different trade sizes
- Liquidity depth heatmap across price levels
- "How much can you sell without crashing price?" calculator
- Compare liquidity across DEXes (Uniswap, Sushi, etc.)

**Output:**
- Slippage curves
- Optimal trade size recommendations
- Liquidity score vs. similar tokens

---

### 16. Volatility Regime Detection
**Priority:** Medium | **Effort:** Medium

Identify and analyze volatility patterns.

**Features:**
- High/low volatility period identification
- Holder behavior correlation per regime
- Volatility clustering analysis
- "Calm before the storm" pattern detection

**Use cases:**
- Risk-adjusted position sizing
- Optimal entry/exit timing
- Anomaly detection

---

## Bot & MEV Analysis

### 17. Bot Detection Dashboard
**Priority:** High | **Effort:** High

Identify and track bot activity on this token.

**Bot types to detect:**
- Sandwich bots targeting this token's traders
- Sniper bots (buys within first blocks of launch)
- Arbitrage bots
- Front-running bots

**Metrics:**
- Bot transaction percentage
- Bot profit extraction
- Most active bot wallets
- Bot activity trends over time

---

### 18. MEV Extraction Tracking
**Priority:** Medium | **Effort:** High

Track MEV (Maximal Extractable Value) impact.

**Metrics:**
- Total MEV extracted from token traders
- Sandwich attack victim count and losses
- JIT (Just-In-Time) liquidity events
- MEV exposure comparison vs. similar tokens

**Visualizations:**
- MEV extraction over time
- Victim wallet analysis
- MEV by type breakdown

---

### 19. Automated Trading Detection
**Priority:** Medium | **Effort:** Medium

Identify non-human trading patterns.

**Detection methods:**
- Inhuman reaction times (<1 block)
- Regular interval trading (every X blocks)
- Copy-trading bot identification
- Market maker pattern recognition

**Output:**
- Automated vs. organic volume ratio
- Known market maker identification
- Bot sophistication scoring

---

## Network Graph Analysis

### 20. Wallet Clustering (Entity Resolution)
**Priority:** High | **Effort:** High

Group wallets controlled by same entity.

**Clustering signals:**
- Shared funding sources (same parent wallet)
- Coordinated transaction timing
- Similar transaction patterns
- Gas price fingerprinting
- Shared contract interactions

**Output:**
- True holder count vs. wallet count
- Entity size distribution
- Sybil attack detection
- Visual cluster map

---

### 21. Token Flow Sankey Diagram
**Priority:** High | **Effort:** Medium

Visualize where tokens come from and go to.

**Flow sources:**
- DEX purchases
- CEX withdrawals
- Airdrops
- Bridge transfers
- Contract distributions

**Flow destinations:**
- Held in wallet
- Sold on DEX
- Deposited to CEX
- Staked/farmed
- Bridged out

**Features:**
- Multi-hop token tracking
- "Black hole" contract detection (tokens enter, never leave)
- Time-lapse flow animation

---

### 22. Influence Network
**Priority:** Medium | **Effort:** High

Map social dynamics between wallets.

**Features:**
- Identify "leader" wallets that others copy
- Detect coordinated trading groups
- Social graph of transfers (who transacts with whom)
- Influence propagation analysis

**Visualizations:**
- Force-directed influence graph
- Leader-follower relationship map
- Coordination score per wallet group

---

## Tokenomics Deep Dive

### 23. Unlock Schedule Impact
**Priority:** High | **Effort:** Medium

Track and predict vesting unlock events.

**Features:**
- Identify and track vesting contracts
- Calendar of upcoming unlock events
- Historical price impact of past unlocks
- "Cliff risk" score calculation

**Alerts:**
- Upcoming large unlocks
- Vesting beneficiary behavior changes
- Early unlock pattern detection

---

### 24. Burn & Mint Analysis
**Priority:** Medium | **Effort:** Low

Track supply dynamics.

**Metrics:**
- Burn rate over time
- Mint events and frequency
- Net supply change trends
- Deflationary/inflationary pressure indicator

**Visualizations:**
- Supply change chart
- Burn event timeline
- Projected supply curves

---

### 25. Staking Flow Analysis
**Priority:** Medium | **Effort:** Medium

Monitor staking contract dynamics.

**Metrics:**
- Tokens moving to/from staking contracts
- Staking ratio over time
- Average stake duration
- Unstaking surge detection (sell pressure warning)

**Features:**
- Yield farming migration tracking
- Staking reward impact on supply
- Staker loyalty scoring

---

## Cross-Token Intelligence

### 26. Whale Portfolio X-Ray
**Priority:** High | **Effort:** High

Analyze what else top holders own.

**Features:**
- Portfolio composition of top 50 holders
- Cross-token correlation
- "Smart money" portfolio tracking
- Early signal: "Whales buying ETH early now buying X"

**Visualizations:**
- Portfolio treemap per whale
- Common holdings heatmap
- Portfolio rotation timeline

---

### 27. Token Correlation Matrix
**Priority:** Medium | **Effort:** Medium

Understand token relationships.

**Metrics:**
- Price correlation with other tokens
- Holder overlap percentage
- "If you hold X, you probably hold Y" recommendations
- Sector rotation detection

**Visualizations:**
- Correlation heatmap
- Holder overlap Venn diagrams
- Sector flow analysis

---

### 28. Liquidity Pair Analysis
**Priority:** Medium | **Effort:** Medium

Analyze all trading pairs for a token.

**Features:**
- List all DEX pairs
- Liquidity distribution across pairs
- Impermanent loss tracking for LPs
- LP holder concentration analysis

**Metrics:**
- Best pair for trading (lowest slippage)
- LP APY comparison
- Liquidity stability score

---

## Temporal Analysis

### 29. Time-of-Day Patterns
**Priority:** Low | **Effort:** Low

Analyze when activity happens.

**Features:**
- Transaction heatmap by hour/day
- Weekday vs. weekend activity comparison
- Geographic distribution inference from timing
- Optimal trading windows identification

**Visualizations:**
- 24-hour activity clock
- Weekly activity heatmap
- Timezone distribution chart

---

### 30. Event Impact Analysis
**Priority:** Medium | **Effort:** High

Correlate external events with on-chain behavior.

**Event sources:**
- Twitter/social media mentions
- GitHub commits (for protocol tokens)
- Partnership announcements
- Exchange listings
- Regulatory news

**Analysis:**
- Holder behavior before/after events
- Price impact measurement
- "Buy the rumor, sell the news" detection

---

### 31. Seasonality Detection
**Priority:** Low | **Effort:** Medium

Find recurring patterns.

**Features:**
- Monthly/quarterly patterns
- Token-specific recurring events
- Correlation with broader market cycles
- Holiday effects

**Use cases:**
- Predict high-activity periods
- Position timing optimization

---

## Risk & Security

### 32. Rug Pull Probability Score
**Priority:** High | **Effort:** High

Assess scam risk factors.

**Risk factors:**
- Liquidity lock status and duration
- Contract ownership (renounced or not)
- Deployer wallet history (previous rugs?)
- Similar contract deployments (copy-paste scams)
- Team token allocation percentage

**Output:**
- Risk score 0-100
- Red flag breakdown
- Comparison to known rugs

---

### 33. Contract Risk Analysis
**Priority:** High | **Effort:** Medium

Analyze smart contract security.

**Risk factors:**
- Proxy contract upgrade risk
- Admin key concentration
- Pause/blacklist function presence
- Honeypot detection
- Unlimited mint capabilities

**Output:**
- Contract safety score
- Function risk breakdown
- Similar contract comparison

---

### 34. Exit Liquidity Calculator
**Priority:** High | **Effort:** Medium

Stress test selling scenarios.

**Simulations:**
- "If top 10 holders dump, what happens?"
- Cascading liquidation scenarios
- Different sell size impacts
- Recovery time estimation

**Visualizations:**
- Price impact curves
- Liquidation cascade simulation
- Liquidity exhaustion levels

---

## Predictive Analytics

### 35. Holder Behavior Prediction
**Priority:** Medium | **Effort:** High

ML-powered wallet behavior forecasting.

**Models:**
- "Will this wallet sell in next 7 days?" classifier
- Accumulation phase detection
- Distribution phase detection
- "Smart money rotating" early warning

**Features:**
- Probability scores per wallet
- Aggregate sell pressure prediction
- Model confidence indicators

---

### 36. Price Support/Resistance from Holders
**Priority:** High | **Effort:** Medium

Map holder cost basis to price levels.

**Features:**
- Cost basis distribution of all holders
- Profit/loss distribution at current price
- Psychological price level identification
- "Bag holder" cluster mapping

**Visualizations:**
- UTXO-style realized price bands
- Support/resistance heatmap
- Profit-taking probability by price

---

### 37. Momentum Indicators from On-Chain
**Priority:** Medium | **Effort:** Medium

Derive trading signals from on-chain data.

**Indicators:**
- New holder acceleration/deceleration
- Whale accumulation momentum
- Transfer velocity trends (SOPR-style)
- Network Value to Transaction ratio (NVT)
- MVRV (Market Value to Realized Value)

**Output:**
- Buy/sell signal generation
- Trend strength indicators
- Divergence alerts

---

## Unique Visualizations

### 38. Token Lifecycle Timeline
**Priority:** Medium | **Effort:** Medium

Visual journey from launch to present.

**Timeline events:**
- Launch date and method
- Key milestones (holder counts, price ATH/ATL)
- Major events (listings, hacks, partnerships)
- Holder composition changes

**Features:**
- Interactive timeline with zoom
- Event annotation system
- Comparison with similar token lifecycles

---

### 39. Token "X-Ray" Single Page Report
**Priority:** High | **Effort:** Medium

Comprehensive one-page token overview.

**Sections:**
- Key metrics with traffic light indicators (red/yellow/green)
- Holder distribution summary
- Risk assessment
- Liquidity analysis
- Recent significant events

**Features:**
- Comparison to category averages
- PDF/image export
- Shareable report links

---

### 40. Live Activity Feed
**Priority:** Medium | **Effort:** High

Real-time transaction monitoring.

**Features:**
- WebSocket-powered live updates
- Transaction stream with highlights
- Significant event detection
- Filterable by size, type, wallet

**Alerts:**
- Large transaction notifications
- Whale movement alerts
- Unusual activity flags

---

## Implementation Phases (Updated)

| Phase | Features | Focus Area |
|-------|----------|------------|
| Phase 1 | #1-4, #11-13 | Core holder analytics & behavior |
| Phase 2 | #5-6, #20-21 | Health scoring & graph analysis |
| Phase 3 | #14-16, #28 | Market microstructure & liquidity |
| Phase 4 | #17-19, #32-34 | Bots, MEV & security |
| Phase 5 | #23-25 | Tokenomics analysis |
| Phase 6 | #26-27, #35-37 | Cross-token & predictive |
| Phase 7 | #7-10, #29-31, #38-40 | Alerts, temporal & visualization |

---

## New Dependencies for Advanced Features

### Machine Learning
- `scikit-learn` for classification models
- `xgboost` for gradient boosting predictions
- `pytorch` for deep learning (optional)

### Graph Analysis
- `networkx` for graph algorithms
- `python-louvain` for community detection
- `pyvis` for interactive graph visualization

### Real-time
- `websockets` for live feeds
- `redis` for caching and pub/sub
- `celery` for background task processing

### Visualization
- `plotly` (already present)
- `altair` for declarative charts
- `d3.js` integration for custom visualizations

### Data Processing
- `polars` for faster DataFrame operations
- `dask` for large dataset handling
- `pyarrow` for efficient data storage
