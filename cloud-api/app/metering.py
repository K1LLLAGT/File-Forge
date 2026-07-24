"""Usage metering for the Cloud API. In-memory reference implementation that
maps 1:1 onto the published pricing (strategy #3).

Swap ``Meter`` for a Redis/Postgres-backed class in production; the interface
(``known``, ``allow``, ``record``, ``snapshot``) is what the API depends on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class Plan(str, Enum):
    METERED = "metered"        # $5/mo, 500 conversions, then $0.01 each
    LIFETIME = "lifetime"      # $49 one-off, unlimited
    ENTERPRISE = "enterprise"  # $199/yr, unlimited + SLA


PLAN_QUOTA = {
    Plan.METERED: 500,
    Plan.LIFETIME: None,       # None == unlimited
    Plan.ENTERPRISE: None,
}


@dataclass
class _Account:
    plan: Plan
    used: int = 0


@dataclass
class Meter:
    accounts: Dict[str, _Account] = field(default_factory=dict)

    def register_key(self, api_key: str, plan: Plan) -> None:
        self.accounts[api_key] = _Account(plan=plan)

    def known(self, api_key: str) -> bool:
        return api_key in self.accounts

    def _quota(self, api_key: str):
        return PLAN_QUOTA[self.accounts[api_key].plan]

    def allow(self, api_key: str) -> bool:
        acct = self.accounts[api_key]
        quota = self._quota(api_key)
        # Metered plans allow overage billing ($0.01/conv), so never hard-block;
        # a real deployment would gate on payment method instead of a cap.
        return quota is None or acct.used < quota or acct.plan is Plan.METERED

    def record(self, api_key: str) -> None:
        self.accounts[api_key].used += 1

    def snapshot(self, api_key: str) -> dict:
        acct = self.accounts[api_key]
        quota = self._quota(api_key)
        remaining = None if quota is None else max(0, quota - acct.used)
        overage = max(0, acct.used - quota) if quota is not None else 0
        return {
            "plan": acct.plan.value,
            "used": acct.used,
            "quota": quota,
            "remaining": remaining,
            "overage_conversions": overage,
            "overage_due_usd": round(overage * 0.01, 2),
        }
