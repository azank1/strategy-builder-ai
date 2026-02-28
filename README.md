# strategy-builder-ai

Quantitative allocation signal platform — open-source engine, proprietary webapp.

Build custom portfolio signals using z-score valuation (SDCA) and long-term trend identification (LTPI), across BTC, ETH, Gold & SPX.

## System Levels

| Level | System | Purpose |
|-------|--------|---------|
| **Level 1** | SDCA (Strategic Dollar Cost Averaging) | Long-term valuation — detect tops and bottoms via z-scored indicators |
| **Level 2** | LTPI (Long-Term Trend Probability Indicator) | Long-term trend — detect market trajectory via time-coherent binary signals |
| **Level 3** | MTPI (Medium-Term Trend Probability) | *(coming soon)* |

Levels combine — SDCA valuation + LTPI trend = 7-level signal matrix (Strongest Buy → Strongest Sell).

## Quick Start

```bash
# Install the core engine
pip install -e ".[dev,ml]"

# Run tests
pytest

# Start the API (requires PostgreSQL)
uvicorn api.main:app --reload

# Start the frontend
cd web && npm run dev
```

## Project Structure

```
strategy-builder-ai/
├── strategy_engine/           # Open-source Python core engine
│   ├── models.py              # Pydantic data models (SDCA, LTPI, signals)
│   ├── core/
│   │   ├── zscore.py          # Z-score engine with outlier methods
│   │   ├── validation.py      # SDCA + LTPI rule enforcement
│   │   ├── coherency.py       # Time coherency analysis
│   │   └── composite.py       # Composite scoring + portfolio signals
│   ├── data/
│   │   ├── base.py            # DataAdapter ABC
│   │   ├── yahoo.py           # Yahoo Finance adapter
│   │   └── coingecko.py       # CoinGecko adapter
│   └── ml/
│       ├── decay.py           # Alpha decay detection
│       ├── correlation.py     # Redundancy analysis
│       └── regime.py          # Market regime detection (HMM)
├── api/                       # FastAPI backend (proprietary)
│   ├── main.py                # App entrypoint
│   ├── config.py              # Settings via pydantic-settings
│   ├── auth.py                # SIWE wallet auth + JWT
│   ├── database.py            # Async SQLAlchemy sessions
│   ├── db_models.py           # User, System, Signal DB models
│   ├── schemas.py             # Request/response schemas
│   └── routes/
│       ├── auth.py            # /auth/nonce, /auth/login
│       ├── users.py           # /users/me
│       ├── systems.py         # CRUD /systems/
│       └── signals.py         # /signals/compute, /signals/portfolio
├── web/                       # Next.js frontend (proprietary)
│   └── src/
│       ├── app/               # App router pages
│       ├── components/        # React components
│       └── lib/               # wagmi config, API client
├── contracts/                 # Solidity (Base L2)
│   └── StrategySubscription.sol
├── tests/                     # Pytest suite (52 tests)
├── docs/                      # PRIVATE — never published
│   ├── level-1-sdca/
│   ├── level-2-ltpi/
│   └── level-3-mtpi/
└── pyproject.toml
```

## Subscription Tiers

| Tier | Price | Assets | Features |
|------|-------|--------|----------|
| Explorer | Free | BTC | Basic signals |
| Strategist | 29 USDC/mo | BTC, ETH, Gold, SPX | Full portfolio signals |
| Quant | 99 USDC/mo | All + alts | ML insights, regime detection |

Payments via USDC on **Base L2** through the `StrategySubscription` smart contract.

## Tech Stack

- **Engine**: Python 3.11+, Pydantic, NumPy, Pandas, SciPy, scikit-learn, hmmlearn
- **API**: FastAPI, SQLAlchemy (async), PostgreSQL, SIWE auth
- **Frontend**: Next.js, TypeScript, Tailwind CSS, wagmi/viem
- **Contracts**: Solidity 0.8.24, OpenZeppelin, Base L2
