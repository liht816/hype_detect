"""
Экспорт репозиториев
"""
from database.repositories.user_repo import UserRepository
from database.repositories.watchlist_repo import WatchlistRepository
from database.repositories.alert_repo import AlertRepository
from database.repositories.analysis_repo import AnalysisRepository

__all__ = [
    "UserRepository",
    "WatchlistRepository", 
    "AlertRepository",
    "AnalysisRepository"
]