"""
Structured error responses aligned with the News API PRD (section 5).

All errors share the shape:
    { "status": "error", "code": "<camelCase code>", "message": "..." }
"""
from fastapi import HTTPException


class NewsAPIError(HTTPException):
    """Base exception that produces a PRD-compliant JSON error body."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(
            status_code=status_code,
            detail={"status": "error", "code": code, "message": message},
        )


# ── 4xx client errors ────────────────────────────────────────────────────────

class ParameterInvalidError(NewsAPIError):
    def __init__(self, message: str) -> None:
        super().__init__(400, "parameterInvalid", message)


class ParametersMissingError(NewsAPIError):
    def __init__(self, message: str) -> None:
        super().__init__(400, "parametersMissing", message)


class ApiKeyMissingError(NewsAPIError):
    def __init__(self) -> None:
        super().__init__(401, "apiKeyMissing",
                         "Your API key is missing.")


class ApiKeyInvalidError(NewsAPIError):
    def __init__(self) -> None:
        super().__init__(401, "apiKeyInvalid",
                         "Your API key is invalid.")


class ApiKeyDisabledError(NewsAPIError):
    def __init__(self) -> None:
        super().__init__(401, "apiKeyDisabled",
                         "Your API key has been disabled.")


class ApiKeyExhaustedError(NewsAPIError):
    def __init__(self) -> None:
        super().__init__(403, "apiKeyExhausted",
                         "You have used up all of your daily requests.")


class PlanUpgradeRequiredError(NewsAPIError):
    def __init__(self, message: str = "This feature is not available on your current plan.") -> None:
        super().__init__(403, "planUpgradeRequired", message)


class RateLimitedError(NewsAPIError):
    def __init__(self) -> None:
        super().__init__(429, "rateLimited",
                         "You have exceeded your per-minute rate limit.")


# ── 5xx server errors ────────────────────────────────────────────────────────

class ServerError(NewsAPIError):
    def __init__(self, message: str = "An internal server error occurred.") -> None:
        super().__init__(500, "serverError", message)


class DataFetchError(NewsAPIError):
    def __init__(self, message: str = "Failed to fetch data from an upstream source.") -> None:
        super().__init__(503, "dataFetchError", message)
