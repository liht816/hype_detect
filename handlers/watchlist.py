"""
Обработчики watchlist
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from services import CoinGeckoService
from utils.keyboards import watchlist_keyboard, watchlist_empty_keyboard, back_to_menu_keyboard, analyze_result_keyboard
from utils.formatters import format_price
from database.connection import async_session
from database.repositories import UserRepository, WatchlistRepository

coingecko = CoinGeckoService()


async def watchlist_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ watchlist"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    async with async_session() as session:
        user_repo = UserRepository(session)
        watchlist_repo = WatchlistRepository(session)
        
        db_user = await user_repo.get_by_telegram_id(user.id)
        if not db_user:
            db_user = await user_repo.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
        
        items = await watchlist_repo.get_all(db_user)
    
    if not items:
        await query.edit_message_text(
            "📋 *Твой Watchlist пуст*\n\n"
            "Добавляй монеты, чтобы отслеживать их!\n\n"
            "*Как добавить:*\n"
            "1. Проанализируй монету (напиши название)\n"
            "2. Нажми кнопку «➕ В Watchlist»\n\n"
            "💡 Или напиши название монеты прямо сейчас!",
            parse_mode="Markdown",
            reply_markup=watchlist_empty_keyboard()
        )
        return
    
    # Получаем текущие цены
    coin_ids = [item.coin_id for item in items]
    prices = await coingecko.get_prices_batch(coin_ids)
    
    text = "📋 *Твой Watchlist*\n\n"
    
    for item in items:
        price_data = prices.get(item.coin_id, {})
        current_price = price_data.get("usd", 0)
        change_24h = price_data.get("usd_24h_change", 0)
        
        # Эмодзи изменения
        change_emoji = "🟢" if change_24h >= 0 else "🔴"
        
        text += f"*{item.coin_symbol.upper()}* — {item.coin_name}\n"
        text += f"💰 ${current_price:,.4f} {change_emoji} {change_24h:+.1f}%\n\n"
    
    text += f"_Всего монет: {len(items)}_"
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=watchlist_keyboard(items)
    )


async def watchlist_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия с watchlist"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    action = parts[1]
    coin_id = parts[2] if len(parts) > 2 else None
    
    user = query.from_user
    
    async with async_session() as session:
        user_repo = UserRepository(session)
        watchlist_repo = WatchlistRepository(session)
        
        db_user = await user_repo.get_by_telegram_id(user.id)
        if not db_user:
            db_user = await user_repo.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
        
        if action == "add" and coin_id:
            last_analysis = context.user_data.get("last_analysis", {})
            
            # Проверяем, есть ли уже
            exists = await watchlist_repo.exists(db_user, coin_id)
            if exists:
                await query.answer("✅ Уже в Watchlist!", show_alert=True)
                return
            
            await watchlist_repo.add(
                user=db_user,
                coin_id=coin_id,
                coin_symbol=last_analysis.get("coin_symbol", coin_id),
                coin_name=last_analysis.get("coin_name", coin_id),
                price=last_analysis.get("price"),
                hype_score=last_analysis.get("hype_score")
            )
            
            await query.answer("✅ Добавлено в Watchlist!", show_alert=True)
            
            # Обновляем кнопки
            try:
                await query.edit_message_reply_markup(
                    reply_markup=analyze_result_keyboard(coin_id, in_watchlist=True)
                )
            except:
                pass
        
        elif action == "remove" and coin_id:
            await watchlist_repo.remove(db_user, coin_id)
            await query.answer("🗑️ Удалено!", show_alert=True)
            
            # Обновляем список
            await watchlist_menu_callback(update, context)
        
        elif action == "add_new":
            await query.edit_message_text(
                "➕ *Добавить монету*\n\n"
                "Напиши название или тикер монеты:",
                parse_mode="Markdown",
                reply_markup=back_to_menu_keyboard()
            )
        
        elif action == "refresh_all":
            await query.answer("🔄 Обновляю...")
            await watchlist_menu_callback(update, context)
        
        elif action == "page":
            page = int(coin_id) if coin_id else 0
            items = await watchlist_repo.get_all(db_user)
            await query.edit_message_reply_markup(
                reply_markup=watchlist_keyboard(items, page=page)
            )


def register_watchlist_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CallbackQueryHandler(
        watchlist_menu_callback,
        pattern=r"^menu:watchlist$"
    ))
    app.add_handler(CallbackQueryHandler(
        watchlist_action_callback,
        pattern=r"^watchlist:"
    ))