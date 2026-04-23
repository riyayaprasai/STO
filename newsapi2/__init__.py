"""
NewsAPI - A Python package for fetching and processing news from various sources
"""

__version__ = "0.1.0"

from .main import app
from .services import news_service
from .utils import news_parser

__all__ = [
    'app',
    'news_service',
    'news_parser',
    '__version__'
]
