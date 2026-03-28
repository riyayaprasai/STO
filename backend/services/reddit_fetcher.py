import os
from typing import Dict, List, Any

import praw


def fetch_reddit_posts(symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        user_agent = os.environ.get("REDDIT_USER_AGENT")

        if not all([client_id, client_secret, user_agent]):
            return []

        if not isinstance(limit, int) or limit <= 0:
            return []

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        subreddits = ["wallstreetbets", "stocks", "investing"]
        results: List[Dict[str, Any]] = []

        remaining = limit
        for subreddit_name in subreddits:
            if remaining <= 0:
                break

            subreddit = reddit.subreddit(subreddit_name)
            for submission in subreddit.search(symbol, limit=remaining):
                results.append(
                    {
                        "id": getattr(submission, "id", None),
                        "title": getattr(submission, "title", "") or "",
                        "body": getattr(submission, "selftext", "") or "",
                        "score": getattr(submission, "score", 0),
                        "created_utc": getattr(submission, "created_utc", None),
                        "subreddit": getattr(
                            getattr(submission, "subreddit", None),
                            "display_name",
                            subreddit_name,
                        ),
                    }
                )
                remaining -= 1

                if remaining <= 0:
                    break

        return results
    except Exception:
        return []

