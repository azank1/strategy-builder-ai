// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title StrategySubscription
 * @notice Recurring USDC/USDT subscription payments on Base L2.
 * @dev Users approve this contract to pull ERC-20 tokens on a monthly cycle.
 *
 * Tiers:
 *   0 = Explorer  (free)
 *   1 = Strategist (~$29 USDC/month)
 *   2 = Quant      (~$99 USDC/month)
 */
contract StrategySubscription is Ownable, ReentrancyGuard {
    // ─── State ───────────────────────────────────────────────────────────────

    struct TierConfig {
        uint256 pricePerMonth; // in payment token decimals (6 for USDC)
        bool active;
    }

    struct Subscription {
        uint8 tier;
        uint256 paidUntil;    // timestamp
        uint256 lastPayment;  // timestamp
    }

    IERC20 public paymentToken; // USDC on Base
    uint256 public constant MONTH = 30 days;

    mapping(uint8 => TierConfig) public tiers;
    mapping(address => Subscription) public subscriptions;

    address public treasury;

    // ─── Events ──────────────────────────────────────────────────────────────

    event Subscribed(address indexed user, uint8 tier, uint256 paidUntil);
    event Renewed(address indexed user, uint8 tier, uint256 paidUntil);
    event Cancelled(address indexed user, uint8 tier);
    event TierUpdated(uint8 tier, uint256 price, bool active);

    // ─── Constructor ─────────────────────────────────────────────────────────

    constructor(
        address _paymentToken,
        address _treasury
    ) Ownable(msg.sender) {
        paymentToken = IERC20(_paymentToken);
        treasury = _treasury;

        // Default tier prices (USDC has 6 decimals)
        tiers[1] = TierConfig({ pricePerMonth: 29 * 1e6, active: true });  // $29
        tiers[2] = TierConfig({ pricePerMonth: 99 * 1e6, active: true });  // $99
    }

    // ─── User Functions ──────────────────────────────────────────────────────

    /**
     * @notice Subscribe to a tier by paying for the first month.
     * @param tier The subscription tier (1 = Strategist, 2 = Quant).
     */
    function subscribe(uint8 tier) external nonReentrant {
        require(tier > 0 && tier <= 2, "Invalid tier");
        TierConfig memory cfg = tiers[tier];
        require(cfg.active, "Tier not active");

        Subscription storage sub = subscriptions[msg.sender];
        require(sub.tier == 0 || block.timestamp > sub.paidUntil, "Already subscribed");

        // Pull payment
        require(
            paymentToken.transferFrom(msg.sender, treasury, cfg.pricePerMonth),
            "Payment failed"
        );

        sub.tier = tier;
        sub.paidUntil = block.timestamp + MONTH;
        sub.lastPayment = block.timestamp;

        emit Subscribed(msg.sender, tier, sub.paidUntil);
    }

    /**
     * @notice Renew an existing subscription for another month.
     * @dev Anyone can call this for any user (e.g., a keeper bot).
     */
    function renew(address user) external nonReentrant {
        Subscription storage sub = subscriptions[user];
        require(sub.tier > 0, "No subscription");
        require(block.timestamp >= sub.paidUntil, "Not yet due");

        TierConfig memory cfg = tiers[sub.tier];
        require(cfg.active, "Tier deactivated");

        require(
            paymentToken.transferFrom(user, treasury, cfg.pricePerMonth),
            "Payment failed — subscription lapsed"
        );

        sub.paidUntil = sub.paidUntil + MONTH;
        sub.lastPayment = block.timestamp;

        emit Renewed(user, sub.tier, sub.paidUntil);
    }

    /**
     * @notice Cancel a subscription. Remains active until paidUntil.
     */
    function cancel() external {
        Subscription storage sub = subscriptions[msg.sender];
        require(sub.tier > 0, "No subscription");
        uint8 oldTier = sub.tier;
        sub.tier = 0; // revert to Explorer on expiry
        emit Cancelled(msg.sender, oldTier);
    }

    // ─── View Functions ──────────────────────────────────────────────────────

    function isActive(address user) external view returns (bool) {
        Subscription memory sub = subscriptions[user];
        if (sub.tier == 0) return true; // Explorer is always active
        return block.timestamp <= sub.paidUntil;
    }

    function getUserTier(address user) external view returns (uint8) {
        Subscription memory sub = subscriptions[user];
        if (sub.tier > 0 && block.timestamp > sub.paidUntil) {
            return 0; // expired → Explorer
        }
        return sub.tier;
    }

    // ─── Admin ───────────────────────────────────────────────────────────────

    function setTierPrice(uint8 tier, uint256 price, bool active) external onlyOwner {
        require(tier > 0, "Cannot modify free tier");
        tiers[tier] = TierConfig({ pricePerMonth: price, active: active });
        emit TierUpdated(tier, price, active);
    }

    function setTreasury(address _treasury) external onlyOwner {
        treasury = _treasury;
    }

    function setPaymentToken(address _token) external onlyOwner {
        paymentToken = IERC20(_token);
    }
}
