"""
Google Trends сервис
"""
from pytrends.request import TrendReq
import asyncio
from datetime import datetime, timedelta
from typing import Optional


class GoogleTrendsService:
    """Анализ Google Trends"""
    
    def __init__(self):
        self.pytrends = TrendReq(hl='en-US', tz=360)
    
    async def get_interest_over_time(
        self,
        keyword: str,
        days: int = 7
    ) -> dict:
        """
        Получить интерес к запросу за период
        
        Returns:
            {
                "current": int (0-100),
                "average": float,
                "peak": int,
                "trend": "rising" | "falling" | "stable",
                "data": [{"date": "2024-01-15", "value": 50}, ...]
            }
        """
        try:
            # Выполняем в executor (pytrends синхронный)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._fetch_trends(keyword, days)
            )
            return result
        except Exception as e:
            print(f"Google Trends error: {e}")
            return self._empty_result()
    
    def _fetch_trends(self, keyword: str, days: int) -> dict:
        """Синхронный запрос к Google Trends"""
        timeframe = f"now {days}-d" if days <= 7 else f"today {days}-d"
        
        self.pytrends.build_payload(
            [keyword],
            cat=0,
            timeframe=timeframe,
            geo='',
            gprop=''
        )
        
        df = self.pytrends.interest_over_time()
        
        if df.empty:
            return self._empty_result()
        
        values = df[keyword].tolist()
        dates = df.index.tolist()
        
        current = values[-1] if values else 0
        average = sum(values) / len(values) if values else 0
        peak = max(values) if values else 0
        
        # Определяем тренд
        if len(values) >= 3:
            recent_avg = sum(values[-3:]) / 3
            older_avg = sum(values[:3]) / 3
            
            if recent_avg > older_avg * 1.2:
                trend = "rising"
            elif recent_avg < older_avg * 0.8:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "current": current,
            "average": round(average, 2),
            "peak": peak,
            "trend": trend,
            "change_percent": round((current - average) / average * 100, 2) if average > 0 else 0,
            "data": [
                {"date": d.strftime("%Y-%m-%d"), "value": v}
                for d, v in zip(dates, values)
            ]
        }
    
    async def compare_coins(self, coins: list[str]) -> dict:
        """
        Сравнить интерес к нескольким монетам
        
        Args:
            coins: ["bitcoin", "ethereum", "solana"]
        
        Returns:
            {"bitcoin": 80, "ethereum": 60, "solana": 30}
        """
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._compare_trends(coins)
            )
            return result
        except Exception as e:
            print(f"Google Trends compare error: {e}")
            return {}
    
    def _compare_trends(self, coins: list[str]) -> dict:
        """Синхронное сравнение"""
        self.pytrends.build_payload(
            coins[:5],  # Максимум 5
            cat=0,
            timeframe='now 7-d',
            geo='',
            gprop=''
        )
        
        df = self.pytrends.interest_over_time()
        
        if df.empty:
            return {}
        
        # Средние значения
        return {
            coin: round(df[coin].mean(), 2)
            for coin in coins if coin in df.columns
        }
    
    async def get_related_queries(self, keyword: str) -> dict:
        """
        Связанные запросы
        
        Returns:
            {"top": [...], "rising": [...]}
        """
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._fetch_related(keyword)
            )
            return result
        except Exception as e:
            print(f"Google Trends related error: {e}")
            return {"top": [], "rising": []}
    
    def _fetch_related(self, keyword: str) -> dict:
        """Синхронный запрос связанных"""
        self.pytrends.build_payload(
            [keyword],
            cat=0,
            timeframe='now 7-d',
            geo='',
            gprop=''
        )
        
        related = self.pytrends.related_queries()
        
        result = {"top": [], "rising": []}
        
        if keyword in related:
            top_df = related[keyword].get("top")
            rising_df = related[keyword].get("rising")
            
            if top_df is not None and not top_df.empty:
                result["top"] = top_df.head(10).to_dict("records")
            
            if rising_df is not None and not rising_df.empty:
                result["rising"] = rising_df.head(10).to_dict("records")
        
        return result
    
    async def get_regional_interest(self, keyword: str) -> list[dict]:
        """
        Интерес по регионам
        """
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._fetch_regional(keyword)
            )
            return result
        except Exception as e:
            print(f"Google Trends regional error: {e}")
            return []
    
    def _fetch_regional(self, keyword: str) -> list[dict]:
        """Синхронный запрос по регионам"""
        self.pytrends.build_payload(
            [keyword],
            cat=0,
            timeframe='now 7-d',
            geo='',
            gprop=''
        )
        
        df = self.pytrends.interest_by_region(resolution='COUNTRY')
        
        if df.empty:
            return []
        
        df = df.sort_values(by=keyword, ascending=False)
        
        return [
            {"country": idx, "value": row[keyword]}
            for idx, row in df.head(10).iterrows()
        ]
    
    def _empty_result(self) -> dict:
        return {
            "current": 0,
            "average": 0,
            "peak": 0,
            "trend": "unknown",
            "change_percent": 0,
            "data": []
        }