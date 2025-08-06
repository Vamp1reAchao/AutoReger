import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    
    # ваши данные
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "токен бота")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "ваш айди"))
    
    # Telegram API Settings лучше не трогать
    API_ID: int = int(os.getenv("API_ID", "2040"))
    API_HASH: str = os.getenv("API_HASH", "b18441a1ff607e10a989891a5462e627")
    
    # GetSMS Settings
    GETSMS_API_KEY: str = os.getenv("GETSMS_API_KEY", "ваш апи @getsim")
    GETSMS_BASE_URL: str = "https://userapi.getsms.shop"
    
    # Путь к прокси
    PROXY_FILE: str = "data/proxies.txt"
    
    
    SESSION_DIR: str = "sessions"
    
    # страны
    COUNTRIES_FILE: str = "data/countries.json"
    
    # Registration Settings
    MAX_ACCOUNTS_PER_BATCH: int = 10
    SMS_TIMEOUT: int = 180  # 3 minutes
    
    def __post_init__(self):
        os.makedirs(self.SESSION_DIR, exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)
