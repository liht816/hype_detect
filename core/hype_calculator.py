"""
Калькулятор рыночного перегрева (Market Heat Index)
Используем строки вместо Enum, чтобы избежать ошибок импорта
"""
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class HypeAnalysis:
    score: int
    level: str  # Строка уровня ("CRITICAL", "HIGH", "LOW")
    reasons: List[str]
    recommendation: str


class HypeCalculator:
    def __init__(self):
        self.current_price = None
        self.previous_price = None

    def calculate(
        self,
        price_change_24h: float = 0.0,
        price_change_7d: float = 0.0,
        market_cap: float = 0.0,
        volume_24h: float = 0.0,
        market_cap_rank: Optional[int] = None
    ) -> HypeAnalysis:
        """
        Расчёт индекса перегрева на основе рыночных метрик
        """
        score = 0
        reasons = []

        # 1. Волатильность
        abs_24h = abs(price_change_24h)
        if abs_24h > 30:
            score += 40
            reasons.append(f"🚀 Экстремальная волатильность: {price_change_24h:+.1f}%")
        elif abs_24h > 15:
            score += 25
            reasons.append(f"📈 Высокая волатильность: {price_change_24h:+.1f}%")
        elif abs_24h > 5:
            score += 10

        # 2. Объем vs Капитализация
        if market_cap > 0 and volume_24h > 0:
            vol_to_cap = volume_24h / market_cap
            if vol_to_cap > 0.5:
                score += 30
                reasons.append("📊 Оборот > 50% от капитализации (P&D риск)")
            elif vol_to_cap > 0.2:
                score += 15
                reasons.append("🔹 Повышенная торговая активность")

        # 3. Недельный тренд
        if abs(price_change_7d) > 100:
            score += 20
            reasons.append(f"⚠️ Резкий рост: {price_change_7d:+.0f}% за неделю")
        elif abs(price_change_7d) > 50:
            score += 10

        # 4. Низкий ранг (риск манипуляций)
        if market_cap_rank and market_cap_rank > 500:
            score += 10
            reasons.append("🎯 Микро-капитализация")

        score = min(score, 100)

        # Определяем уровень и рекомендацию
        if score >= 80:
            level = "💀 КРИТИЧЕСКИЙ (DANGER)"
            rec = "Рынок крайне нестабилен. Высокий риск дайпа. Не входить!"
        elif score >= 60:
            level = "🔴 ВЫСОКИЙ (HIGH)"
            rec = "Сильный импульс. Подтягивай стопы, будь осторожен."
        elif score >= 40:
            level = "🟠 ПОВЫШЕННЫЙ"
            rec = "Активное движение. Требуется осторожность."
        elif score >= 20:
            level = "🟡 УМЕРЕННЫЙ"
            rec = "Нормальная активность. Благоприятно для анализа."
        else:
            level = "🟢 СПОКОЙНО"
            rec = "Рынок стабилен или в накоплении."

        return HypeAnalysis(
            score=score,
            level=level,
            reasons=reasons,
            recommendation=rec
        )