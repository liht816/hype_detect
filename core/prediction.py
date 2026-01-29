"""
Движок прогнозирования (ML-лайт)
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import random


@dataclass
class Prediction:
    """Прогноз"""
    coin_id: str
    coin_symbol: str
    
    # Прогноз
    direction: str  # "pump", "dump", "stable"
    confidence: float  # 0-1
    
    # Причины
    factors: list[str]
    
    # Временные рамки
    timeframe: str  # "24h", "7d"
    created_at: datetime = None
    
    # Для проверки
    price_at_prediction: float = 0.0
    target_price_low: float = 0.0
    target_price_high: float = 0.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class PredictionEngine:
    """
    Движок прогнозов
    
    Использует комбинацию:
    - Исторических паттернов хайпа
    - Активности китов
    - Sentiment анализа
    - Технических индикаторов (если есть)
    """
    
    # Исторические паттерны P&D
    PUMP_PATTERNS = {
        "rapid_hype_growth": {
            "weight": 0.3,
            "condition": lambda h: h.get("mention_velocity", 0) > 200
        },
        "whale_accumulation": {
            "weight": 0.25,
            "condition": lambda h: h.get("whale_buy_pressure", 0.5) > 0.7
        },
        "extreme_sentiment": {
            "weight": 0.2,
            "condition": lambda h: h.get("positive_ratio", 0.5) > 0.85
        },
        "low_cap_high_hype": {
            "weight": 0.25,
            "condition": lambda h: (
                h.get("market_cap_rank", 0) > 500 and
                h.get("hype_score", 0) > 60
            )
        }
    }
    
    DUMP_PATTERNS = {
        "whale_distribution": {
            "weight": 0.35,
            "condition": lambda h: h.get("whale_buy_pressure", 0.5) < 0.3
        },
        "hype_declining": {
            "weight": 0.3,
            "condition": lambda h: h.get("mention_velocity", 0) < -30
        },
        "price_overextended": {
            "weight": 0.35,
            "condition": lambda h: h.get("price_change_7d", 0) > 200
        }
    }
    
    def predict(
        self,
        coin_id: str,
        coin_symbol: str,
        current_price: float,
        
        # Хайп метрики
        hype_score: int = 0,
        mention_velocity: float = 0.0,
        
        # Рыночные метрики
        price_change_24h: float = 0.0,
        price_change_7d: float = 0.0,
        volume_change: float = 0.0,
        market_cap_rank: Optional[int] = None,
        
        # Whale метрики
        whale_buy_pressure: float = 0.5,
        
        # Sentiment
        positive_ratio: float = 0.5,
        
        # Timeframe
        timeframe: str = "24h"
    ) -> Prediction:
        """
        Сделать прогноз
        """
        context = {
            "hype_score": hype_score,
            "mention_velocity": mention_velocity,
            "price_change_24h": price_change_24h,
            "price_change_7d": price_change_7d,
            "volume_change": volume_change,
            "market_cap_rank": market_cap_rank or 9999,
            "whale_buy_pressure": whale_buy_pressure,
            "positive_ratio": positive_ratio,
        }
        
        # Проверяем паттерны
        pump_score = self._calculate_pattern_score(context, self.PUMP_PATTERNS)
        dump_score = self._calculate_pattern_score(context, self.DUMP_PATTERNS)
        
        factors = []
        
        # Определяем направление
        if pump_score > 0.6 and pump_score > dump_score:
            direction = "pump"
            confidence = min(pump_score, 0.85)
            factors = self._get_pump_factors(context)
            
            # Целевые цены
            if timeframe == "24h":
                target_low = current_price * 1.05
                target_high = current_price * 1.30
            else:
                target_low = current_price * 1.10
                target_high = current_price * 1.50
        
        elif dump_score > 0.5 and dump_score > pump_score:
            direction = "dump"
            confidence = min(dump_score, 0.80)
            factors = self._get_dump_factors(context)
            
            if timeframe == "24h":
                target_low = current_price * 0.70
                target_high = current_price * 0.95
            else:
                target_low = current_price * 0.50
                target_high = current_price * 0.85
        
        else:
            direction = "stable"
            confidence = 1 - max(pump_score, dump_score)
            factors = ["Нет явных сигналов в какую-либо сторону"]
            target_low = current_price * 0.95
            target_high = current_price * 1.05
        
        return Prediction(
            coin_id=coin_id,
            coin_symbol=coin_symbol,
            direction=direction,
            confidence=round(confidence, 2),
            factors=factors,
            timeframe=timeframe,
            price_at_prediction=current_price,
            target_price_low=round(target_low, 8),
            target_price_high=round(target_high, 8),
        )
    
    def _calculate_pattern_score(
        self,
        context: dict,
        patterns: dict
    ) -> float:
        """Расчёт скора по паттернам"""
        score = 0.0
        total_weight = 0.0
        
        for pattern_name, pattern in patterns.items():
            total_weight += pattern["weight"]
            if pattern["condition"](context):
                score += pattern["weight"]
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _get_pump_factors(self, context: dict) -> list[str]:
        """Факторы для прогноза пампа"""
        factors = []
        
        if context.get("mention_velocity", 0) > 200:
            factors.append(f"📈 Взрывной рост упоминаний (+{context['mention_velocity']:.0f}%)")
        
        if context.get("whale_buy_pressure", 0.5) > 0.7:
            factors.append("🐋 Киты активно скупают")
        
        if context.get("positive_ratio", 0.5) > 0.8:
            factors.append("😃 Очень позитивный sentiment")
        
        if context.get("hype_score", 0) > 60:
            factors.append(f"🔥 Высокий хайп-скор ({context['hype_score']})")
        
        if context.get("volume_change", 0) > 200:
            factors.append("📊 Аномально высокий объём")
        
        return factors or ["Комбинация факторов указывает на рост"]
    
    def _get_dump_factors(self, context: dict) -> list[str]:
        """Факторы для прогноза дампа"""
        factors = []
        
        if context.get("whale_buy_pressure", 0.5) < 0.3:
            factors.append("🐋 Киты распродаются")
        
        if context.get("mention_velocity", 0) < -30:
            factors.append(f"📉 Упоминания падают ({context['mention_velocity']:.0f}%)")
        
        if context.get("price_change_7d", 0) > 200:
            factors.append(f"⚠️ Цена перегрета (+{context['price_change_7d']:.0f}% за неделю)")
        
        if context.get("hype_score", 0) > 80:
            factors.append("💀 Экстремальный хайп — часто предшествует дампу")
        
        return factors or ["Комбинация факторов указывает на падение"]
    
    async def check_prediction(
        self,
        prediction: Prediction,
        current_price: float
    ) -> dict:
        """
        Проверка прогноза
        
        Returns:
            {
                "is_correct": bool,
                "actual_change": float,
                "predicted_direction": str,
                "actual_direction": str
            }
        """
        price_change = ((current_price - prediction.price_at_prediction) / 
                       prediction.price_at_prediction) * 100
        
        # Определяем фактическое направление
        if price_change > 5:
            actual_direction = "pump"
        elif price_change < -5:
            actual_direction = "dump"
        else:
            actual_direction = "stable"
        
        is_correct = prediction.direction == actual_direction
        
        # Частичная правота для "stable"
        if prediction.direction == "stable" and abs(price_change) < 10:
            is_correct = True
        
        return {
            "is_correct": is_correct,
            "actual_change": round(price_change, 2),
            "predicted_direction": prediction.direction,
            "actual_direction": actual_direction,
            "prediction_confidence": prediction.confidence
        }
    
    def format_prediction(self, pred: Prediction) -> str:
        """Форматирование прогноза"""
        direction_emoji = {
            "pump": "🚀",
            "dump": "📉",
            "stable": "➡️"
        }
        
        direction_text = {
            "pump": "РОСТ",
            "dump": "ПАДЕНИЕ",
            "stable": "БЕЗ ИЗМЕНЕНИЙ"
        }
        
        confidence_bar = "🟩" * int(pred.confidence * 5) + "⬜" * (5 - int(pred.confidence * 5))
        
        factors_text = "\n".join(f"• {f}" for f in pred.factors)
        
        return f"""
🔮 *Прогноз: ${pred.coin_symbol.upper()}*

{direction_emoji.get(pred.direction, '❓')} Направление: *{direction_text.get(pred.direction, '?')}*
📊 Уверенность: {confidence_bar} ({pred.confidence*100:.0f}%)
⏱️ Таймфрейм: {pred.timeframe}

💰 *Текущая цена:* ${pred.price_at_prediction:.6f}
🎯 *Целевой диапазон:*
   ${pred.target_price_low:.6f} — ${pred.target_price_high:.6f}

📋 *Факторы:*
{factors_text}

⚠️ _Это не финансовый совет. Прогноз основан на анализе паттернов._
"""