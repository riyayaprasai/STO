from textblob import TextBlob
import asyncio
from datetime import datetime, timedelta

async def analyze_sentiment(text: str) -> dict:
    """Analyze sentiment of text using TextBlob with enhanced metrics."""
    # TextBlob is CPU-bound, run in thread pool
    loop = asyncio.get_event_loop()
    analysis = await loop.run_in_executor(None, TextBlob, text)
    
    # Get both polarity and subjectivity
    polarity = analysis.sentiment.polarity
    subjectivity = analysis.sentiment.subjectivity
    
    # Determine sentiment category with more granular classification
    if polarity > 0.5:
        sentiment = "very positive"
    elif polarity > 0.1:
        sentiment = "positive"
    elif polarity < -0.5:
        sentiment = "very negative"
    elif polarity < -0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Determine subjectivity category
    if subjectivity > 0.7:
        subjectivity_category = "very subjective"
    elif subjectivity > 0.3:
        subjectivity_category = "somewhat subjective"
    else:
        subjectivity_category = "objective"
    
    return {
        "sentiment": {
            "category": sentiment,
            "score": polarity,
            "subjectivity": {
                "category": subjectivity_category,
                "score": subjectivity
            }
        }
    }

async def enrich_news_with_sentiment(news_items: list) -> dict:
    """Add sentiment analysis to a list of news items with aggregated metrics."""
    if not news_items:
        return {"articles": [], "summary": {}}
    
    # Analyze each article
    for item in news_items:
        sentiment_data = await analyze_sentiment(item["title"])
        item.update(sentiment_data)
    
    # Calculate aggregate sentiment metrics
    sentiment_scores = [item["sentiment"]["score"] for item in news_items]
    subjectivity_scores = [item["sentiment"]["subjectivity"]["score"] for item in news_items]
    
    # Count sentiment categories
    sentiment_distribution = {
        "very_positive": len([i for i in news_items if i["sentiment"]["category"] == "very positive"]),
        "positive": len([i for i in news_items if i["sentiment"]["category"] == "positive"]),
        "neutral": len([i for i in news_items if i["sentiment"]["category"] == "neutral"]),
        "negative": len([i for i in news_items if i["sentiment"]["category"] == "negative"]),
        "very_negative": len([i for i in news_items if i["sentiment"]["category"] == "very negative"])
    }
    
    # Calculate time-based metrics if timestamps are available
    recent_sentiment = None
    if all("published_parsed" in item for item in news_items):
        recent_items = [
            item for item in news_items 
            if datetime.fromisoformat(item["published_parsed"]) > datetime.now() - timedelta(hours=24)
        ]
        if recent_items:
            recent_sentiment = sum(item["sentiment"]["score"] for item in recent_items) / len(recent_items)
    
    return {
        "articles": news_items,
        "summary": {
            "overall_sentiment": sum(sentiment_scores) / len(sentiment_scores),
            "sentiment_distribution": sentiment_distribution,
            "recent_24h_sentiment": recent_sentiment,
            "average_subjectivity": sum(subjectivity_scores) / len(subjectivity_scores),
            "total_articles": len(news_items)
        }
    } 