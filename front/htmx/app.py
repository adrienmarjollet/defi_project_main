"""
HTMX Frontend for DeFi Analytics

A minimal, multi-page frontend using Flask + HTMX for token analysis.
Entry point: token address + chain selection.
"""

import os
import sys

from flask import Flask, render_template, request, jsonify

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv

load_dotenv()

from defi_library.constants import COMMON_TOKENS, DEFAULT_TOKEN

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Supported chains
# ---------------------------------------------------------------------------
CHAINS = {
    "ethereum": {"name": "Ethereum", "short": "ETH", "explorer": "https://etherscan.io"},
    "bsc": {"name": "BNB Smart Chain", "short": "BSC", "explorer": "https://bscscan.com"},
    "solana": {"name": "Solana", "short": "SOL", "explorer": "https://solscan.io"},
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_htmx_request():
    """Check if the request comes from HTMX."""
    return request.headers.get("HX-Request") == "true"


def get_token_context():
    """Extract token_address and chain from request args."""
    token_address = request.args.get("token", "").strip()
    chain = request.args.get("chain", "ethereum").strip()
    return token_address, chain


def common_context():
    """Build context dictionary shared across all pages."""
    token_address, chain = get_token_context()
    return {
        "token_address": token_address,
        "chain": chain,
        "chains": CHAINS,
        "common_tokens": COMMON_TOKENS,
        "default_token": DEFAULT_TOKEN,
        "chain_info": CHAINS.get(chain, CHAINS["ethereum"]),
    }


# ---------------------------------------------------------------------------
# Demo data generators (used when subgraph is not configured)
# ---------------------------------------------------------------------------

def _demo_token_info(token_address, chain):
    """Return demo token metadata."""
    # Check if it matches a known token
    name_map = {v.lower(): k for k, v in COMMON_TOKENS.items()}
    symbol = name_map.get(token_address.lower(), "TOKEN")
    names = {
        "WETH": "Wrapped Ether",
        "PEPE": "Pepe",
        "USDC": "USD Coin",
        "USDT": "Tether USD",
        "SHIB": "Shiba Inu",
        "UNI": "Uniswap",
        "TOKEN": "Unknown Token",
    }
    return {
        "name": names.get(symbol, "Unknown Token"),
        "symbol": symbol,
        "address": token_address,
        "chain": chain,
        "decimals": 18,
        "total_supply": "1,000,000,000",
        "holder_count": 2543,
    }


def _demo_holders():
    """Return demo holder data."""
    return [
        {"rank": 1, "address": "0x28C6...9e3F", "full_address": "0x28C6c06B97CAda3Edc34bE077C1059e3590e9e3F", "balance": "152,340,000", "percentage": 15.23, "type": "exchange"},
        {"rank": 2, "address": "0xF977...bAFC", "full_address": "0xF977814e90dA44bFA03b6295A0616a897441bAFC", "balance": "98,500,000", "percentage": 9.85, "type": "exchange"},
        {"rank": 3, "address": "0x21a3...d1f0", "full_address": "0x21a31Ee1afC51d94C2eFcCAa2093aD1322d1f0", "balance": "45,200,000", "percentage": 4.52, "type": "whale"},
        {"rank": 4, "address": "0x5041...B860", "full_address": "0x5041ed759Dd4aFc3a72b8192C143F72f4724B860", "balance": "38,100,000", "percentage": 3.81, "type": "whale"},
        {"rank": 5, "address": "0xDFd5...0626", "full_address": "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d", "balance": "25,800,000", "percentage": 2.58, "type": "whale"},
        {"rank": 6, "address": "0x1f9a...fCA0", "full_address": "0x1f9a8c40f5d1eBBB0b9E8C9F51C9F7aA3efCA0", "balance": "18,900,000", "percentage": 1.89, "type": "contract"},
        {"rank": 7, "address": "0xAb5B...c9e4", "full_address": "0xAb5B7b5849784279280188b556AF3c179F2c9e4", "balance": "12,400,000", "percentage": 1.24, "type": "whale"},
        {"rank": 8, "address": "0x7Be2...3bA1", "full_address": "0x7Be2FB91F55F60C0EEB0C8E8C9F51C9F7aA3bA1", "balance": "8,700,000", "percentage": 0.87, "type": "eoa"},
        {"rank": 9, "address": "0x9C3a...1dF7", "full_address": "0x9C3a19C4E0BdC8B9f5ECBB0C8E8C9F51C9F1dF7", "balance": "6,200,000", "percentage": 0.62, "type": "eoa"},
        {"rank": 10, "address": "0xE8f0...5a2C", "full_address": "0xE8f0C9C4E0BdC8B9f5ECBB0C8E8C9F51C95a2C", "balance": "4,100,000", "percentage": 0.41, "type": "eoa"},
    ]


def _demo_whale_data():
    """Return demo whale tracking data."""
    return {
        "total_concentration": 38.9,
        "concentration_change": -2.3,
        "accumulating": 3,
        "distributing": 2,
        "stability_score": 72,
        "pattern": "Mild Distribution",
        "alerts": [
            {"address": "0x21a3...d1f0", "action": "distributed", "change": -8.2, "severity": "high"},
            {"address": "0x28C6...9e3F", "action": "accumulated", "change": 3.5, "severity": "medium"},
            {"address": "0x5041...B860", "action": "accumulated", "change": 2.1, "severity": "low"},
        ],
        "whales": [
            {"address": "0x28C6...9e3F", "balance": "152.3M", "pct": 15.23, "change": "+3.5%", "trend": "up"},
            {"address": "0xF977...bAFC", "balance": "98.5M", "pct": 9.85, "change": "-0.2%", "trend": "stable"},
            {"address": "0x21a3...d1f0", "balance": "45.2M", "pct": 4.52, "change": "-8.2%", "trend": "down"},
            {"address": "0x5041...B860", "balance": "38.1M", "pct": 3.81, "change": "+2.1%", "trend": "up"},
            {"address": "0xDFd5...0626", "balance": "25.8M", "pct": 2.58, "change": "+0.3%", "trend": "stable"},
        ],
    }


def _demo_health_score():
    """Return demo health score data."""
    return {
        "overall_score": 67.4,
        "grade": "B",
        "risk_level": "Medium",
        "holder_count": 2543,
        "components": {
            "holder_count": {"score": 72.5, "weight": 20, "status": "Good"},
            "concentration": {"score": 54.3, "weight": 25, "status": "Fair"},
            "growth_trend": {"score": 68.1, "weight": 20, "status": "Good"},
            "whale_stability": {"score": 71.8, "weight": 20, "status": "Good"},
            "contract_ratio": {"score": 78.2, "weight": 15, "status": "Good"},
        },
        "risk_factors": [
            "Moderate concentration: Top 10 hold 45.2%",
            "Some whale distribution detected",
        ],
        "positive_factors": [
            "Strong holder count (2,500+ holders)",
            "Healthy EOA ratio (72.3%)",
            "Stable growth pattern",
        ],
    }


def _demo_suspicious_activity():
    """Return demo suspicious activity data."""
    return {
        "overall_risk_score": 48.0,
        "risk_level": "Medium",
        "total_flags": 4,
        "critical_flags": 0,
        "high_flags": 1,
        "medium_flags": 2,
        "low_flags": 1,
        "activities": [
            {
                "type": "Concentration Spike",
                "severity": "high",
                "description": "Single wallet holds 18.5% of supply",
                "risk_score": 18.5,
                "addresses": ["0x28C6...9e3F"],
            },
            {
                "type": "Coordinated Wallets",
                "severity": "medium",
                "description": "5 wallets with similar balances (8.2% total)",
                "risk_score": 10.0,
                "addresses": ["0xaaaa...1111", "0xbbbb...2222", "0xcccc...3333"],
            },
            {
                "type": "Sybil Cluster",
                "severity": "medium",
                "description": "8 wallets with identical balances (3.5% total)",
                "risk_score": 12.0,
                "addresses": ["0x1111...aaaa", "0x2222...bbbb"],
            },
            {
                "type": "Dump Pattern",
                "severity": "low",
                "description": "Some whale distribution detected (3 of 8 whales)",
                "risk_score": 7.5,
                "addresses": [],
            },
        ],
    }


def _demo_price_data():
    """Return demo price history data."""
    import random
    random.seed(42)
    prices = []
    base = 1850.0
    for i in range(30):
        base += random.uniform(-80, 80)
        base = max(base, 500)
        prices.append({
            "day": i + 1,
            "date": f"2025-01-{i+1:02d}",
            "price": round(base, 2),
            "volume": round(random.uniform(50_000_000, 200_000_000), 0),
        })
    current = prices[-1]["price"]
    prev = prices[0]["price"]
    change = current - prev
    change_pct = (change / prev) * 100
    return {
        "current_price": f"${current:,.2f}",
        "price_change": round(change, 2),
        "price_change_pct": round(change_pct, 2),
        "high_30d": f"${max(p['price'] for p in prices):,.2f}",
        "low_30d": f"${min(p['price'] for p in prices):,.2f}",
        "avg_volume": f"${sum(p['volume'] for p in prices) / len(prices):,.0f}",
        "prices": prices,
    }


# ---------------------------------------------------------------------------
# Full page routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    """Landing page with token address + chain selection."""
    ctx = common_context()
    return render_template("pages/home.html", **ctx)


@app.route("/overview")
def overview():
    """Token overview page."""
    ctx = common_context()
    token_address, chain = get_token_context()
    if not token_address:
        return render_template("pages/home.html", **ctx, error="Please enter a token address.")
    ctx["token"] = _demo_token_info(token_address, chain)
    if is_htmx_request():
        return render_template("partials/token_info.html", **ctx)
    return render_template("pages/overview.html", **ctx)


@app.route("/holders")
def holders():
    """Holder analysis page."""
    ctx = common_context()
    token_address, chain = get_token_context()
    if not token_address:
        return render_template("pages/home.html", **ctx, error="Please enter a token address.")
    ctx["token"] = _demo_token_info(token_address, chain)
    ctx["holders"] = _demo_holders()
    # Distribution stats
    top10_pct = sum(h["percentage"] for h in ctx["holders"])
    ctx["distribution"] = {
        "top10_pct": round(top10_pct, 2),
        "top10_count": len(ctx["holders"]),
        "exchange_pct": round(sum(h["percentage"] for h in ctx["holders"] if h["type"] == "exchange"), 2),
        "whale_pct": round(sum(h["percentage"] for h in ctx["holders"] if h["type"] == "whale"), 2),
        "contract_pct": round(sum(h["percentage"] for h in ctx["holders"] if h["type"] == "contract"), 2),
        "eoa_pct": round(sum(h["percentage"] for h in ctx["holders"] if h["type"] == "eoa"), 2),
    }
    if is_htmx_request():
        return render_template("partials/holder_table.html", **ctx)
    return render_template("pages/holders.html", **ctx)


@app.route("/whales")
def whales():
    """Whale tracking page."""
    ctx = common_context()
    token_address, chain = get_token_context()
    if not token_address:
        return render_template("pages/home.html", **ctx, error="Please enter a token address.")
    ctx["token"] = _demo_token_info(token_address, chain)
    ctx["whale_data"] = _demo_whale_data()
    if is_htmx_request():
        return render_template("partials/whale_table.html", **ctx)
    return render_template("pages/whales.html", **ctx)


@app.route("/health")
def health():
    """Health score page."""
    ctx = common_context()
    token_address, chain = get_token_context()
    if not token_address:
        return render_template("pages/home.html", **ctx, error="Please enter a token address.")
    ctx["token"] = _demo_token_info(token_address, chain)
    ctx["health"] = _demo_health_score()
    if is_htmx_request():
        return render_template("partials/health_score.html", **ctx)
    return render_template("pages/health.html", **ctx)


@app.route("/suspicious")
def suspicious():
    """Suspicious activity page."""
    ctx = common_context()
    token_address, chain = get_token_context()
    if not token_address:
        return render_template("pages/home.html", **ctx, error="Please enter a token address.")
    ctx["token"] = _demo_token_info(token_address, chain)
    ctx["report"] = _demo_suspicious_activity()
    if is_htmx_request():
        return render_template("partials/suspicious_report.html", **ctx)
    return render_template("pages/suspicious.html", **ctx)


@app.route("/price")
def price():
    """Price history page."""
    ctx = common_context()
    token_address, chain = get_token_context()
    if not token_address:
        return render_template("pages/home.html", **ctx, error="Please enter a token address.")
    ctx["token"] = _demo_token_info(token_address, chain)
    ctx["price_data"] = _demo_price_data()
    if is_htmx_request():
        return render_template("partials/price_chart.html", **ctx)
    return render_template("pages/price.html", **ctx)


# ---------------------------------------------------------------------------
# HTMX partial endpoints
# ---------------------------------------------------------------------------

@app.route("/partials/token-search", methods=["POST"])
def token_search():
    """Handle the main token search form submission via HTMX."""
    token_address = request.form.get("token_address", "").strip()
    chain = request.form.get("chain", "ethereum").strip()

    if not token_address:
        return '<div class="alert alert-error">Please enter a token address.</div>'

    if not token_address.startswith("0x") and chain != "solana":
        return '<div class="alert alert-error">Invalid address format. EVM addresses must start with 0x.</div>'

    # Return redirect headers for HTMX to navigate to overview
    response = app.make_response("")
    response.headers["HX-Redirect"] = f"/overview?token={token_address}&chain={chain}"
    return response


@app.route("/partials/quick-token", methods=["POST"])
def quick_token():
    """Fill token address from quick-select buttons."""
    token_address = request.form.get("address", "")
    chain = request.form.get("chain", "ethereum")
    return f'<input type="text" id="token-input" name="token_address" value="{token_address}" class="input-token" placeholder="0x..." required>'


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
