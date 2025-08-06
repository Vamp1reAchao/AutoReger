from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🎯 Регистрация аккаунтов", callback_data="register_accounts")
    )
    builder.row(
        InlineKeyboardButton(text="🌍 Экспорт стран", callback_data="export_countries"),
        InlineKeyboardButton(text="⚙️ Управление прокси", callback_data="manage_proxies")
    )
    builder.row(
        InlineKeyboardButton(text="💎 Баланс GetSMS", callback_data="check_balance"),
        InlineKeyboardButton(text="📈 Статистика", callback_data="show_stats")
    )
    
    return builder.as_markup()

def get_proxy_choice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✨ Использовать прокси", callback_data="use_proxies_yes"),
        InlineKeyboardButton(text="🚫 Без прокси", callback_data="use_proxies_no")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_proxy_management_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📤 Загрузить прокси", callback_data="upload_proxies"),
        InlineKeyboardButton(text="🔍 Тестировать прокси", callback_data="test_proxies")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Статистика прокси", callback_data="proxy_stats"),
        InlineKeyboardButton(text="🔄 Сбросить использованные", callback_data="reset_proxies")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚫 Отмена", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✨ Подтвердить", callback_data=f"confirm_{action}"),
        InlineKeyboardButton(text="🚫 Отмена", callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_country_keyboard(countries: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    popular_countries = [
        {"id": "0", "name": "🌍 Любая страна"},
        {"id": "7", "name": "🇷🇺 Россия"},
        {"id": "1", "name": "🇺🇸 США"},
        {"id": "16", "name": "🇺🇦 Украина"},
        {"id": "2", "name": "🇰🇿 Казахстан"}
    ]
    
    for country in popular_countries:
        builder.row(
            InlineKeyboardButton(
                text=country["name"], 
                callback_data=f"country_{country['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="📋 Полный список стран", callback_data="export_countries")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()
    
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="back_to_main")
    )
    
    return builder.as_markup()
