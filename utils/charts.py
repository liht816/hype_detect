"""
Генерация графиков
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import io

# Для работы без GUI
plt.switch_backend('Agg')

# Цветовая схема
COLORS = {
    "background": "#16213e",
    "panel": "#1a1a2e",
    "text": "#ffffff",
    "grid": "#333333",
    "green": "#00ff88",
    "red": "#ff6b6b",
    "yellow": "#ffd93d",
    "orange": "#ff9f43",
}


def create_hype_chart(
    price_history: list,
    mentions_by_day: dict,
    coin_symbol: str,
    hype_score: int
) -> io.BytesIO:
    """
    Создаёт график цены
    
    Args:
        price_history: [(timestamp_ms, price), ...]
        mentions_by_day: {"2024-01-15": 5, ...} (не используется сейчас)
        coin_symbol: Символ монеты
        hype_score: Текущий хайп-скор
    
    Returns:
        BytesIO с PNG изображением
    """
    
    try:
        # Создаём новую фигуру
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor(COLORS["background"])
        ax.set_facecolor(COLORS["panel"])
        if not price_history:
            price_history = [[int(datetime.now().timestamp() * 1000), 0.0]]
        if price_history and len(price_history) > 0:
            # Парсим данные
            dates = []
            prices = []
            
            for item in price_history:
                try:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        timestamp = item[0]
                        price = item[1]
                        
                        # Конвертируем timestamp
                        if timestamp > 10000000000:  # миллисекунды
                            dt = datetime.fromtimestamp(timestamp / 1000)
                        else:
                            dt = datetime.fromtimestamp(timestamp)
                        
                        dates.append(dt)
                        prices.append(float(price))
                except Exception as e:
                    continue
            
            if dates and prices:
                # Рисуем линию цены
                ax.plot(dates, prices, color=COLORS["green"], linewidth=2.5, label='Цена USD')
                ax.fill_between(dates, prices, alpha=0.2, color=COLORS["green"])
                ax.set_ylabel('Цена (USD)', color=COLORS["green"], fontsize=12, fontweight='bold')
                ax.tick_params(axis='y', labelcolor=COLORS["green"])
                
                # Форматируем ось X
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
                
                # Определяем интервал для оси X
                if len(dates) > 20:
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
                else:
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
                
                plt.xticks(rotation=45, ha='right')
        
        # Заголовок с цветом по хайпу
        if hype_score >= 80:
            title_color = COLORS["red"]
        elif hype_score >= 60:
            title_color = COLORS["orange"]
        elif hype_score >= 40:
            title_color = COLORS["yellow"]
        else:
            title_color = COLORS["green"]
        
        ax.set_title(
            f'{coin_symbol.upper()} — Хайп-скор: {hype_score}/100',
            fontsize=18,
            fontweight='bold',
            color=title_color,
            pad=20
        )
        
        # Сетка
        ax.grid(True, alpha=0.3, color=COLORS["grid"])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        plt.tight_layout()
        
        # Сохраняем в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=COLORS["background"])
        buf.seek(0)
        
        # Закрываем фигуру чтобы освободить память
        plt.close(fig)
        plt.close('all')
        
        return buf
        
    except Exception as e:
        print(f"Chart creation error: {e}")
        
        # Создаём пустой график с сообщением об ошибке
        plt.close('all')
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor(COLORS["background"])
        ax.set_facecolor(COLORS["panel"])
        ax.text(0.5, 0.5, f'{coin_symbol.upper()}\n\nГрафик недоступен', 
                ha='center', va='center', fontsize=20, color='white',
                transform=ax.transAxes)
        ax.axis('off')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=COLORS["background"])
        buf.seek(0)
        plt.close(fig)
        plt.close('all')
        
        return buf


def create_simple_chart(coin_symbol: str, hype_score: int) -> io.BytesIO:
    """
    Создаёт простой график-заглушку
    """
    plt.close('all')
    
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(COLORS["background"])
    ax.set_facecolor(COLORS["panel"])
    
    # Хайп-бар
    if hype_score >= 80:
        bar_color = COLORS["red"]
    elif hype_score >= 60:
        bar_color = COLORS["orange"]
    elif hype_score >= 40:
        bar_color = COLORS["yellow"]
    else:
        bar_color = COLORS["green"]
    
    # Рисуем прогресс-бар хайпа
    ax.barh([0], [hype_score], color=bar_color, height=0.5)
    ax.barh([0], [100], color='gray', alpha=0.3, height=0.5)
    
    ax.set_xlim(0, 100)
    ax.set_ylim(-1, 1)
    ax.axis('off')
    
    ax.text(50, 0.7, f'{coin_symbol.upper()}', ha='center', va='center', 
            fontsize=24, color='white', fontweight='bold')
    ax.text(50, -0.7, f'Хайп-скор: {hype_score}/100', ha='center', va='center',
            fontsize=16, color='white')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=COLORS["background"])
    buf.seek(0)
    plt.close(fig)
    plt.close('all')
    
    return buf