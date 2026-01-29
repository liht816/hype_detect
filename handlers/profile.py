"""
Обработчики профиля
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from utils.keyboards import profile_keyboard, back_to_menu_keyboard
from database.connection import async_session
from database.repositories import UserRepository, AnalysisRepository
from config import ACHIEVEMENTS


async def profile_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ профиля"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    async with async_session() as session:
        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(user.id)
        
        if not db_user:
            db_user = await user_repo.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
        
        achievements = await user_repo.get_achievements(db_user)
    
    level_names = {
        1: "🥉 Новичок",
        2: "🥈 Любитель",
        3: "🥇 Трейдер",
        4: "💎 Эксперт",
        5: "👑 Мастер",
    }
    
    level_name = level_names.get(db_user.level, f"Уровень {db_user.level}")
    
    text = f"""
👤 *Твой профиль*

{level_name}
⭐ Очки: {db_user.points}
📊 Анализов: {db_user.analyses_count}
🔥 Streak: {db_user.streak_days} дней

🏆 *Достижения:* {len(achievements)}/{len(ACHIEVEMENTS)}
"""
    
    if achievements:
        text += "\n"
        for ach_id in achievements[:5]:
            if ach_id in ACHIEVEMENTS:
                text += f"• {ACHIEVEMENTS[ach_id]['name']}\n"
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=profile_keyboard()
    )


async def profile_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия профиля"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split(":")[1]
    user = query.from_user
    
    async with async_session() as session:
        user_repo = UserRepository(session)
        analysis_repo = AnalysisRepository(session)
        db_user = await user_repo.get_by_telegram_id(user.id)
        
        if not db_user:
            db_user = await user_repo.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
        
        if action == "achievements":
            achievements = await user_repo.get_achievements(db_user)
            
            text = "🏆 *Все достижения*\n\n"
            
            for ach_id, ach_data in ACHIEVEMENTS.items():
                if ach_id in achievements:
                    status = "✅"
                else:
                    status = "🔒"
                
                text += f"{status} *{ach_data['name']}*\n"
                text += f"    +{ach_data['points']} очков\n\n"
            
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=profile_keyboard()
            )
        
        elif action == "stats":
            history = await analysis_repo.get_user_history(db_user, limit=50)
            
            text = f"""
📊 *Статистика*

🔍 Всего анализов: {db_user.analyses_count}
🎯 Верных прогнозов: {db_user.correct_predictions}
🔥 Текущий streak: {db_user.streak_days} дней
⭐ Всего очков: {db_user.points}
📈 Уровень: {db_user.level}
"""
            
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=profile_keyboard()
            )
        
        elif action == "history":
            history = await analysis_repo.get_user_history(db_user, limit=10)
            
            if not history:
                text = "📜 *История*\n\n_Пока пусто_"
            else:
                text = "📜 *Последние анализы*\n\n"
                
                for item in history:
                    date = item.created_at.strftime("%d.%m %H:%M")
                    hype_emoji = "🟢" if item.hype_score < 40 else "🟠" if item.hype_score < 70 else "🔴"
                    
                    text += f"{hype_emoji} *{item.coin_symbol.upper()}* — {item.hype_score}/100\n"
                    text += f"    {date}\n\n"
            
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=profile_keyboard()
            )
        
        elif action == "leaderboard":
            top_users = await user_repo.get_leaderboard(limit=10)
            
            text = "🏆 *Топ трейдеров*\n\n"
            
            medals = ["🥇", "🥈", "🥉"]
            
            for i, u in enumerate(top_users):
                medal = medals[i] if i < 3 else f"{i+1}."
                name = u.username or u.first_name or f"User{u.telegram_id}"
                text += f"{medal} *{name}* — {u.points} очков\n"
            
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=profile_keyboard()
            )


def register_profile_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CallbackQueryHandler(
        profile_menu_callback,
        pattern=r"^menu:profile$"
    ))
    app.add_handler(CallbackQueryHandler(
        profile_action_callback,
        pattern=r"^profile:"
    ))