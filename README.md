# Strategy Builder AI

Build, run, and manage quantitative allocation strategies across crypto,
commodities, and equities — all from a single dashboard.

## What It Does

- **Build custom strategies** — compose multi-indicator signal systems for any supported asset
- **Real-time scoring** — outlier-robust computation engine with automatic decay detection
- **Portfolio signals** — 7-level allocation recommendations from Strongest Buy to Strongest Sell
- **On-chain subscriptions** — pay with USDC on Base L2, no credit cards

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

## Tech Stack

- **Engine**: Python 3.11+, Pydantic, NumPy, Pandas, SciPy
- **API**: FastAPI, SQLAlchemy (async), PostgreSQL, Redis, SIWE auth
- **Frontend**: Next.js, TypeScript, Tailwind CSS, wagmi/viem
- **Contracts**: Solidity 0.8.24, OpenZeppelin, Base L2

## License

Engine library: MIT — API and frontend: proprietary.
