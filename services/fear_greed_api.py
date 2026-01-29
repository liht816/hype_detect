"""
Fear & Greed Index API
"""
import aiohttp
from datetime import datetime
from typing import Optional
from config import FEAR_GREED_API_URL


class FearGreedService:
    """Сервис Fear & Greed Index"""
    
    def __init__(self):
        self.base_url = FEAR_GREED_API_URL
    
    async def get_current(self) -> Optional[dict]:
        """
        Текущее значение индекса
        
        Returns:
            {
                "value": 45,
                "classification": "Fear",
                "timestamp": "2024-01-15",
                "time_until_update": "4 hours"
            }
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params={"limit": 1}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        if data.get("data"):
                            item = data["data"][0]
                            return {
                                "value": int(item.get("value", 0)),
                                "classification": item.get("value_classification", "Unknown"),
                                "timestamp": datetime.fromtimestamp(
                                    int(item.get("timestamp", 0))
                                ).strftime("%Y-%m-%d"),
                                "time_until_update": item.get("time_until_update", "Unknown")
                            }
        except Exception as e:
            print(f"Fear & Greed API error: {e}")
        
        return None
    
    async def get_history(self, days: int = 30) -> list[dict]:
        """
        История индекса
        
        Returns:
            [{"value": 45, "classification": "Fear", "date": "2024-01-15"}, ...]
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params={"limit": days}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        result = []
                        for item in data.get("data", []):
                            result.append({
                                "value": int(item.get("value", 0)),
                                "classification": item.get("value_classification", "Unknown"),
                                "date": datetime.fromtimestamp(
                                    int(item.get("timestamp", 0))
                                ).strftime("%Y-%m-%d")
                            })
                        
                        return result
        except Exception as e:
            print(f"Fear & Greed history error: {e}")
        
        return []
    
    async def get_analysis(self) -> dict:
        """
        Полный анализ с рекомендациями
        
        Returns:
            {
                "current": {...},
                "trend": "improving" | "worsening" | "stable",
                "avg_7d": float,
                "avg_30d": float,
                "recommendation": str
            }
        """
        current = await self.get_current()
        history = await self.get_history(30)
        
        if not current or not history:
            return {
                "current": None,
                "trend": "unknown",
                "avg_7d": 0,
                "avg_30d": 0,
                "recommendation": "Нет данных"
            }
        
        # Средние значения
        values = [h["value"] for h in history]
        avg_7d = sum(values[:7]) / min(7, len(values)) if values else 0
        avg_30d = sum(values) / len(values) if values else 0
        
        # Определяем тренд
        if len(values) >= 7:
            recent = sum(values[:3]) / 3
            older = sum(values[4:7]) / 3
            
            if recent > older + 5:
                trend = "improving"
            elif recent < older - 5:
                trend = "worsening"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Рекомендация
        value = current["value"]
        if value <= 20:
            recommendation = "🔥 Экстремальный страх — исторически хорошее время для покупки"
        elif value <= 40:
            recommendation = "😰 Страх на рынке — рассмотри накопление позиций"
        elif value <= 60:
            recommendation = "😐 Нейтральные настроения — рынок в раздумьях"
        elif value <= 80:
            recommendation = "🤑 Жадность — будь осторожен с новыми покупками"
        else:
            recommendation = "🤯 Экстремальная жадность — рассмотри фиксацию прибыли"
        
        return {
            "current": current,
            "trend": trend,
            "avg_7d": round(avg_7d, 1),
            "avg_30d": round(avg_30d, 1),
            "recommendation": recommendation
        }
    
    def get_emoji_for_value(self, value: int) -> str:
        """Эмодзи для значения"""
        if value <= 20:
            return "😱"
        elif value <= 40:
            return "😰"
        elif value <= 60:
            return "😐"
        elif value <= 80:
            return "🤑"
        else:
            return "🤯"
    
    def get_color_for_value(self, value: int) -> str:
        """Цвет для визуализации"""
        if value <= 20:
            return "#ff4444"
        elif value <= 40:
            return "#ff9944"
        elif value <= 60:
            return "#ffff44"
        elif value <= 80:
            return "#99ff44"
        else:
            return "#44ff44"