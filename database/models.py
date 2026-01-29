"""
SQLAlchemy модели
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, Text, JSON, BigInteger
)
from sqlalchemy.orm import relationship
from database.connection import Base


class User(Base):
    """Пользователь бота"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    language = Column(String(10), default="ru")
    
    # Статистика
    analyses_count = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    
    daily_analysis_limit = Column(Integer, nullable=True)  
# None -> дефолт FREE_ANALYSES_PER_DAY
# -1 -> безлимит
    # Настройки
    notifications_enabled = Column(Boolean, default=True)
    quiet_hours_start = Column(Integer, nullable=True)
    quiet_hours_end = Column(Integer, nullable=True)
    alert_threshold = Column(Integer, default=60)
    
    # Премиум
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False)
    granted_by = Column(BigInteger, nullable=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    streak_days = Column(Integer, default=0)
    last_streak_date = Column(DateTime, nullable=True)
    
    # Связи
    watchlist = relationship("WatchlistItem", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    portfolio = relationship("PortfolioItem", back_populates="user", cascade="all, delete-orphan")
    
    def has_premium_access(self) -> bool:
        """Проверка премиум доступа"""
        from config import is_admin
        
        # Админы всегда имеют доступ
        if is_admin(self.telegram_id):
            return True
        
        # Проверяем премиум
        if self.is_premium:
            if self.premium_until is None:
                return True  # Бессрочный
            return datetime.utcnow() < self.premium_until
        
        return False

class WatchlistItem(Base):
    """Элемент списка отслеживания"""
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    coin_id = Column(String(100), nullable=False)  # CoinGecko ID
    coin_symbol = Column(String(20), nullable=False)
    coin_name = Column(String(100), nullable=False)
    
    added_at = Column(DateTime, default=datetime.utcnow)
    added_price = Column(Float, nullable=True)  # Цена при добавлении
    added_hype_score = Column(Integer, nullable=True)
    
    # Настройки уведомлений для этой монеты
    notify_hype_change = Column(Boolean, default=True)
    notify_price_change = Column(Boolean, default=True)
    notify_whale_activity = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="watchlist")


class Alert(Base):
    """Настроенный алерт"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Тип алерта
    alert_type = Column(String(50), nullable=False)
    # Типы: hype_spike, price_change, whale_move, trending, new_listing
    
    coin_id = Column(String(100), nullable=True)  # Null = все монеты
    coin_symbol = Column(String(20), nullable=True)
    
    # Условия
    condition = Column(JSON, nullable=True)
    # Пример: {"hype_change": ">50", "price_change": ">10"}
    
    # Статус
    is_active = Column(Boolean, default=True)
    triggered_count = Column(Integer, default=0)
    last_triggered = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="alerts")


class AnalysisHistory(Base):
    """История анализов"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    coin_id = Column(String(100), nullable=False)
    coin_symbol = Column(String(20), nullable=False)
    coin_name = Column(String(100), nullable=False)
    
    # Результаты анализа
    hype_score = Column(Integer, nullable=False)
    price_at_analysis = Column(Float, nullable=True)
    market_cap_rank = Column(Integer, nullable=True)
    
    # Детали
    reddit_mentions = Column(Integer, default=0)
    twitter_mentions = Column(Integer, default=0)
    sentiment_score = Column(Float, nullable=True)
    
    # Прогноз пользователя (для геймификации)
    user_prediction = Column(String(20), nullable=True)  # "pump", "dump", "stable"
    prediction_result = Column(String(20), nullable=True)  # Реальный результат
    prediction_checked = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="analyses")


class UserAchievement(Base):
    """Достижения пользователя"""
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(String(50), nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="achievements")


class PortfolioItem(Base):
    """Элемент портфолио"""
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    coin_id = Column(String(100), nullable=False)
    coin_symbol = Column(String(20), nullable=False)
    
    amount = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    buy_date = Column(DateTime, default=datetime.utcnow)
    
    notes = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="portfolio")


class CoinCache(Base):
    """Кэш данных о монетах"""
    __tablename__ = "coin_cache"
    
    id = Column(Integer, primary_key=True)
    coin_id = Column(String(100), unique=True, nullable=False, index=True)
    
    data = Column(JSON, nullable=False)
    hype_data = Column(JSON, nullable=True)
    
    updated_at = Column(DateTime, default=datetime.utcnow)


class TrendingSnapshot(Base):
    """Снимки трендовых монет"""
    __tablename__ = "trending_snapshots"
    
    id = Column(Integer, primary_key=True)
    coins = Column(JSON, nullable=False)  # Список трендовых
    source = Column(String(50), nullable=False)  # coingecko, twitter, reddit
    created_at = Column(DateTime, default=datetime.utcnow)