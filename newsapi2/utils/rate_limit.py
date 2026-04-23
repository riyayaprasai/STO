"""
In-memory sliding-window rate limiter.

Two windows are tracked per API key:
  - per-minute  (short burst limit)
  - per-day     (daily quota)

Thread safety: this is suitable for single-process deployments (SQLite / uvicorn
with one worker). For multi-process deployments, replace with a Redis-backed store.
"""
import time
from collections import defaultdict
from config import TIER_LIMITS


class RateLimitStore:
    def __init__(self) -> None:
        # api_key -> {"minute": [timestamps], "day": [timestamps]}
        self._store: dict = defaultdict(lambda: {"minute": [], "day": []})

    def check_and_record(self, api_key: str, tier: str) -> tuple[bool, dict]:
        """
        Check whether this request is within limits and record it if so.

        Returns (allowed, rate_info_dict).
        rate_info_dict always contains:
          - limit, remaining, reset (per-minute window, kept for compatibility)
          - limit_day, remaining_day, reset_day (per-day window)
        On denial it also contains: exhausted_type ("minute" | "daily").
        """
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        now = time.time()
        record = self._store[api_key]

        # Prune timestamps outside their window
        record["minute"] = [t for t in record["minute"] if now - t < 60]
        record["day"] = [t for t in record["day"] if now - t < 86_400]

        per_minute: int | None = limits["per_minute"]
        daily: int | None = limits["daily"]

        # Per-minute check
        if per_minute is not None and len(record["minute"]) >= per_minute:
            oldest = min(record["minute"])
            return False, {
                "limit": per_minute,
                "remaining": 0,
                "reset": int(oldest + 60),
                "limit_day": daily if daily is not None else None,
                "remaining_day": max((daily - len(record["day"])), 0) if daily is not None else None,
                "reset_day": int(min(record["day"]) + 86_400) if record["day"] else int(now + 86_400),
                "exhausted_type": "minute",
            }

        # Daily check
        if daily is not None and len(record["day"]) >= daily:
            oldest = min(record["day"])
            return False, {
                "limit": per_minute if per_minute is not None else 999_999,
                "remaining": 0,
                "reset": int(now + 60),
                "limit_day": daily,
                "remaining_day": 0,
                "reset_day": int(oldest + 86_400),
                "exhausted_type": "daily",
            }

        # Record this request
        record["minute"].append(now)
        record["day"].append(now)

        effective_limit_minute = per_minute if per_minute is not None else None
        remaining_minute = (per_minute - len(record["minute"])) if per_minute is not None else None

        effective_limit_day = daily if daily is not None else None
        remaining_day = (daily - len(record["day"])) if daily is not None else None

        # Reset times are "start of window + window_size"
        reset_minute = int(min(record["minute"]) + 60) if record["minute"] else int(now + 60)
        reset_day = int(min(record["day"]) + 86_400) if record["day"] else int(now + 86_400)

        return True, {
            # Compatibility (existing clients/docs): minute window
            "limit": effective_limit_minute if effective_limit_minute is not None else 999_999,
            "remaining": remaining_minute if remaining_minute is not None else 999_999,
            "reset": reset_minute,
            # Explicit day window
            "limit_day": effective_limit_day,
            "remaining_day": remaining_day,
            "reset_day": reset_day,
        }


rate_limit_store = RateLimitStore()
