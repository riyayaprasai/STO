"""
Validate live NLP sentiment scores against mock baseline values.

Fetches real data from Reddit and/or Twitter, runs VADER scoring,
and compares results to the hardcoded mock baselines in sentiment_service.py.

Usage:
    cd backend
    source venv/bin/activate
    python validate_live_scores.py

Requires at least one of REDDIT_CLIENT_ID or TWITTER_BEARER_TOKEN in .env.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from services.reddit_fetcher import fetch_reddit_posts
from services.twitter_fetcher import fetch_tweets
from services.nlp import score_split, score_texts
from services.sentiment_service import MOCK_BY_SYMBOL, MOCK_OVERVIEW

# Symbols to validate against mock baselines
TEST_SYMBOLS = ["AAPL", "GME", "AMC", "GOOGL", "MSFT"]

# Acceptable drift thresholds
SCORE_DRIFT_WARN = 0.15    # warn if live score differs from mock by more than this
SCORE_DRIFT_FAIL = 0.35    # fail if live score differs from mock by more than this
MIN_MENTIONS = 1           # need at least 1 mention to validate


def validate_symbol(symbol):
    """Fetch live data for a symbol and compare against mock baseline."""
    mock = MOCK_BY_SYMBOL.get(symbol)
    if not mock:
        return {"symbol": symbol, "status": "SKIP", "reason": "no mock baseline"}

    reddit_posts = fetch_reddit_posts(symbol, 30)
    tweets = fetch_tweets(symbol, 30)

    reddit_texts = [p["title"] + " " + p["body"] for p in reddit_posts]
    twitter_texts = [t["text"] for t in tweets]

    total = len(reddit_texts) + len(twitter_texts)

    if total == 0:
        return {
            "symbol": symbol,
            "status": "NO_DATA",
            "reason": "no posts/tweets returned (check API keys)",
            "reddit_count": 0,
            "twitter_count": 0,
        }

    scored = score_split(reddit_texts, twitter_texts)
    live_score = scored["overall_score"]
    live_label = scored["label"]
    mock_score = mock["score"]
    mock_label = mock["label"]
    drift = abs(live_score - mock_score)

    if drift > SCORE_DRIFT_FAIL:
        status = "FAIL"
    elif drift > SCORE_DRIFT_WARN:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "symbol": symbol,
        "status": status,
        "live_score": round(live_score, 4),
        "live_label": live_label,
        "mock_score": mock_score,
        "mock_label": mock_label,
        "drift": round(drift, 4),
        "reddit_count": len(reddit_texts),
        "twitter_count": len(twitter_texts),
        "reddit_score": scored.get("reddit_score"),
        "twitter_score": scored.get("twitter_score"),
    }


def validate_overview(symbol_results):
    """Compare aggregated live scores against the mock overview."""
    live_symbols_with_data = [r for r in symbol_results if r["status"] in ("PASS", "WARN", "FAIL")]

    if not live_symbols_with_data:
        return {"status": "SKIP", "reason": "no live data to aggregate"}

    live_avg = sum(r["live_score"] for r in live_symbols_with_data) / len(live_symbols_with_data)
    mock_avg = MOCK_OVERVIEW["overall_score"]
    drift = abs(live_avg - mock_avg)

    if drift > SCORE_DRIFT_FAIL:
        status = "FAIL"
    elif drift > SCORE_DRIFT_WARN:
        status = "WARN"
    else:
        status = "PASS"

    return {
        "status": status,
        "live_overall": round(live_avg, 4),
        "mock_overall": mock_avg,
        "drift": round(drift, 4),
        "symbols_with_data": len(live_symbols_with_data),
    }


def print_results(symbol_results, overview_result):
    """Print a formatted validation report."""
    print("\n" + "=" * 70)
    print("  STO LIVE vs MOCK SENTIMENT VALIDATION REPORT")
    print("=" * 70)

    # API status
    has_reddit = bool(os.environ.get("REDDIT_CLIENT_ID"))
    has_twitter = bool(os.environ.get("TWITTER_BEARER_TOKEN"))
    print(f"\n  Reddit API:  {'CONNECTED' if has_reddit else 'NOT CONFIGURED'}")
    print(f"  Twitter API: {'CONNECTED' if has_twitter else 'NOT CONFIGURED'}")

    # Per-symbol results
    print(f"\n{'Symbol':<8} {'Status':<8} {'Live':>8} {'Mock':>8} {'Drift':>8} {'Reddit':>8} {'Twitter':>8}")
    print("-" * 70)

    for r in symbol_results:
        if r["status"] in ("SKIP", "NO_DATA"):
            print(f"  {r['symbol']:<6} {r['status']:<8} {'--':>8} {'--':>8} {'--':>8} {r.get('reddit_count', '--'):>8} {r.get('twitter_count', '--'):>8}  {r.get('reason', '')}")
        else:
            status_icon = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[r["status"]]
            print(
                f"  {r['symbol']:<6} {status_icon:<8} {r['live_score']:>8.4f} {r['mock_score']:>8.2f} "
                f"{r['drift']:>8.4f} {r['reddit_count']:>8} {r['twitter_count']:>8}"
            )

    # Overview
    print("-" * 70)
    ov = overview_result
    if ov["status"] == "SKIP":
        print(f"  {'OVERALL':<6} {'SKIP':<8}  {ov.get('reason', '')}")
    else:
        print(
            f"  {'OVERALL':<6} {ov['status']:<8} {ov['live_overall']:>8.4f} {ov['mock_overall']:>8.2f} "
            f"{ov['drift']:>8.4f}"
        )

    # Summary
    print("\n" + "-" * 70)
    statuses = [r["status"] for r in symbol_results] + [ov["status"]]
    passes = statuses.count("PASS")
    warns = statuses.count("WARN")
    fails = statuses.count("FAIL")
    skips = statuses.count("SKIP") + statuses.count("NO_DATA")
    print(f"  PASS: {passes}  WARN: {warns}  FAIL: {fails}  SKIP: {skips}")

    if fails > 0:
        print("\n  RESULT: VALIDATION FAILED")
        print("  Some live scores differ significantly from mock baselines.")
        print("  This is expected — mock values are static, live data changes.")
        print("  Review the drifts above; update mocks if live data is stable.")
    elif warns > 0:
        print("\n  RESULT: VALIDATION PASSED WITH WARNINGS")
        print("  Live scores are within acceptable range but drifting from mocks.")
    elif passes > 0:
        print("\n  RESULT: VALIDATION PASSED")
        print("  Live NLP scores are consistent with mock baselines.")
    else:
        print("\n  RESULT: NO DATA")
        print("  Could not fetch any live data. Check API credentials in .env")

    print("=" * 70 + "\n")

    return fails == 0


def main():
    has_reddit = bool(os.environ.get("REDDIT_CLIENT_ID"))
    has_twitter = bool(os.environ.get("TWITTER_BEARER_TOKEN"))

    if not has_reddit and not has_twitter:
        print("\nERROR: No API credentials found in .env")
        print("Set at least one of: REDDIT_CLIENT_ID, TWITTER_BEARER_TOKEN")
        print("See .env.example for the required format.\n")
        sys.exit(1)

    print("\nFetching live data for validation...")
    symbol_results = []
    for symbol in TEST_SYMBOLS:
        print(f"  Fetching {symbol}...", end=" ", flush=True)
        result = validate_symbol(symbol)
        print(f"{result['status']}")
        symbol_results.append(result)

    overview_result = validate_overview(symbol_results)
    passed = print_results(symbol_results, overview_result)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
