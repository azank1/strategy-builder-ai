# Smart Contracts — Strategy Builder AI

## StrategySubscription.sol

Recurring USDC subscription contract for Base L2.

### Tiers
| Tier | Name | Price | Assets |
|------|------|-------|--------|
| 0 | Explorer | Free | BTC |
| 1 | Strategist | 29 USDC/mo | BTC, ETH, Gold, SPX |
| 2 | Quant | 99 USDC/mo | All + alts + ML |

### Key Functions
- `subscribe(tier)` — Pay first month and activate tier
- `renew(user)` — Pay next month (callable by keeper bots)
- `cancel()` — Cancel; stays active until `paidUntil`
- `isActive(user)` / `getUserTier(user)` — View functions for API integration

### Deployment
Target: **Base L2** (Chain ID: 8453)

Payment tokens:
- USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- USDT: `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2`

### Dependencies
- OpenZeppelin Contracts v5.x (`@openzeppelin/contracts`)

### TODO
- [ ] Add Foundry/Hardhat project configuration
- [ ] Write deployment scripts
- [ ] Add unit tests
- [ ] Integrate with API backend (read tier from chain)
- [ ] Add keeper bot for auto-renewal
- [ ] Consider EIP-7265 circuit breaker for safety
