# strategy-builder-ai

Quantitative allocation signal platform for multi-asset portfolios.

## Quick Start

```bash
# Install the core engine
pip install -e ".[dev,ml]"

# Run tests
pytest

# Start the API (requires PostgreSQL + Redis)
uvicorn api.main:app --reload

# Start the frontend
cd web && npm run dev
```

## Subscription Tiers

| Tier | Price | Assets | Features |
|------|-------|--------|----------|
| Explorer | Free | BTC | Basic signals |
| Strategist | 29 USDC/mo | BTC, ETH, Gold, SPX | Full portfolio signals |
| Quant | 99 USDC/mo | All + alts | ML insights, regime detection |

Payments via USDC on **Base L2**.

## Tech Stack

- **Engine**: Python 3.11+, Pydantic, NumPy, Pandas, SciPy
- **API**: FastAPI, SQLAlchemy (async), PostgreSQL, Redis, SIWE auth
- **Frontend**: Next.js, TypeScript, Tailwind CSS, wagmi/viem
- **Contracts**: Solidity 0.8.24, OpenZeppelin, Base L2

## License

Engine library: MIT — API and frontend: proprietary.
