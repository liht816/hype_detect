"""
Обработчики китов
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from utils.keyboards import whales_menu_keyboard, back_to_menu_keyboard
from utils.formatters import format_large_number


async def whales_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню китов"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🐋 *Отслеживание китов*\n\n"
        "Следи за крупными транзакциями!\n\n"
        "*Последние движения:*\n\n"
        "📥 *Покупка:* $2.5M ETH\n"
        "   Binance → Unknown Wallet\n"
        "   _5 минут назад_\n\n"
        "📤 *Продажа:* $1.8M BTC\n"
        "   Whale Wallet → Coinbase\n"
        "   _12 минут назад_\n\n"
        "📥 *Покупка:* $950K SOL\n"
        "   Unknown → Unknown\n"
        "   _23 минуты назад_\n\n"
        "💡 _Киты часто знают больше нас!_",
        parse_mode="Markdown",
        reply_markup=whales_menu_keyboard()
    )


async def whales_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия с китами"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    action = parts[1]
    
    if action == "recent":
        await query.edit_message_text(
            "🐋 *Последние транзакции китов*\n\n"
            "📥 $5.2M ETH — Покупка\n"
            "📤 $3.1M BTC — Продажа\n"
            "📥 $2.8M SOL — Покупка\n"
            "📥 $1.5M LINK — Покупка\n"
            "📤 $1.2M AVAX — Продажа\n\n"
            "📊 *Итого за 24ч:*\n"
            "Покупок: $45M\n"
            "Продаж: $32M\n"
            "Баланс: 🟢 +$13M",
            parse_mode="Markdown",
            reply_markup=whales_menu_keyboard()
        )
    
    elif action == "coin":
        coin = parts[2] if len(parts) > 2 else "bitcoin"
        coin_upper = coin.upper()[:3]
        
        await query.edit_message_text(
            f"🐋 *Киты {coin_upper}*\n\n"
            f"*Активность за 24 часа:*\n\n"
            f"📥 Покупки: $12.5M\n"
            f"📤 Продажи: $8.2M\n"
            f"📊 Чистый приток: 🟢 +$4.3M\n\n"
            f"*Крупнейшие транзакции:*\n\n"
            f"1. 📥 $3.2M — Binance → Wallet\n"
            f"2. 📤 $2.1M — Wallet → Kraken\n"
            f"3. 📥 $1.8M — Coinbase → Wallet\n\n"
            f"💡 _Киты покупают больше чем продают!_",
            parse_mode="Markdown",
            reply_markup=whales_menu_keyboard()
        )
    
    elif action == "search":
        await query.edit_message_text(
            "🔍 *Поиск китов*\n\n"
            "Напиши название монеты, чтобы увидеть активность китов:",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard()
        )


def register_whales_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CallbackQueryHandler(
        whales_menu_callback,
        pattern=r"^menu:whales$"
    ))
    app.add_handler(CallbackQueryHandler(
        whales_action_callback,
        pattern=r"^whales:"
    ))