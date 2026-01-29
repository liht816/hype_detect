"""
Детектор Red Flags (признаков скама)
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import re


class RedFlagSeverity(Enum):
    """Серьёзность red flag"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RedFlag:
    """Отдельный red flag"""
    id: str
    name: str
    description: str
    severity: RedFlagSeverity
    details: Optional[str] = None


@dataclass
class RedFlagResult:
    """Результат проверки на red flags"""
    coin_id: str
    coin_symbol: str
    coin_name: str
    
    red_flags: list[RedFlag] = field(default_factory=list)
    risk_score: int = 0  # 0-100
    risk_level: str = "low"  # low, medium, high, critical
    
    recommendation: str = ""
    is_safe: bool = True
    
    # Позитивные сигналы
    green_flags: list[str] = field(default_factory=list)


class RedFlagsDetector:
    """
    Детектор подозрительных признаков
    
    Проверяет:
    - Токеномику
    - Команду
    - Код/контракт
    - Социальные сигналы
    - Рыночные аномалии
    """
    
    # Паттерны подозрительных названий
    SCAM_NAME_PATTERNS = [
        r"elon",
        r"musk",
        r"shib.*inu",
        r"doge.*coin",
        r"safe.*moon",
        r"baby.*",
        r"mini.*",
        r"100x",
        r"1000x",
        r"inu$",
        r"moon$",
        r"rocket",
    ]
    
    def analyze(
        self,
        coin_id: str,
        coin_symbol: str,
        coin_name: str,
        
        # Рыночные данные
        market_cap: Optional[float] = None,
        market_cap_rank: Optional[int] = None,
        volume_24h: Optional[float] = None,
        price_change_24h: Optional[float] = None,
        price_change_7d: Optional[float] = None,
        
        # Данные о проекте
        website_url: Optional[str] = None,
        twitter_url: Optional[str] = None,
        github_url: Optional[str] = None,
        telegram_url: Optional[str] = None,
        
        # Социальные данные
        twitter_followers: int = 0,
        reddit_subscribers: int = 0,
        github_commits_30d: int = 0,
        github_stars: int = 0,
        
        # Токеномика
        total_supply: Optional[float] = None,
        circulating_supply: Optional[float] = None,
        max_supply: Optional[float] = None,
        
        # Дополнительно
        contract_address: Optional[str] = None,
        launch_date: Optional[str] = None,
        is_contract_verified: bool = True,
        has_audit: bool = False,
        
        # Хайп данные
        hype_score: int = 0,
        sentiment_positive_ratio: float = 0.5,
    ) -> RedFlagResult:
        """
        Главный метод анализа
        """
        red_flags = []
        green_flags = []
        
        # ===== 1. ПРОВЕРКА НАЗВАНИЯ =====
        self._check_name(coin_name, coin_symbol, red_flags)
        
        # ===== 2. РЫНОЧНЫЕ АНОМАЛИИ =====
        self._check_market_anomalies(
            market_cap=market_cap,
            market_cap_rank=market_cap_rank,
            volume_24h=volume_24h,
            price_change_24h=price_change_24h,
            price_change_7d=price_change_7d,
            red_flags=red_flags,
            green_flags=green_flags
        )
        
        # ===== 3. СОЦИАЛЬНЫЕ СИГНАЛЫ =====
        self._check_social_signals(
            twitter_followers=twitter_followers,
            reddit_subscribers=reddit_subscribers,
            market_cap=market_cap,
            sentiment_positive_ratio=sentiment_positive_ratio,
            red_flags=red_flags,
            green_flags=green_flags
        )
        
        # ===== 4. РАЗРАБОТКА =====
        self._check_development(
            github_url=github_url,
            github_commits_30d=github_commits_30d,
            github_stars=github_stars,
            red_flags=red_flags,
            green_flags=green_flags
        )
        
        # ===== 5. ПРОЗРАЧНОСТЬ =====
        self._check_transparency(
            website_url=website_url,
            contract_address=contract_address,
            is_contract_verified=is_contract_verified,
            has_audit=has_audit,
            red_flags=red_flags,
            green_flags=green_flags
        )
        
        # ===== 6. ТОКЕНОМИКА =====
        self._check_tokenomics(
            total_supply=total_supply,
            circulating_supply=circulating_supply,
            max_supply=max_supply,
            red_flags=red_flags
        )
        
        # ===== 7. ХАЙП =====
        self._check_hype_signals(
            hype_score=hype_score,
            market_cap_rank=market_cap_rank,
            red_flags=red_flags
        )
        
        # Расчёт risk score
        risk_score = self._calculate_risk_score(red_flags, green_flags)
        risk_level = self._get_risk_level(risk_score)
        
        # Рекомендация
        recommendation = self._get_recommendation(risk_score, red_flags, green_flags)
        
        return RedFlagResult(
            coin_id=coin_id,
            coin_symbol=coin_symbol,
            coin_name=coin_name,
            red_flags=red_flags,
            risk_score=risk_score,
            risk_level=risk_level,
            recommendation=recommendation,
            is_safe=risk_score < 40,
            green_flags=green_flags
        )
    
    def _check_name(self, name: str, symbol: str, red_flags: list):
        """Проверка названия на подозрительные паттерны"""
        name_lower = name.lower()
        symbol_lower = symbol.lower()
        
        for pattern in self.SCAM_NAME_PATTERNS:
            if re.search(pattern, name_lower) or re.search(pattern, symbol_lower):
                red_flags.append(RedFlag(
                    id="suspicious_name",
                    name="🎭 Подозрительное название",
                    description="Название похоже на типичные скам-токены",
                    severity=RedFlagSeverity.MEDIUM,
                    details=f"Паттерн: {pattern}"
                ))
                break
    
    def _check_market_anomalies(
        self,
        market_cap: Optional[float],
        market_cap_rank: Optional[int],
        volume_24h: Optional[float],
        price_change_24h: Optional[float],
        price_change_7d: Optional[float],
        red_flags: list,
        green_flags: list
    ):
        """Проверка рыночных аномалий"""
        
        # Аномально низкий объём
        if market_cap and volume_24h:
            volume_ratio = volume_24h / market_cap
            
            if volume_ratio < 0.001:
                red_flags.append(RedFlag(
                    id="low_volume",
                    name="📉 Очень низкий объём",
                    description="Объём торгов подозрительно низкий",
                    severity=RedFlagSeverity.MEDIUM,
                    details=f"Объём/капитализация: {volume_ratio:.4f}"
                ))
            elif volume_ratio > 5:
                red_flags.append(RedFlag(
                    id="high_volume",
                    name="📊 Аномальный объём",
                    description="Объём слишком высокий относительно капитализации",
                    severity=RedFlagSeverity.HIGH,
                    details=f"Объём/капитализация: {volume_ratio:.2f}"
                ))
        
        # Экстремальные изменения цены
        if price_change_24h and abs(price_change_24h) > 100:
            red_flags.append(RedFlag(
                id="extreme_price_change",
                name="🎢 Экстремальная волатильность",
                description="Цена изменилась более чем на 100% за 24ч",
                severity=RedFlagSeverity.HIGH,
                details=f"Изменение: {price_change_24h:+.1f}%"
            ))
        
        # Очень низкая капитализация
        if market_cap and market_cap < 100000:
            red_flags.append(RedFlag(
                id="micro_cap",
                name="💰 Микро-капитализация",
                description="Очень легко манипулировать ценой",
                severity=RedFlagSeverity.HIGH,
                details=f"Cap: ${market_cap:,.0f}"
            ))
        
        # Позитивные сигналы
        if market_cap_rank and market_cap_rank < 100:
            green_flags.append("🏆 Топ-100 по капитализации")
        
        if market_cap and market_cap > 1_000_000_000:
            green_flags.append("💎 Капитализация > $1B")
    
    def _check_social_signals(
        self,
        twitter_followers: int,
        reddit_subscribers: int,
        market_cap: Optional[float],
        sentiment_positive_ratio: float,
        red_flags: list,
        green_flags: list
    ):
        """Проверка социальных сигналов"""
        
        # Мало подписчиков для размера проекта
        if market_cap and market_cap > 10_000_000:
            if twitter_followers < 1000:
                red_flags.append(RedFlag(
                    id="low_social",
                    name="👥 Мало подписчиков",
                    description="Для такой капитализации подозрительно мало подписчиков",
                    severity=RedFlagSeverity.MEDIUM,
                    details=f"Twitter: {twitter_followers}"
                ))
        
        # Слишком много позитива (боты?)
        if sentiment_positive_ratio > 0.95:
            red_flags.append(RedFlag(
                id="fake_sentiment",
                name="🤖 Подозрительный sentiment",
                description="Почти 100% позитива — признак ботов",
                severity=RedFlagSeverity.MEDIUM,
                details=f"Позитив: {sentiment_positive_ratio*100:.0f}%"
            ))
        
        # Позитивные сигналы
        if twitter_followers > 100_000:
            green_flags.append(f"🐦 {twitter_followers:,} подписчиков в Twitter")
        
        if reddit_subscribers > 50_000:
            green_flags.append(f"💬 {reddit_subscribers:,} подписчиков на Reddit")
    
    def _check_development(
        self,
        github_url: Optional[str],
        github_commits_30d: int,
        github_stars: int,
        red_flags: list,
        green_flags: list
    ):
        """Проверка активности разработки"""
        
        if not github_url:
            red_flags.append(RedFlag(
                id="no_github",
                name="📂 Нет GitHub",
                description="Отсутствует публичный репозиторий",
                severity=RedFlagSeverity.MEDIUM
            ))
        else:
            if github_commits_30d == 0:
                red_flags.append(RedFlag(
                    id="inactive_dev",
                    name="💤 Нет активности",
                    description="0 коммитов за 30 дней",
                    severity=RedFlagSeverity.MEDIUM
                ))
            elif github_commits_30d > 50:
                green_flags.append(f"👨‍💻 Активная разработка ({github_commits_30d} коммитов/мес)")
            
            if github_stars > 1000:
                green_flags.append(f"⭐ {github_stars:,} звёзд на GitHub")
    
    def _check_transparency(
        self,
        website_url: Optional[str],
        contract_address: Optional[str],
        is_contract_verified: bool,
        has_audit: bool,
        red_flags: list,
        green_flags: list
    ):
        """Проверка прозрачности проекта"""
        
        if not website_url:
            red_flags.append(RedFlag(
                id="no_website",
                name="🌐 Нет сайта",
                description="Отсутствует официальный сайт",
                severity=RedFlagSeverity.HIGH
            ))
        
        if contract_address and not is_contract_verified:
            red_flags.append(RedFlag(
                id="unverified_contract",
                name="📜 Неверифицированный контракт",
                description="Код контракта не опубликован",
                severity=RedFlagSeverity.CRITICAL
            ))
        
        # Позитивные
        if has_audit:
            green_flags.append("✅ Прошёл аудит безопасности")
        
        if is_contract_verified:
            green_flags.append("📜 Контракт верифицирован")
    
    def _check_tokenomics(
        self,
        total_supply: Optional[float],
        circulating_supply: Optional[float],
        max_supply: Optional[float],
        red_flags: list
    ):
        """Проверка токеномики"""
        
        if total_supply and circulating_supply:
            ratio = circulating_supply / total_supply
            
            if ratio < 0.1:
                red_flags.append(RedFlag(
                    id="low_circulation",
                    name="🔒 Мало токенов в обращении",
                    description="Менее 10% токенов в обращении",
                    severity=RedFlagSeverity.HIGH,
                    details=f"В обращении: {ratio*100:.1f}%"
                ))
        
        # Огромный supply (часто у мем-токенов)
        if total_supply and total_supply > 1_000_000_000_000_000:
            red_flags.append(RedFlag(
                id="huge_supply",
                name="📊 Огромный supply",
                description="Квадриллионы токенов — типично для скамов",
                severity=RedFlagSeverity.MEDIUM
            ))
    
    def _check_hype_signals(
        self,
        hype_score: int,
        market_cap_rank: Optional[int],
        red_flags: list
    ):
        """Проверка хайп-сигналов"""
        
        # Высокий хайп + низкий ранг = подозрительно
        if hype_score >= 70 and market_cap_rank and market_cap_rank > 500:
            red_flags.append(RedFlag(
                id="hype_vs_rank",
                name="🔥 Хайп не соответствует рангу",
                description="Много хайпа для малоизвестной монеты",
                severity=RedFlagSeverity.HIGH,
                details=f"Хайп: {hype_score}, Ранг: #{market_cap_rank}"
            ))
    
    def _calculate_risk_score(
        self,
        red_flags: list[RedFlag],
        green_flags: list[str]
    ) -> int:
        """Расчёт итогового risk score"""
        
        # Базовый скор от red flags
        severity_weights = {
            RedFlagSeverity.LOW: 5,
            RedFlagSeverity.MEDIUM: 15,
            RedFlagSeverity.HIGH: 25,
            RedFlagSeverity.CRITICAL: 40,
        }
        
        risk_score = sum(
            severity_weights.get(rf.severity, 10)
            for rf in red_flags
        )
        
        # Снижаем за green flags
        risk_score -= len(green_flags) * 5
        
        return max(0, min(100, risk_score))
    
    def _get_risk_level(self, score: int) -> str:
        """Определение уровня риска"""
        if score >= 70:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 30:
            return "medium"
        else:
            return "low"
    
    def _get_recommendation(
        self,
        risk_score: int,
        red_flags: list[RedFlag],
        green_flags: list[str]
    ) -> str:
        """Генерация рекомендации"""
        
        critical_flags = [rf for rf in red_flags if rf.severity == RedFlagSeverity.CRITICAL]
        
        if critical_flags:
            return (
                "🚨 *КРИТИЧЕСКИЙ РИСК*\n\n"
                "Обнаружены критические признаки скама. "
                "Настоятельно рекомендуем избегать этот проект!"
            )
        
        if risk_score >= 70:
            return (
                "⛔ *ВЫСОКИЙ РИСК*\n\n"
                "Множество тревожных признаков. "
                "Вероятность скама очень высока. Не инвестируй!"
            )
        
        if risk_score >= 50:
            return (
                "⚠️ *ПОВЫШЕННЫЙ РИСК*\n\n"
                "Есть серьёзные red flags. "
                "Если решишь инвестировать — только те деньги, которые готов потерять полностью."
            )
        
        if risk_score >= 30:
            return (
                "👀 *УМЕРЕННЫЙ РИСК*\n\n"
                "Есть некоторые подозрительные моменты. "
                "Требуется дополнительное исследование перед инвестицией."
            )
        
        if green_flags:
            return (
                "✅ *НИЗКИЙ РИСК*\n\n"
                f"Обнаружено {len(green_flags)} позитивных сигналов. "
                "Проект выглядит легитимным, но всегда делай собственный ресёрч."
            )
        
        return (
            "📊 *НЕОПРЕДЕЛЁННО*\n\n"
            "Недостаточно данных для полноценной оценки. "
            "Рекомендуем дождаться больше информации о проекте."
        )
    
    def format_result(self, result: RedFlagResult) -> str:
        """Форматирование результата для сообщения"""
        
        risk_emoji = {
            "critical": "🚨",
            "high": "⛔",
            "medium": "⚠️",
            "low": "✅"
        }
        
        text = f"""
*Red Flag анализ: {result.coin_name}* ({result.coin_symbol.upper()})

{risk_emoji.get(result.risk_level, '❓')} *Risk Score: {result.risk_score}/100*
Уровень риска: *{result.risk_level.upper()}*

"""
        
        if result.red_flags:
            text += "🚩 *Red Flags:*\n"
            for rf in result.red_flags[:7]:  # Максимум 7
                severity_icon = {
                    RedFlagSeverity.LOW: "🟡",
                    RedFlagSeverity.MEDIUM: "🟠",
                    RedFlagSeverity.HIGH: "🔴",
                    RedFlagSeverity.CRITICAL: "💀"
                }
                text += f"{severity_icon.get(rf.severity, '⚪')} {rf.name}\n"
                text += f"   _{rf.description}_\n"
            text += "\n"
        
        if result.green_flags:
            text += "✅ *Green Flags:*\n"
            for gf in result.green_flags[:5]:
                text += f"• {gf}\n"
            text += "\n"
        
        text += f"💡 *Вердикт:*\n{result.recommendation}"
        
        return text