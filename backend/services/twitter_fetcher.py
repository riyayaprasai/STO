import logging
import os
from typing import Any, Dict, List

import tweepy

logger = logging.getLogger(__name__)


def fetch_tweets(symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
        if not bearer_token:
            return []

        if not isinstance(limit, int) or limit <= 0:
            return []

        query = f"${symbol} -is:retweet lang:en"

        # Tweepy v2 search API returns Tweet objects with optional public metrics
        client = tweepy.Client(bearer_token=bearer_token)
        response = client.search_recent_tweets(
            query=query,
            max_results=min(limit, 100),
            tweet_fields=["created_at", "public_metrics"],
        )

        tweets = response.data or []
        results: List[Dict[str, Any]] = []
        for tweet in tweets:
            public_metrics = getattr(tweet, "public_metrics", None) or {}
            like_count = (
                getattr(public_metrics, "like_count", None)
                if hasattr(public_metrics, "like_count")
                else public_metrics.get("like_count", 0)
            )
            retweet_count = (
                getattr(public_metrics, "retweet_count", None)
                if hasattr(public_metrics, "retweet_count")
                else public_metrics.get("retweet_count", 0)
            )

            results.append(
                {
                    "id": getattr(tweet, "id", None),
                    "text": getattr(tweet, "text", "") or "",
                    "created_at": getattr(tweet, "created_at", None),
                    "like_count": like_count,
                    "retweet_count": retweet_count,
                }
            )

        return results
    except tweepy.errors.TooManyRequests as e:
        logger.warning("Twitter rate limit hit in fetch_tweets: %s", e)
        return []
    except Exception:
        return []

