"""
Конфигурация приложения
"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ====== PATHS ======
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# ====== TELEGRAM ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_IDS = [int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x]

# ====== REDDIT ======
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "HypeDetector/2.0")

CRYPTO_SUBREDDITS = [
    "cryptocurrency",
    "cryptomoonshots",
    "altcoin",
    "defi",
    "bitcoin",
    "ethereum",
    "binance",
    "solana",
    "cardano",
    "memecoins"
]

# ====== TWITTER ======
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# ====== ETHERSCAN ======
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

# ====== DATABASE ======
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./hype_detector.db")

# ====== REDIS ======
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ====== API URLS ======
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
FEAR_GREED_API_URL = "https://api.alternative.me/fng/"
WHALE_ALERT_API_URL = "https://api.whale-alert.io/v1"

# ====== SETTINGS ======
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "ru")
CACHE_TTL = int(os.getenv("CACHE_TTL", 300))  # 5 минут
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@TraiLight")

# Лимиты
FREE_ANALYSES_PER_DAY = 3
FREE_ALERTS_COUNT = 3

# Интервалы проверки (секунды)
ALERT_CHECK_INTERVAL = 60
TRENDING_UPDATE_INTERVAL = 300
WHALE_CHECK_INTERVAL = 30

# ====== HYPE THRESHOLDS ======
HYPE_THRESHOLDS = {
    "organic": (0, 20),
    "moderate": (20, 40),
    "high": (40, 60),
    "extreme": (60, 80),
    "danger": (80, 100)
}

# ====== ACHIEVEMENTS ======
ACHIEVEMENTS = {
    "first_analysis": {"name": "🔰 Первый анализ", "points": 10},
    "analyzer_10": {"name": "🔍 Аналитик", "points": 50},
    "analyzer_100": {"name": "🎯 Эксперт", "points": 200},
    "caught_pump": {"name": "🎣 Поймал памп", "points": 100},
    "avoided_dump": {"name": "🛡️ Избежал дамп", "points": 150},
    "whale_spotter": {"name": "🐋 Охотник на китов", "points": 75},
    "early_bird": {"name": "🐦 Ранняя пташка", "points": 50},
    "streak_7": {"name": "🔥 7 дней подряд", "points": 100},
    "streak_30": {"name": "💎 30 дней подряд", "points": 500},
}


# ====== ФУНКЦИИ ======

def is_admin(user_id: int) -> bool:
    """
    Проверка, является ли пользователь админом
    
    Args:
        user_id: Telegram ID пользователя
    
    Returns:
        True если админ, False если нет
    """
    return user_id in ADMIN_USER_IDS


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS