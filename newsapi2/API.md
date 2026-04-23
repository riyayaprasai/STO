# Finance News API Documentation

## Overview
The Finance News API provides comprehensive financial news and market data aggregation with sentiment analysis. This API requires authentication using API keys.

## Base URL
```
http://localhost:8000
```

## Authentication
All endpoints require API key authentication. Include your API key in the `X-API-Key` header with every request.

Example:
```python
import requests

headers = {
    "X-Api-Key": "your_api_key_here"
}

response = requests.get("http://localhost:8000/api/news/AAPL", headers=headers)
```

## News Endpoints

### GET /api/news/{ticker}
Get news and analysis for a specific stock ticker.

#### Parameters
- ticker (path): Stock symbol (e.g., AAPL, MSFT)
- include_company_info (query): Include detailed company information (default: true)
- sentiment_threshold (query): Filter by minimum sentiment score (-1 to 1)
- time_range_hours (query): Filter news from last N hours
- sources (query): List of news sources to include

#### Example Request
```python
import requests

headers = {
    "X-Api-Key": "your_api_key_here"
}

response = requests.get(
    "http://localhost:8000/api/news/AAPL",
    params={
        "sentiment_threshold": 0.2,
        "time_range_hours": 24,
        "sources": ["reuters", "bloomberg"]
    },
    headers=headers
)
```

## Error Handling
The API uses standard HTTP status codes and returns detailed error messages:

- 400: Bad Request - Invalid input parameters
- 401: Unauthorized - Missing API key
- 403: Forbidden - Invalid API key
- 404: Not Found - Resource not found
- 500: Internal Server Error - Server-side error

## Rate Limiting
Rate limiting is enforced per API key and varies by user tier. Two windows are tracked:
- per-minute (burst)
- per-day (quota)

Rate limit response headers are attached to every authenticated response:
- `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (per-minute)
- `X-RateLimit-Limit-Day`, `X-RateLimit-Remaining-Day`, `X-RateLimit-Reset-Day` (per-day)

On limit exhaustion:
- `429` for per-minute bursts (`rateLimited`)
- `403` for per-day quota exhaustion (`apiKeyExhausted`)

Note: the current implementation uses an in-memory store (single-process). If you run multiple workers/processes, limits will not be shared across them.

### Tiers
Tiers are stored on each user as `tier` and currently affect:
- Rate limits (see `config.py` `TIER_LIMITS`)
- Historical article access window (see `config.py` `TIER_HISTORY_DAYS`)

Default tiers:
- `free`
- `developer`
- `business`
- `enterprise`

## Best Practices
1. Keep your API key secure and never share it
2. Use HTTPS for all API requests
3. Implement proper error handling in your applications
4. Monitor your API usage
5. Contact support if you need a new API key or have issues with existing ones

## Support
For support or to request a new API key, please contact:
- Email: pratyushkhanal95@gmail.com
- GitHub: https://github.com/pratyushkhanal

## Versioning
The API is currently at version 1.0.0. All future updates will maintain backward compatibility.

## License
This API is licensed under the Apache 2.0 License. 