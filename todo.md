# Token Holder Analytics - Feature Roadmap

## Priority Features

### 1. Holder Count Over Time
**Priority:** High | **Effort:** Low

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

---

### 2. Whale Tracking Dashboard
**Priority:** High | **Effort:** Medium

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

---

### 3. Bubble Map Visualization
**Priority:** High | **Effort:** Medium

Interactive bubble chart of all holders.

**Implementation approach:**
- Use Plotly scatter plot with size = balance
- Color coding: contracts (blue), EOAs (green), exchanges (orange)
- Click to drill down into holder details
- Zoom levels: whales → medium → retail

**Enhancements:**
- Force-directed graph showing transfers between holders
- Cluster detection (wallets that move together)

---

### 4. Holder Distribution Analysis
**Priority:** Medium | **Effort:** Low

Analyze the shape of holder distribution.

**New metrics:**
- Gini coefficient (inequality measure)
- Holder tiers: Whales (>1%), Dolphins (0.1-1%), Fish (<0.1%)
- Distribution histogram with log scale
- Lorenz curve visualization

---

### 5. Token Health Score
**Priority:** High | **Effort:** Medium

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

---

### 6. Suspicious Activity Detection
**Priority:** High | **Effort:** High

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
| Phase 1 | Holder count over time, Holder distribution analysis | - |
| Phase 2 | Whale tracking dashboard, Bubble map visualization | - |
| Phase 3 | Token health score, Suspicious activity detection | - |
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
