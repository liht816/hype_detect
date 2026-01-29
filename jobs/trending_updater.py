"""
Обновление трендов
"""
import logging
from datetime import datetime

from services import CoinGeckoService, RedditAnalyzer
from database.connection import async_session
from database.models import TrendingSnapshot

logger = logging.getLogger(__name__)


class TrendingUpdater:
    """Обновление трендовых монет"""
    
    def __init__(self):
        self.coingecko = CoinGeckoService()
    
    async def update_trending(self):
        """Обновление трендов из всех источников"""
        try:
            # CoinGecko trending
            cg_trending = await self.coingecko.get_trending()
            
            if cg_trending:
                await self._save_snapshot(
                    coins=[
                        {
                            "id": t.get("item", {}).get("id"),
                            "name": t.get("item", {}).get("name"),
                            "symbol": t.get("item", {}).get("symbol"),
                            "rank": t.get("item", {}).get("market_cap_rank"),
                        }
                        for t in cg_trending[:10]
                    ],
                    source="coingecko"
                )
            
            # Reddit trending (реже, чтобы не спамить API)
            # Можно добавить отдельный интервал
            
            logger.debug("✅ Trending updated")
            
        except Exception as e:
            logger.error(f"❌ Trending update error: {e}")
    
    async def _save_snapshot(self, coins: list, source: str):
        """Сохранение снимка трендов"""
        async with async_session() as session:
            snapshot = TrendingSnapshot(
                coins=coins,
                source=source,
                created_at=datetime.utcnow()
            )
            session.add(snapshot)
            await session.commit()