"""
Экспорт сервисов
"""
from services.coingecko import CoinGeckoService
from services.google_trends import GoogleTrendsService
from services.whale_tracker import WhaleTracker
from services.fear_greed_api import FearGreedService
from services.news_aggregator import NewsAggregator
from services.github_analyzer import GitHubAnalyzer
from .reddit_analyzer import RedditAnalyzer

__all__ = [
    "CoinGeckoService",
    "GoogleTrendsService",
    "WhaleTracker",
    "FearGreedService",
    "NewsAggregator",
    "GitHubAnalyzer",
]
