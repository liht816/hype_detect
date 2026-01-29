from handlers.start import register_start_handlers
from handlers.analyze import register_analyze_handlers
from handlers.trending import register_trending_handlers
from handlers.watchlist import register_watchlist_handlers
from handlers.alerts import register_alerts_handlers
from handlers.compare import register_compare_handlers
from handlers.whales import register_whales_handlers
from handlers.fear_greed import register_fear_greed_handlers
from handlers.portfolio import register_portfolio_handlers
from handlers.learn import register_learn_handlers
from handlers.profile import register_profile_handlers
from handlers.settings import register_settings_handlers
from handlers.redflag import register_redflag_handlers
from handlers.admin import register_admin_handlers
from handlers.market import register_market_handlers

def register_all_handlers(app):
    register_start_handlers(app)
    register_analyze_handlers(app)
    register_trending_handlers(app)
    register_watchlist_handlers(app)
    register_alerts_handlers(app)
    register_compare_handlers(app)
    register_whales_handlers(app)
    register_fear_greed_handlers(app)
    register_portfolio_handlers(app)
    register_learn_handlers(app)
    register_profile_handlers(app)
    register_settings_handlers(app)
    register_redflag_handlers(app)
    register_admin_handlers(app)
    register_market_handlers(app)
