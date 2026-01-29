"""
Репозиторий пользователей
"""
from datetime import datetime, timedelta
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, UserAchievement
from config import ACHIEVEMENTS, is_admin


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create(self, telegram_id: int, **kwargs) -> User:
        """Получить или создать пользователя"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(telegram_id=telegram_id, **kwargs)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        
        return user
    
    async def set_daily_limit(self, user: User, limit: int | None):
        """
        limit:
        None  -> дефолтный лимит
        -1    -> безлимит
        >=0   -> лимит в день
        """
        user.daily_analysis_limit = limit
        await self.session.commit()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Получить пользователя по Telegram ID"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def update_activity(self, user: User):
        """Обновить активность и streak"""
        now = datetime.utcnow()
        today = now.date()
        
        if user.last_streak_date:
            last_date = user.last_streak_date.date()
            if last_date == today - timedelta(days=1):
                user.streak_days += 1
            elif last_date != today:
                user.streak_days = 1
        else:
            user.streak_days = 1
        
        user.last_active = now
        user.last_streak_date = now
        
        await self.session.commit()
        await self._check_streak_achievements(user)
    
    async def increment_analyses(self, user: User):
        """Увеличить счётчик анализов"""
        user.analyses_count += 1
        await self.session.commit()
        await self._check_analysis_achievements(user)
    
    async def add_points(self, user: User, points: int):
        """Добавить очки"""
        user.points += points
        new_level = self._calculate_level(user.points)
        if new_level > user.level:
            user.level = new_level
        await self.session.commit()
    
    async def unlock_achievement(self, user: User, achievement_id: str) -> bool:
        """Разблокировать достижение"""
        result = await self.session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user.id,
                UserAchievement.achievement_id == achievement_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return False
        
        achievement = UserAchievement(
            user_id=user.id,
            achievement_id=achievement_id
        )
        self.session.add(achievement)
        
        if achievement_id in ACHIEVEMENTS:
            user.points += ACHIEVEMENTS[achievement_id]["points"]
        
        await self.session.commit()
        return True
    
    async def get_achievements(self, user: User) -> list[str]:
        """Получить список достижений"""
        result = await self.session.execute(
            select(UserAchievement.achievement_id).where(
                UserAchievement.user_id == user.id
            )
        )
        return [row[0] for row in result.fetchall()]
    
    async def get_leaderboard(self, limit: int = 10) -> list[User]:
        """Топ пользователей по очкам"""
        result = await self.session.execute(
            select(User).order_by(User.points.desc()).limit(limit)
        )
        return result.scalars().all()
    
    async def grant_premium(
        self,
        user: User,
        days: int = None,
        granted_by: int = None
    ) -> bool:
        """Выдать премиум пользователю"""
        user.is_premium = True
        user.granted_by = granted_by
        
        if days:
            user.premium_until = datetime.utcnow() + timedelta(days=days)
        else:
            user.premium_until = None  # Бессрочно
        
        await self.session.commit()
        return True
    
    async def revoke_premium(self, user: User) -> bool:
        """Забрать премиум"""
        user.is_premium = False
        user.premium_until = None
        user.granted_by = None
        await self.session.commit()
        return True
    
    async def get_all_premium_users(self) -> list[User]:
        """Получить всех премиум пользователей"""
        result = await self.session.execute(
            select(User).where(User.is_premium == True)
        )
        return result.scalars().all()
    
    async def _check_analysis_achievements(self, user: User):
        """Проверка ачивок за анализы"""
        if user.analyses_count == 1:
            await self.unlock_achievement(user, "first_analysis")
        elif user.analyses_count == 10:
            await self.unlock_achievement(user, "analyzer_10")
        elif user.analyses_count == 100:
            await self.unlock_achievement(user, "analyzer_100")
    
    async def _check_streak_achievements(self, user: User):
        """Проверка ачивок за streak"""
        if user.streak_days == 7:
            await self.unlock_achievement(user, "streak_7")
        elif user.streak_days == 30:
            await self.unlock_achievement(user, "streak_30")
    
    def _calculate_level(self, points: int) -> int:
        """Расчёт уровня по очкам"""
        thresholds = [0, 100, 300, 600, 1000, 1500, 2500, 4000, 6000, 10000]
        for i, threshold in enumerate(thresholds):
            if points < threshold:
                return i
        return len(thresholds)