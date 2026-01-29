"""
Менеджер алертов
"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
import asyncio


class AlertType(Enum):
    """Типы алертов"""
    HYPE_SPIKE = "hype_spike"           # Резкий рост хайпа
    HYPE_DROP = "hype_drop"             # Падение хайпа (после пампа)
    PRICE_CHANGE = "price_change"       # Изменение цены
    WHALE_MOVE = "whale_move"           # Движение китов
    TRENDING = "trending"               # Вход в тренды
    NEW_LISTING = "new_listing"         # Новый листинг
    INFLUENCER = "influencer"           # Упоминание инфлюенсером
    RED_FLAG = "red_flag"               # Обнаружен red flag


@dataclass
class AlertCondition:
    """Условие срабатывания алерта"""
    alert_type: AlertType
    coin_id: Optional[str] = None       # None = все монеты
    threshold: float = 0.0              # Порог
    comparison: str = ">"               # >, <, >=, <=, ==
    
    def check(self, value: float) -> bool:
        """Проверка условия"""
        ops = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "==": lambda a, b: a == b,
        }
        return ops.get(self.comparison, lambda a, b: False)(value, self.threshold)


@dataclass
class AlertEvent:
    """Событие алерта"""
    alert_type: AlertType
    coin_id: str
    coin_symbol: str
    coin_name: str
    
    # Данные события
    current_value: float
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None
    
    # Контекст
    details: dict = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}


class AlertManager:
    """
    Менеджер алертов
    
    Отвечает за:
    - Проверку условий алертов
    - Генерацию уведомлений
    - Дедупликацию (не спамить одинаковыми алертами)
    - Учёт тихих часов
    """
    
    def __init__(self):
        self._last_alerts: dict[str, datetime] = {}  # Для дедупликации
        self._cooldown = timedelta(hours=1)  # Минимум час между одинаковыми алертами
    
    def check_hype_spike(
        self,
        coin_id: str,
        coin_symbol: str,
        coin_name: str,
        current_hype: int,
        previous_hype: int,
        threshold: int = 20  # Минимальное изменение
    ) -> Optional[AlertEvent]:
        """
        Проверка на резкий рост хайпа
        """
        change = current_hype - previous_hype
        
        if change >= threshold:
            if self._is_on_cooldown(f"hype_spike:{coin_id}"):
                return None
            
            self._mark_sent(f"hype_spike:{coin_id}")
            
            return AlertEvent(
                alert_type=AlertType.HYPE_SPIKE,
                coin_id=coin_id,
                coin_symbol=coin_symbol,
                coin_name=coin_name,
                current_value=current_hype,
                previous_value=previous_hype,
                change_percent=change,
                details={
                    "message": f"Хайп вырос на {change} пунктов!",
                    "severity": "high" if change >= 30 else "medium"
                }
            )
        
        return None
    
    def check_price_change(
        self,
        coin_id: str,
        coin_symbol: str,
        coin_name: str,
        current_price: float,
        previous_price: float,
        threshold_percent: float = 10.0
    ) -> Optional[AlertEvent]:
        """
        Проверка на изменение цены
        """
        if previous_price == 0:
            return None
        
        change_percent = ((current_price - previous_price) / previous_price) * 100
        
        if abs(change_percent) >= threshold_percent:
            direction = "up" if change_percent > 0 else "down"
            key = f"price_{direction}:{coin_id}"
            
            if self._is_on_cooldown(key):
                return None
            
            self._mark_sent(key)
            
            return AlertEvent(
                alert_type=AlertType.PRICE_CHANGE,
                coin_id=coin_id,
                coin_symbol=coin_symbol,
                coin_name=coin_name,
                current_value=current_price,
                previous_value=previous_price,
                change_percent=change_percent,
                details={
                    "direction": direction,
                    "severity": "high" if abs(change_percent) >= 20 else "medium"
                }
            )
        
        return None
    
    def check_whale_activity(
        self,
        coin_id: str,
        coin_symbol: str,
        coin_name: str,
        transaction_type: str,  # "buy" or "sell"
        amount_usd: float,
        threshold_usd: float = 1000000
    ) -> Optional[AlertEvent]:
        """
        Проверка на крупную транзакцию кита
        """
        if amount_usd >= threshold_usd:
            key = f"whale_{transaction_type}:{coin_id}"
            
            if self._is_on_cooldown(key):
                return None
            
            self._mark_sent(key)
            
            return AlertEvent(
                alert_type=AlertType.WHALE_MOVE,
                coin_id=coin_id,
                coin_symbol=coin_symbol,
                coin_name=coin_name,
                current_value=amount_usd,
                details={
                    "transaction_type": transaction_type,
                    "severity": "high" if amount_usd >= 5000000 else "medium"
                }
            )
        
        return None
    
    def check_trending(
        self,
        coin_id: str,
        coin_symbol: str,
        coin_name: str,
        is_trending: bool,
        was_trending: bool = False
    ) -> Optional[AlertEvent]:
        """
        Проверка на вход в тренды
        """
        if is_trending and not was_trending:
            key = f"trending:{coin_id}"
            
            if self._is_on_cooldown(key):
                return None
            
            self._mark_sent(key)
            
            return AlertEvent(
                alert_type=AlertType.TRENDING,
                coin_id=coin_id,
                coin_symbol=coin_symbol,
                coin_name=coin_name,
                current_value=1,
                details={
                    "message": "Монета вошла в тренды!",
                    "severity": "medium"
                }
            )
        
        return None
    
    def check_red_flag(
        self,
        coin_id: str,
        coin_symbol: str,
        coin_name: str,
        red_flags: list[str]
    ) -> Optional[AlertEvent]:
        """
        Проверка на обнаружение red flags
        """
        if red_flags:
            key = f"redflag:{coin_id}"
            
            # Для red flags более длинный cooldown
            if self._is_on_cooldown(key, cooldown=timedelta(hours=24)):
                return None
            
            self._mark_sent(key)
            
            return AlertEvent(
                alert_type=AlertType.RED_FLAG,
                coin_id=coin_id,
                coin_symbol=coin_symbol,
                coin_name=coin_name,
                current_value=len(red_flags),
                details={
                    "red_flags": red_flags,
                    "severity": "critical" if len(red_flags) >= 3 else "high"
                }
            )
        
        return None
    
    def format_alert_message(self, event: AlertEvent) -> str:
        """
        Форматирование сообщения алерта
        """
        severity_emoji = {
            "critical": "🚨🚨🚨",
            "high": "🚨",
            "medium": "⚠️",
            "low": "📢"
        }
        
        emoji = severity_emoji.get(event.details.get("severity", "medium"), "📢")
        
        if event.alert_type == AlertType.HYPE_SPIKE:
            return (
                f"{emoji} *HYPE ALERT: ${event.coin_symbol.upper()}*\n\n"
                f"Хайп-скор: {int(event.previous_value)} → {int(event.current_value)}\n"
                f"Изменение: *+{int(event.change_percent)} пунктов*\n\n"
                f"⚡ {event.details.get('message', '')}\n\n"
                f"Рекомендация: Проверь монету на признаки P&D"
            )
        
        elif event.alert_type == AlertType.PRICE_CHANGE:
            direction_emoji = "📈" if event.details.get("direction") == "up" else "📉"
            return (
                f"{emoji} *PRICE ALERT: ${event.coin_symbol.upper()}*\n\n"
                f"{direction_emoji} Цена: ${event.previous_value:.4f} → ${event.current_value:.4f}\n"
                f"Изменение: *{event.change_percent:+.2f}%*\n\n"
                f"Рекомендация: Проверь новости и хайп-скор"
            )
        
        elif event.alert_type == AlertType.WHALE_MOVE:
            tx_type = event.details.get("transaction_type", "move")
            tx_emoji = "🐋📥" if tx_type == "buy" else "🐋📤"
            action = "купил" if tx_type == "buy" else "продал"
            
            return (
                f"{emoji} *WHALE ALERT: ${event.coin_symbol.upper()}*\n\n"
                f"{tx_emoji} Кит {action} на ${event.current_value:,.0f}\n\n"
                f"Это может повлиять на цену!"
            )
        
        elif event.alert_type == AlertType.TRENDING:
            return (
                f"{emoji} *TRENDING: ${event.coin_symbol.upper()}*\n\n"
                f"🔥 *{event.coin_name}* вошла в тренды!\n\n"
                f"Рекомендация: Проверь, органический ли это рост"
            )
        
        elif event.alert_type == AlertType.RED_FLAG:
            flags = event.details.get("red_flags", [])
            flags_text = "\n".join(f"• {flag}" for flag in flags[:5])
            
            return (
                f"{emoji} *RED FLAG ALERT: ${event.coin_symbol.upper()}*\n\n"
                f"Обнаружены тревожные признаки:\n{flags_text}\n\n"
                f"⚠️ *Будь очень осторожен с этой монетой!*"
            )
        
        else:
            return (
                f"{emoji} *ALERT: ${event.coin_symbol.upper()}*\n\n"
                f"{event.coin_name}\n"
                f"Тип: {event.alert_type.value}"
            )
    
    def is_quiet_hours(
        self,
        quiet_start: Optional[int],
        quiet_end: Optional[int],
        current_hour: Optional[int] = None
    ) -> bool:
        """
        Проверка тихих часов
        """
        if quiet_start is None or quiet_end is None:
            return False
        
        if current_hour is None:
            current_hour = datetime.now().hour
        
        if quiet_start <= quiet_end:
            return quiet_start <= current_hour < quiet_end
        else:  # Переход через полночь
            return current_hour >= quiet_start or current_hour < quiet_end
    
    def _is_on_cooldown(
        self,
        key: str,
        cooldown: Optional[timedelta] = None
    ) -> bool:
        """Проверка кулдауна"""
        if cooldown is None:
            cooldown = self._cooldown
        
        last_time = self._last_alerts.get(key)
        if last_time is None:
            return False
        
        return datetime.utcnow() - last_time < cooldown
    
    def _mark_sent(self, key: str):
        """Отметить отправку"""
        self._last_alerts[key] = datetime.utcnow()
    
    def clear_cooldowns(self):
        """Очистить все кулдауны (для тестирования)"""
        self._last_alerts.clear()