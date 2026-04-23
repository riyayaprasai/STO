from fastapi import APIRouter, Depends, HTTPException, Query
from services.yahoo import get_yahoo_news, get_ticker_info
from services.news_sources import get_all_news
from services.sentiment import enrich_news_with_sentiment
from typing import Optional, List, Dict
import re
from datetime import datetime
from services.google import get_google_news
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User

router = APIRouter()

def validate_ticker(ticker: str) -> str:
    """Validate and format ticker symbol."""
    # Remove any whitespace and convert to uppercase
    ticker = ticker.strip().upper()
    
    # Check if ticker matches basic stock symbol pattern
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker symbol. Please use 1-5 letter symbol (e.g., AAPL, MSFT, GOOGL)"
        )
    return ticker

@router.get("/{ticker}")
async def get_unified_news(
    ticker: str,
    include_company_info: bool = Query(True, description="Include detailed company information"),
    sentiment_threshold: Optional[float] = Query(
        None, 
        description="Filter by minimum sentiment score (-1 to 1)",
        ge=-1, 
        le=1
    ),
    time_range_hours: Optional[int] = Query(
        None,
        description="Filter news from last N hours",
        gt=0
    ),
    sources: List[str] = Query(
        ["yahoo", "reuters", "bloomberg", "marketwatch", "seekingalpha"],
        description="List of news sources to include"
    ),
    custom_domains: List[str] = Query(
        [],
        description="List of custom news domains (e.g., 'ft.com,wsj.com')"
    ),
    custom_names: List[str] = Query(
        [],
        description="List of display names for custom domains (e.g., 'Financial Times,Wall Street Journal')"
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get comprehensive financial news and analysis for a stock ticker.
    
    Parameters:
    - ticker: Stock symbol (e.g., AAPL, MSFT)
    - include_company_info: Whether to include detailed company information
    - sentiment_threshold: Filter news by minimum sentiment score (-1 to 1)
    - time_range_hours: Get news from the last N hours
    - sources: List of news sources to include
    - custom_domains: List of custom news domains (e.g., 'ft.com,wsj.com')
    - custom_names: List of display names for custom domains (must match length of custom_domains)
    
    Available default sources:
    - yahoo: Yahoo Finance
    - reuters: Reuters News
    - bloomberg: Bloomberg News
    - marketwatch: MarketWatch
    - seekingalpha: Seeking Alpha
    
    Returns:
    - Detailed company and market information
    - News articles from multiple sources
    - Sentiment analysis and trends
    - Market sentiment summary
    """
    try:
        # Validate ticker
        ticker = validate_ticker(ticker)
        
        # Process custom sources
        custom_sources = {}
        if len(custom_domains) != len(custom_names):
            raise HTTPException(
                status_code=400,
                detail="Number of custom domains must match number of custom names"
            )
            
        for domain, name in zip(custom_domains, custom_names):
            source_key = domain.split('.')[0].lower()  # Use first part of domain as key
            custom_sources[source_key] = {
                "domain": domain,
                "display_name": name
            }
            sources.append(source_key)  # Add custom source to sources list
        
        # Get company information if requested
        company_info = await get_ticker_info(ticker) if include_company_info else None
        
        # Get news from Yahoo Finance
        yahoo_news = await get_yahoo_news(ticker) if "yahoo" in sources else []
        
        # Get news from other sources
        other_news = await get_all_news(
            ticker, 
            sources=[s for s in sources if s != "yahoo"],
            custom_sources=custom_sources if custom_sources else None
        )
        
        # Process all news sources with sentiment analysis
        news_results = {}
        all_articles = []
        
        # Process Yahoo news
        if yahoo_news:
            yahoo_results = await enrich_news_with_sentiment(yahoo_news)
            news_results["yahoo"] = yahoo_results
            all_articles.extend(yahoo_results["articles"])
        
        # Process other sources
        for source, articles in other_news.items():
            if articles:
                source_results = await enrich_news_with_sentiment(articles)
                news_results[source] = source_results
                all_articles.extend(source_results["articles"])
        
        # Apply filters if specified
        if sentiment_threshold is not None:
            for source in news_results:
                news_results[source]["articles"] = [
                    article for article in news_results[source]["articles"]
                    if article["sentiment"]["score"] >= sentiment_threshold
                ]
        
        # Calculate overall metrics
        total_articles = sum(len(source["articles"]) for source in news_results.values())
        overall_sentiment = None
        if total_articles > 0:
            sentiment_sum = sum(
                source["summary"]["overall_sentiment"] * len(source["articles"])
                for source in news_results.values()
                if len(source["articles"]) > 0
            )
            overall_sentiment = sentiment_sum / total_articles
        
        return {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "company_info": company_info,
            "market_sentiment": {
                "overall_score": overall_sentiment,
                "total_articles": total_articles,
                "sources": {
                    source: results["summary"]
                    for source, results in news_results.items()
                }
            },
            "news": {
                source: results["articles"]
                for source, results in news_results.items()
            }
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )