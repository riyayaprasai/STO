"""
Authentication and per-request rate-limit enforcement.

API keys are accepted via:
  - X-Api-Key request header  (preferred)
  - apiKey query parameter     (convenience, e.g. ?apiKey=YOUR_KEY)

Rate-limit headers are injected into every response:
  X-RateLimit-Limit     – requests allowed in the current window
  X-RateLimit-Remaining – requests left in this window
  X-RateLimit-Reset     – Unix timestamp when the window resets
"""
from fastapi import Depends, HTTPException, Query, Response, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session

from database import get_db
from models import User, get_user_by_api_key
from utils.rate_limit import rate_limit_store

_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)


def _api_error(status: int, code: str, message: str):
    raise HTTPException(
        status_code=status,
        detail={"status": "error", "code": code, "message": message},
    )


def get_current_user(
    response: Response,
    api_key_hdr: str | None = Security(_api_key_header),
    api_key_query: str | None = Query(None, alias="apiKey"),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate the API key, enforce rate limits, and attach rate-limit headers
    to the response.  Returns the authenticated User ORM object.
    """
    api_key = api_key_hdr or api_key_query

    if not api_key:
        _api_error(401, "apiKeyMissing",
                   "Your API key is missing. Pass it in the X-Api-Key header "
                   "or as the apiKey query parameter.")

    user: User | None = get_user_by_api_key(db, api_key)
    if not user:
        _api_error(401, "apiKeyInvalid", "Your API key is invalid.")

    if not user.is_active:
        _api_error(401, "apiKeyDisabled", "Your API key has been disabled.")

    allowed, rate_info = rate_limit_store.check_and_record(user.api_key, user.tier)

    # Always attach rate-limit headers so clients can inspect their quota
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

    # Day window (None = unlimited)
    if rate_info.get("limit_day") is not None:
        response.headers["X-RateLimit-Limit-Day"] = str(rate_info["limit_day"])
        response.headers["X-RateLimit-Remaining-Day"] = str(rate_info["remaining_day"])
        response.headers["X-RateLimit-Reset-Day"] = str(rate_info["reset_day"])
    else:
        response.headers["X-RateLimit-Limit-Day"] = "unlimited"
        response.headers["X-RateLimit-Remaining-Day"] = "unlimited"
        response.headers["X-RateLimit-Reset-Day"] = str(rate_info.get("reset_day", rate_info["reset"]))

    if not allowed:
        exhausted_type = rate_info.get("exhausted_type", "minute")
        if exhausted_type == "daily":
            _api_error(403, "apiKeyExhausted",
                       "You have used up all of your daily requests. "
                       "Upgrade your plan or wait for the quota to reset.")
        _api_error(429, "rateLimited",
                   "You have exceeded your per-minute rate limit. "
                   "Please slow down your requests.")

    return user


# Kept for backward-compatibility with the legacy /api/news route
validate_api_key = get_current_user
