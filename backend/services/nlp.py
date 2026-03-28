from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def score_texts(texts: list[str]) -> dict:
    analyzer = SentimentIntensityAnalyzer()

    volume = len(texts)
    if volume == 0:
        avg_compound = 0.0
    else:
        compounds = [
            analyzer.polarity_scores(text or "").get("compound", 0.0) for text in texts
        ]
        avg_compound = sum(compounds) / len(compounds) if compounds else 0.0

    overall_score = (avg_compound + 1) / 2  # map [-1, 1] -> [0, 1]

    if avg_compound > 0.05:
        label = "positive"
    elif avg_compound < -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {
        "overall_score": float(overall_score),
        "label": label,
        "volume": volume,
        "reddit_score": None,
        "twitter_score": None,
    }


def score_split(reddit_texts: list[str], twitter_texts: list[str]) -> dict:
    reddit_result = score_texts(reddit_texts)
    twitter_result = score_texts(twitter_texts)

    reddit_volume = reddit_result["volume"]
    twitter_volume = twitter_result["volume"]
    total_volume = reddit_volume + twitter_volume

    # Convert back to compound for a weighted average (linear mapping)
    reddit_compound = reddit_result["overall_score"] * 2 - 1
    twitter_compound = twitter_result["overall_score"] * 2 - 1

    if total_volume == 0:
        avg_compound = 0.0
    else:
        avg_compound = (
            reddit_compound * reddit_volume + twitter_compound * twitter_volume
        ) / total_volume

    overall_score = (avg_compound + 1) / 2

    if avg_compound > 0.05:
        label = "positive"
    elif avg_compound < -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {
        "overall_score": float(overall_score),
        "label": label,
        "volume": total_volume,
        "reddit_score": float(reddit_result["overall_score"])
        if reddit_volume > 0
        else None,
        "twitter_score": float(twitter_result["overall_score"])
        if twitter_volume > 0
        else None,
    }

