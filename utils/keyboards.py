"""
Все inline клавиатуры бота
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    from config import is_admin

    keyboard = [
        [InlineKeyboardButton("🔍 Анализ монеты", callback_data="menu:analyze"),
         InlineKeyboardButton("🔥 Тренды", callback_data="menu:trending")],
        [InlineKeyboardButton("📋 Мой Watchlist", callback_data="menu:watchlist"),
         InlineKeyboardButton("🔔 Алерты", callback_data="menu:alerts")],
        [InlineKeyboardButton("⚖️ Сравнить", callback_data="menu:compare"),
         InlineKeyboardButton("🐋 Киты", callback_data="menu:whales")],
        [InlineKeyboardButton("😱 Страх/Жадность", callback_data="menu:fear"),
         InlineKeyboardButton("💼 Портфолио", callback_data="menu:portfolio")],
        [InlineKeyboardButton("🚨 Red Flags", callback_data="menu:redflag"),
         InlineKeyboardButton("🎓 Обучение", callback_data="menu:learn")],
        [InlineKeyboardButton("👤 Профиль", callback_data="menu:profile"),
         InlineKeyboardButton("⚙️ Настройки", callback_data="menu:settings")],
        [InlineKeyboardButton("📊 Рынок", callback_data="menu:market")],
    ]

    if user_id and is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="menu:admin")])

    return InlineKeyboardMarkup(keyboard)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка в главное меню"""
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_keyboard(destination: str = "menu:main") -> InlineKeyboardMarkup:
    """Просто кнопка назад"""
    keyboard = [
        [InlineKeyboardButton("◀️ Назад", callback_data=destination)],
    ]
    return InlineKeyboardMarkup(keyboard)


def analyze_result_keyboard(coin_id: str, in_watchlist: bool = False) -> InlineKeyboardMarkup:
    """Кнопки после анализа монеты"""
    watchlist_btn = (
        InlineKeyboardButton("✅ В Watchlist", callback_data=f"watchlist:remove:{coin_id}")
        if in_watchlist else
        InlineKeyboardButton("➕ В Watchlist", callback_data=f"watchlist:add:{coin_id}")
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Обновить", callback_data=f"analyze:refresh:{coin_id}"),
            watchlist_btn,
        ],
        [
            InlineKeyboardButton("📈 7 дней", callback_data=f"chart:7d:{coin_id}"),
            InlineKeyboardButton("📅 30 дней", callback_data=f"chart:30d:{coin_id}"),
        ],
        [
            InlineKeyboardButton("🚨 Red Flags", callback_data=f"redflag:check:{coin_id}"),
            InlineKeyboardButton("🔔 Алерт", callback_data=f"alert:setup:{coin_id}"),
        ],
        [
            InlineKeyboardButton("🎯 Мой прогноз", callback_data=f"predict:make:{coin_id}"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def prediction_keyboard(coin_id: str) -> InlineKeyboardMarkup:
    """Кнопки для прогноза"""
    keyboard = [
        [
            InlineKeyboardButton("🚀 Памп", callback_data=f"predict:pump:{coin_id}"),
            InlineKeyboardButton("📉 Дамп", callback_data=f"predict:dump:{coin_id}"),
            InlineKeyboardButton("➡️ Стабильно", callback_data=f"predict:stable:{coin_id}"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data=f"analyze:back:{coin_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def trending_keyboard() -> InlineKeyboardMarkup:
    """Кнопки на странице трендов"""
    keyboard = [
        [
            InlineKeyboardButton("🔥 CoinGecko", callback_data="trending:coingecko"),
            InlineKeyboardButton("🐦 Twitter", callback_data="trending:twitter"),
        ],
        [
            InlineKeyboardButton("💬 Reddit", callback_data="trending:reddit"),
            InlineKeyboardButton("📊 По хайпу", callback_data="trending:hype"),
        ],
        [
            InlineKeyboardButton("🔄 Обновить", callback_data="trending:refresh"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def watchlist_keyboard(items: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура watchlist с пагинацией"""
    keyboard = []
    
    start = page * per_page
    end = start + per_page
    page_items = items[start:end]
    
    for item in page_items:
        keyboard.append([
            InlineKeyboardButton(
                f"{item.coin_symbol.upper()} — {item.coin_name}",
                callback_data=f"watchlist:view:{item.coin_id}"
            ),
            InlineKeyboardButton(
                "❌",
                callback_data=f"watchlist:remove:{item.coin_id}"
            ),
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton("◀️", callback_data=f"watchlist:page:{page-1}")
        )
    if end < len(items):
        nav_buttons.append(
            InlineKeyboardButton("▶️", callback_data=f"watchlist:page:{page+1}")
        )
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("➕ Добавить", callback_data="watchlist:add_new"),
        InlineKeyboardButton("🔄 Обновить", callback_data="watchlist:refresh_all"),
    ])
    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
    ])
    
    return InlineKeyboardMarkup(keyboard)


def watchlist_empty_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пустого watchlist"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить монету", callback_data="watchlist:add_new")],
        [InlineKeyboardButton("🔥 Посмотреть тренды", callback_data="menu:trending")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def alerts_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню алертов"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Хайп-алерт", callback_data="alert:type:hype"),
            InlineKeyboardButton("💰 Цена", callback_data="alert:type:price"),
        ],
        [
            InlineKeyboardButton("🐋 Киты", callback_data="alert:type:whale"),
            InlineKeyboardButton("🔥 Тренды", callback_data="alert:type:trending"),
        ],
        [
            InlineKeyboardButton("📋 Мои алерты", callback_data="alert:list"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def alert_list_keyboard(alerts: list) -> InlineKeyboardMarkup:
    """Список алертов пользователя"""
    keyboard = []
    
    for alert in alerts[:10]:
        status = "🟢" if alert.is_active else "🔴"
        coin = alert.coin_symbol.upper() if alert.coin_symbol else "Все"
        text = f"{status} {alert.alert_type} — {coin}"
        
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"alert:view:{alert.id}"),
            InlineKeyboardButton("🗑️", callback_data=f"alert:delete:{alert.id}"),
        ])
    
    keyboard.append([
        InlineKeyboardButton("➕ Новый алерт", callback_data="alert:new"),
    ])
    keyboard.append([
        InlineKeyboardButton("◀️ Назад", callback_data="menu:alerts"),
    ])
    
    return InlineKeyboardMarkup(keyboard)


def compare_keyboard() -> InlineKeyboardMarkup:
    """Меню сравнения"""
    keyboard = [
        [
            InlineKeyboardButton("2 монеты", callback_data="compare:count:2"),
            InlineKeyboardButton("3 монеты", callback_data="compare:count:3"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def whales_menu_keyboard() -> InlineKeyboardMarkup:
    """Меню отслеживания китов"""
    keyboard = [
        [
            InlineKeyboardButton("🐋 Последние", callback_data="whales:recent"),
        ],
        [
            InlineKeyboardButton("₿ BTC", callback_data="whales:coin:bitcoin"),
            InlineKeyboardButton("Ξ ETH", callback_data="whales:coin:ethereum"),
        ],
        [
            InlineKeyboardButton("🔍 Другая монета", callback_data="whales:search"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def fear_greed_keyboard() -> InlineKeyboardMarkup:
    """Индекс страха и жадности"""
    keyboard = [
        [
            InlineKeyboardButton("📊 История", callback_data="fear:history"),
            InlineKeyboardButton("🔄 Обновить", callback_data="fear:refresh"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def portfolio_keyboard(has_items: bool = False) -> InlineKeyboardMarkup:
    """Меню портфолио"""
    if not has_items:
        keyboard = [
            [InlineKeyboardButton("➕ Добавить позицию", callback_data="portfolio:add")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("➕ Добавить", callback_data="portfolio:add"),
                InlineKeyboardButton("📊 Статистика", callback_data="portfolio:stats"),
            ],
            [
                InlineKeyboardButton("🔄 Обновить цены", callback_data="portfolio:refresh"),
            ],
            [
                InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
            ],
        ]
    return InlineKeyboardMarkup(keyboard)


def redflag_keyboard() -> InlineKeyboardMarkup:
    """Проверка на скам"""
    keyboard = [
        [
            InlineKeyboardButton("🔍 Проверить монету", callback_data="redflag:search"),
        ],
        [
            InlineKeyboardButton("📚 Что такое Red Flags?", callback_data="redflag:info"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def learn_keyboard() -> InlineKeyboardMarkup:
    """Меню обучения"""
    keyboard = [
        [
            InlineKeyboardButton("📖 Что такое P&D", callback_data="learn:pnd"),
        ],
        [
            InlineKeyboardButton("🎯 Как читать хайп", callback_data="learn:hype"),
        ],
        [
            InlineKeyboardButton("🧠 Психология трейдинга", callback_data="learn:psychology"),
        ],
        [
            InlineKeyboardButton("✅ Чеклист покупки", callback_data="learn:checklist"),
        ],
        [
            InlineKeyboardButton("🎮 Симулятор", callback_data="learn:simulator"),
        ],
        [
            InlineKeyboardButton("📚 Словарь", callback_data="learn:glossary"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def profile_keyboard() -> InlineKeyboardMarkup:
    """Меню профиля"""
    keyboard = [
        [
            InlineKeyboardButton("🏆 Достижения", callback_data="profile:achievements"),
            InlineKeyboardButton("📊 Статистика", callback_data="profile:stats"),
        ],
        [
            InlineKeyboardButton("📜 История", callback_data="profile:history"),
        ],
        [
            InlineKeyboardButton("🥇 Лидерборд", callback_data="profile:leaderboard"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def settings_keyboard(user) -> InlineKeyboardMarkup:
    """Меню настроек"""
    notif_status = "🔔" if user.notifications_enabled else "🔕"
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"{notif_status} Уведомления", 
                callback_data="settings:toggle_notifications"
            ),
        ],
        [
            InlineKeyboardButton("🌙 Тихие часы", callback_data="settings:quiet_hours"),
        ],
        [
            InlineKeyboardButton("📊 Порог хайпа", callback_data="settings:threshold"),
        ],
        [
            InlineKeyboardButton("🌍 Язык", callback_data="settings:language"),
        ],
        [
            InlineKeyboardButton("🗑️ Удалить данные", callback_data="settings:delete_data"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_keyboard(action: str, data: str = "") -> InlineKeyboardMarkup:
    """Подтверждение действия"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data=f"confirm:yes:{action}:{data}"),
            InlineKeyboardButton("❌ Нет", callback_data=f"confirm:no:{action}:{data}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def alerts_home_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ Создать алерт по монете", callback_data="alert:new")],
        [InlineKeyboardButton("📋 Мои алерты", callback_data="alert:list")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def alert_threshold_keyboard(coin_id: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("5%", callback_data=f"alert:set:{coin_id}:5"),
            InlineKeyboardButton("10%", callback_data=f"alert:set:{coin_id}:10"),
        ],
        [
            InlineKeyboardButton("20%", callback_data=f"alert:set:{coin_id}:20"),
            InlineKeyboardButton("30%", callback_data=f"alert:set:{coin_id}:30"),
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="menu:alerts"),
            InlineKeyboardButton("🏠 Меню", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)