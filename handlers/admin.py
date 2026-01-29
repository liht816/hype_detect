from __future__ import annotations

from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from config import is_admin, FREE_ANALYSES_PER_DAY
from database.connection import async_session
from database.models import User, AnalysisHistory
from sqlalchemy import select, func


# ---------- клавиатуры ----------

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Подписки / доступ", callback_data="admin:subs:0")],
        [InlineKeyboardButton("➕ Выдать/изменить лимит", callback_data="admin:mode:setlimit")],
        [InlineKeyboardButton("♾️ Сделать безлимит", callback_data="admin:mode:unlimited")],
        [InlineKeyboardButton("↩️ Сбросить на дефолт", callback_data="admin:mode:reset")],
        [InlineKeyboardButton("➖ Убрать доступ", callback_data="admin:mode:revoke")],
        [InlineKeyboardButton("🔎 Найти по ID", callback_data="admin:mode:lookup")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")],
    ])


def subs_kb(page: int, has_next: bool) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin:subs:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin:subs:{page+1}"))

    rows = []
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🔄 Обновить", callback_data=f"admin:subs:{page}")])
    rows.append([InlineKeyboardButton("◀️ Админ меню", callback_data="menu:admin")])
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


# ---------- утилиты ----------

async def _safe_edit_or_send(q, text: str, reply_markup=None):
    try:
        await q.edit_message_text(text=text, parse_mode="Markdown", reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return
        await q.message.reply_text(text=text, parse_mode="Markdown", reply_markup=reply_markup)


def _limit_to_text(limit: int | None) -> str:
    # None -> дефолт
    if limit is None:
        return f"{FREE_ANALYSES_PER_DAY}/день (по умолчанию)"
    if limit == -1:
        return "безлимит"
    return f"{limit}/день"


def _effective_limit(limit: int | None) -> int | None:
    # возвращает фактический лимит: None -> дефолт
    if limit is None:
        return FREE_ANALYSES_PER_DAY
    return limit


def _has_access(u: User) -> bool:
    """
    Считаем “подписка/доступ”:
    - безлимит (-1)
    - или лимит больше дефолта
    - или is_premium=True (если поле существует)
    """
    lim = getattr(u, "daily_analysis_limit", None)
    if lim == -1:
        return True
    if isinstance(lim, int) and lim > FREE_ANALYSES_PER_DAY:
        return True

    if hasattr(u, "is_premium") and getattr(u, "is_premium"):
        return True

    return False


async def _get_today_usage_map(session) -> dict[int, int]:
    """
    Возвращает {user_table_id: count_today}
    """
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    res = await session.execute(
        select(AnalysisHistory.user_id, func.count(AnalysisHistory.id))
        .where(AnalysisHistory.created_at >= today)
        .group_by(AnalysisHistory.user_id)
    )
    return {row[0]: row[1] for row in res.all()}


async def _find_user_by_tg_id(session, tg_id: int) -> User | None:
    res = await session.execute(select(User).where(User.telegram_id == tg_id))
    return res.scalar_one_or_none()


async def _set_limit(session, tg_id: int, new_limit: int | None) -> tuple[bool, str]:
    """
    new_limit:
      None -> дефолт
      -1   -> безлимит
      N    -> N в день
    """
    u = await _find_user_by_tg_id(session, tg_id)
    if not u:
        return False, "Пользователь не найден. Он должен сначала написать боту /start."

    # если в таблице нет колонки daily_analysis_limit — будет AttributeError
    if not hasattr(u, "daily_analysis_limit"):
        return False, "В модели нет поля daily_analysis_limit. Нужна миграция БД."

    u.daily_analysis_limit = new_limit
    await session.commit()

    return True, "OK"


# ---------- handlers ----------

async def admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        pass

    if not is_admin(q.from_user.id):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    context.user_data["admin_waiting"] = None

    await _safe_edit_or_send(
        q,
        "👑 *Админ панель*\n\n"
        "Тут ты можешь:\n"
        "• посмотреть у кого доступ/подписка\n"
        "• выдать/изменить лимит анализов\n"
        "• сделать безлимит\n"
        "• сбросить на дефолт\n"
        "• найти пользователя по ID\n",
        reply_markup=admin_menu_kb()
    )


async def admin_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        pass

    if not is_admin(q.from_user.id):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    mode = q.data.split(":")[2]
    context.user_data["admin_waiting"] = mode

    if mode == "setlimit":
        await q.message.reply_text(
            "➕ *Выдать/изменить лимит*\n\n"
            "Отправь сообщение в формате:\n"
            "`ID ЛИМИТ`\n\n"
            "Примеры:\n"
            "• `123456789 50`  (50 анализов в день)\n"
            "• `123456789 10`  (10 анализов в день)\n",
            parse_mode="Markdown"
        )
    elif mode == "unlimited":
        await q.message.reply_text(
            "♾️ *Безлимит*\n\n"
            "Отправь:\n"
            "`ID -1`\n\n"
            "Пример:\n"
            "• `123456789 -1`",
            parse_mode="Markdown"
        )
    elif mode == "reset":
        await q.message.reply_text(
            "↩️ *Сброс на дефолт*\n\n"
            "Отправь:\n"
            "`ID 0`\n\n"
            "Пример:\n"
            "• `123456789 0`",
            parse_mode="Markdown"
        )
    elif mode == "revoke":
        await q.message.reply_text(
            "➖ *Убрать доступ*\n\n"
            "Это вернёт лимит к дефолту (и снимет premium, если есть).\n\n"
            "Отправь:\n"
            "`ID 0`\n\n"
            "Пример:\n"
            "• `123456789 0`",
            parse_mode="Markdown"
        )
    elif mode == "lookup":
        await q.message.reply_text(
            "🔎 *Найти пользователя по ID*\n\n"
            "Отправь:\n"
            "`ID 1`\n\n"
            "Пример:\n"
            "• `123456789 1`",
            parse_mode="Markdown"
        )


async def admin_subscriptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer("Загружаю…")
    except BadRequest:
        pass

    if not is_admin(q.from_user.id):
        await q.answer("⛔ Нет доступа", show_alert=True)
        return

    parts = q.data.split(":")
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    per_page = 15
    offset = page * per_page

    async with async_session() as session:
        res = await session.execute(select(User).order_by(User.created_at.desc()))
        users = res.scalars().all()

        subs = [u for u in users if _has_access(u)]

        usage_map = await _get_today_usage_map(session)

        slice_ = subs[offset:offset + per_page]
        has_next = offset + per_page < len(subs)

        text = "💎 *Подписки / расширенный доступ*\n\n"
        if not subs:
            text += "_Пока никого нет._\n"
            await _safe_edit_or_send(q, text, reply_markup=subs_kb(page=0, has_next=False))
            return

        text += f"Всего: *{len(subs)}*\nСтраница: *{page+1}*\n\n"

        for u in slice_:
            tg_id = u.telegram_id
            uname = f"@{u.username}" if u.username else "(без username)"

            lim = getattr(u, "daily_analysis_limit", None)
            lim_text = _limit_to_text(lim)

            used_today = usage_map.get(u.id, 0)
            eff = _effective_limit(lim)
            usage_txt = f"{used_today}/∞" if eff == -1 else f"{used_today}/{eff}"

            text += (
                f"• *{uname}* `{tg_id}`\n"
                f"  лимит: *{lim_text}*\n"
                f"  использовано сегодня: *{usage_txt}*\n\n"
            )

    await _safe_edit_or_send(q, text, reply_markup=subs_kb(page=page, has_next=has_next))


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Ловим текст от админа, когда он выбрал режим (setlimit/unlimited/reset/revoke/lookup).
    Формат: ID VALUE
    """
    if not is_admin(update.effective_user.id):
        return False

    mode = context.user_data.get("admin_waiting")
    if not mode:
        return False

    raw = (update.message.text or "").strip().split()
    if len(raw) != 2:
        await update.message.reply_text("Формат: `ID значение`", parse_mode="Markdown")
        return True

    try:
        tg_id = int(raw[0])
        val = int(raw[1])
    except ValueError:
        await update.message.reply_text("ID и значение должны быть числами.")
        return True

    async with async_session() as session:
        # lookup
        if mode == "lookup":
            u = await _find_user_by_tg_id(session, tg_id)
            if not u:
                await update.message.reply_text("Пользователь не найден. Пусть сначала напишет /start.")
                return True

            usage_map = await _get_today_usage_map(session)
            used_today = usage_map.get(u.id, 0)

            lim = getattr(u, "daily_analysis_limit", None)
            lim_text = _limit_to_text(lim)
            eff = _effective_limit(lim)
            usage_txt = f"{used_today}/∞" if eff == -1 else f"{used_today}/{eff}"

            uname = f"@{u.username}" if u.username else "(без username)"
            await update.message.reply_text(
                "🔎 *Пользователь*\n\n"
                f"username: *{uname}*\n"
                f"id: `{u.telegram_id}`\n"
                f"лимит: *{lim_text}*\n"
                f"использовано сегодня: *{usage_txt}*",
                parse_mode="Markdown",
                reply_markup=admin_menu_kb()
            )
            return True

        # setlimit/unlimited/reset/revoke -> лимит
        if val == 0:
            new_limit = None  # дефолт
        else:
            new_limit = val   # -1 или N

        ok, msg = await _set_limit(session, tg_id, new_limit)
        if not ok:
            await update.message.reply_text(f"❌ {msg}", reply_markup=admin_menu_kb())
            return True

        # если revoke/reset: ещё и премиум снимем, если поле есть
        if mode in ("revoke", "reset"):
            u = await _find_user_by_tg_id(session, tg_id)
            if u and hasattr(u, "is_premium"):
                u.is_premium = False
                u.premium_until = None
                await session.commit()

        context.user_data["admin_waiting"] = None

        pretty = "дефолт" if new_limit is None else ("безлимит" if new_limit == -1 else str(new_limit))
        await update.message.reply_text(
            f"✅ Готово\nПользователь `{tg_id}` → *{pretty}*",
            parse_mode="Markdown",
            reply_markup=admin_menu_kb()
        )
        return True


def register_admin_handlers(app):
    app.add_handler(CallbackQueryHandler(admin_menu_callback, pattern=r"^menu:admin$"))
    app.add_handler(CallbackQueryHandler(admin_subscriptions_callback, pattern=r"^admin:subs:"))
    app.add_handler(CallbackQueryHandler(admin_mode_callback, pattern=r"^admin:mode:"))