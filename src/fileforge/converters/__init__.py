"""Pro-tier features. Every entry point in this package calls
``licensing.require(Tier.PRO)`` (or higher) before doing work, so the same
codebase ships to all tiers and unlocks by license key."""
