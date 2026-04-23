import feedparser
import yfinance as yf
import aiohttp
import asyncio
from datetime import datetime, timedelta
from exceptions import (
    TickerValidationError,
    DataFetchError,
    RateLimitError,
    InvalidDataError
)
from logging_config import logger

async def get_yahoo_news(ticker: str):
    """Get news from Yahoo Finance RSS feed."""
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        
        # feedparser doesn't support async, but it's fast enough to run in the main thread
        feed = feedparser.parse(url)

        if feed.bozo:  # feedparser encountered an error
            logger.error(f"Feed parsing error for {ticker}: {feed.bozo_exception}")
            raise InvalidDataError(f"Failed to parse Yahoo Finance feed for {ticker}")

        headlines = []
        for entry in feed.entries:
            try:
                headlines.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published,
                    "source": "Yahoo",
                    "summary": entry.get("summary", ""),
                    "published_parsed": datetime.fromtimestamp(
                        datetime(*entry.published_parsed[:6]).timestamp()
                    ).isoformat()
                })
            except (AttributeError, ValueError) as e:
                logger.warning(f"Error processing news entry for {ticker}: {str(e)}")
                continue

        logger.info(f"Successfully fetched {len(headlines)} news items for {ticker}")
        return headlines

    except Exception as e:
        logger.error(f"Error fetching Yahoo news for {ticker}: {str(e)}")
        raise DataFetchError(f"Failed to fetch news from Yahoo Finance: {str(e)}")

async def get_ticker_info(ticker: str):
    """Get detailed company and stock information using yfinance."""
    try:
        # Validate ticker format
        if not isinstance(ticker, str) or not ticker.strip():
            raise TickerValidationError("Ticker symbol cannot be empty")
        
        ticker = ticker.strip().upper()
        if not ticker.isalpha() or len(ticker) > 5:
            raise TickerValidationError(
                "Invalid ticker symbol. Please use 1-5 letter symbol (e.g., AAPL, MSFT, GOOGL)"
            )

        # yfinance operations are blocking, run them in a thread pool
        loop = asyncio.get_event_loop()
        
        try:
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)
        except Exception as e:
            logger.error(f"Error creating Ticker object for {ticker}: {str(e)}")
            raise DataFetchError(f"Failed to initialize stock data for {ticker}")

        try:
            info = await loop.run_in_executor(None, lambda: stock.info)
            if not info:
                raise InvalidDataError(f"No data found for ticker {ticker}")
        except Exception as e:
            logger.error(f"Error fetching stock info for {ticker}: {str(e)}")
            raise DataFetchError(f"Failed to fetch stock information for {ticker}")

        # Get historical data for price analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        try:
            history = await loop.run_in_executor(
                None, 
                lambda: stock.history(start=start_date, end=end_date)
            )
        except Exception as e:
            logger.warning(f"Could not fetch historical data for {ticker}: {str(e)}")
            history = None

        # Calculate price metrics
        if history is not None and not history.empty:
            try:
                current_price = history['Close'].iloc[-1]
                price_change = current_price - history['Close'].iloc[0]
                price_change_pct = (price_change / history['Close'].iloc[0]) * 100
                high_30d = history['High'].max()
                low_30d = history['Low'].min()
                avg_volume = history['Volume'].mean()
            except Exception as e:
                logger.warning(f"Error calculating price metrics for {ticker}: {str(e)}")
                current_price = price_change = price_change_pct = high_30d = low_30d = avg_volume = None
        else:
            current_price = price_change = price_change_pct = high_30d = low_30d = avg_volume = None

        # Prepare response data
        try:
            response_data = {
                "company_info": {
                    "name": info.get("longName"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "description": info.get("longBusinessSummary"),
                    "website": info.get("website"),
                    "country": info.get("country"),
                    "employees": info.get("fullTimeEmployees"),
                    "ceo": info.get("companyOfficers", [{}])[0].get("name") if info.get("companyOfficers") else None
                },
                "market_data": {
                    "current_price": current_price,
                    "currency": info.get("currency"),
                    "market_cap": info.get("marketCap"),
                    "price_change_30d": price_change,
                    "price_change_pct_30d": price_change_pct,
                    "high_30d": high_30d,
                    "low_30d": low_30d,
                    "avg_volume_30d": avg_volume,
                    "pe_ratio": info.get("trailingPE"),
                    "dividend_yield": info.get("dividendYield"),
                    "beta": info.get("beta"),
                    "52_week_high": info.get("fiftyTwoWeekHigh"),
                    "52_week_low": info.get("fiftyTwoWeekLow")
                },
                "analyst_data": {
                    "target_price": info.get("targetMeanPrice"),
                    "recommendation": info.get("recommendationKey"),
                    "num_analysts": info.get("numberOfAnalystOpinions"),
                    "profit_margins": info.get("profitMargins")
                }
            }
            
            logger.info(f"Successfully fetched company info for {ticker}")
            return response_data

        except Exception as e:
            logger.error(f"Error preparing response data for {ticker}: {str(e)}")
            raise InvalidDataError(f"Failed to process company information for {ticker}")

    except (TickerValidationError, DataFetchError, InvalidDataError) as e:
        # Re-raise specific exceptions
        raise e
    except Exception as e:
        # Log unexpected errors and raise generic error
        logger.error(f"Unexpected error in get_ticker_info for {ticker}: {str(e)}")
        raise DataFetchError(f"An unexpected error occurred while fetching data for {ticker}") 