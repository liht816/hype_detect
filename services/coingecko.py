"""
CoinGecko API сервис
"""
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from config import COINGECKO_BASE_URL, CACHE_TTL


class CoinGeckoService:
    """Сервис для работы с CoinGecko API"""
    
    def __init__(self):
        self.base_url = COINGECKO_BASE_URL
        self._cache = {}
        self._cache_times = {}
    
    def _is_cache_valid(self, key: str) -> bool:
        """Проверка валидности кэша"""
        if key not in self._cache_times:
            return False
        return (datetime.now() - self._cache_times[key]).seconds < CACHE_TTL
    
    async def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Базовый запрос к API"""
        cache_key = f"{endpoint}:{str(params)}"
        
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}{endpoint}",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._cache[cache_key] = data
                        self._cache_times[cache_key] = datetime.now()
                        return data
                    elif resp.status == 429:
                        # Rate limit - ждём и повторяем
                        await asyncio.sleep(60)
                        return await self._request(endpoint, params)
        except Exception as e:
            print(f"CoinGecko API error: {e}")
        
        return None
    
    async def search_coin(self, query: str) -> Optional[dict]:
        """
        Поиск монеты по названию или тикеру
        
        Returns:
            {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc", ...}
        """
        data = await self._request("/search", {"query": query})
        if data and data.get("coins"):
            return data["coins"][0]
        return None
    
    async def get_coin_data(self, coin_id: str) -> Optional[dict]:
        """
        Получить полные данные о монете
        
        Returns:
            Полный объект монеты с market_data, community_data и т.д.
        """
        return await self._request(
            f"/coins/{coin_id}",
            {
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "true",
                "developer_data": "true",
                "sparkline": "false"
            }
        )
    
    async def get_price(self, coin_id: str) -> Optional[float]:
        """Получить текущую цену"""
        data = await self._request(
            "/simple/price",
            {"ids": coin_id, "vs_currencies": "usd"}
        )
        if data and coin_id in data:
            return data[coin_id].get("usd")
        return None
    
    async def get_prices_batch(self, coin_ids: list[str]) -> dict:
        """Получить цены для нескольких монет"""
        ids_str = ",".join(coin_ids)
        data = await self._request(
            "/simple/price",
            {"ids": ids_str, "vs_currencies": "usd", "include_24hr_change": "true"}
        )
        return data or {}
    
    async def get_price_history(
        self, 
        coin_id: str, 
        days: int = 7
    ) -> list[tuple[int, float]]:
        """
        История цен
        
        Returns:
            [(timestamp_ms, price), ...]
        """
        data = await self._request(
            f"/coins/{coin_id}/market_chart",
            {"vs_currency": "usd", "days": days}
        )
        if data:
            return data.get("prices", [])
        return []
    
    async def get_ohlc(self, coin_id: str, days: int = 7) -> list:
        """OHLC данные для свечного графика"""
        data = await self._request(
            f"/coins/{coin_id}/ohlc",
            {"vs_currency": "usd", "days": days}
        )
        return data or []
    
    async def get_trending(self) -> list[dict]:
        """
        Трендовые монеты
        
        Returns:
            [{"item": {"id": "...", "name": "...", "symbol": "...", ...}}, ...]
        """
        data = await self._request("/search/trending")
        if data:
            return data.get("coins", [])
        return []
    
    async def get_global_data(self) -> Optional[dict]:
        """Глобальные данные рынка"""
        data = await self._request("/global")
        if data:
            return data.get("data")
        return None
    
    async def get_top_gainers_losers(self, limit: int = 10) -> dict:
        """Топ растущих и падающих монет"""
        data = await self._request(
            "/coins/markets",
            {
                "vs_currency": "usd",
                "order": "price_change_percentage_24h_desc",
                "per_page": limit * 2,
                "page": 1,
                "sparkline": "false"
            }
        )
        
        if not data:
            return {"gainers": [], "losers": []}
        
        # Сортируем
        sorted_data = sorted(data, key=lambda x: x.get("price_change_percentage_24h", 0), reverse=True)
        
        return {
            "gainers": sorted_data[:limit],
            "losers": sorted_data[-limit:][::-1]
        }
    
    async def get_coin_by_contract(self, platform: str, contract: str) -> Optional[dict]:
        """Получить монету по адресу контракта"""
        return await self._request(f"/coins/{platform}/contract/{contract}")
    
    async def get_categories(self) -> list:
        """Список категорий"""
        data = await self._request("/coins/categories/list")
        return data or []
    
    async def get_coins_by_category(self, category_id: str) -> list:
        """Монеты в категории"""
        data = await self._request(
            "/coins/markets",
            {
                "vs_currency": "usd",
                "category": category_id,
                "order": "market_cap_desc",
                "per_page": 50,
                "page": 1
            }
        )
        return data or []