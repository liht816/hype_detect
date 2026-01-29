"""
Экспорт сервисов
"""
from services.coingecko import CoinGeckoService
from services.reddit_analyzer import RedditAnalyzer
from services.twitter_analyzer import TwitterAnalyzer
from services.google_trends import GoogleTrendsService
from services.whale_tracker import WhaleTracker
from services.fear_greed_api import FearGreedService
from services.news_aggregator import NewsAggregator
from services.github_analyzer import GitHubAnalyzer

__all__ = [
    "CoinGeckoService",
    "RedditAnalyzer",
    "TwitterAnalyzer",
    "GoogleTrendsService",
    "WhaleTracker",
    "FearGreedService",
    "NewsAggregator",
    "GitHubAnalyzer",
]