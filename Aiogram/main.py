#!/usr/bin/env python3

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import register_handlers
from utils.logger import setup_logging
from config import Config

async def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    config = Config()
    
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is required")
        return
    
    if not config.ADMIN_ID:
        logger.error("ADMIN_ID environment variable is required")
        return
    
    if not config.API_ID or not config.API_HASH:
        logger.error("API_ID and API_HASH environment variables are required")
        return
    
    if not config.GETSMS_API_KEY:
        logger.error("GETSMS_API_KEY environment variable is required")
        return
    
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    register_handlers(dp)
    
    logger.info("Starting Telegram Account Registration Bot...")
    logger.info(f"Admin ID: {config.ADMIN_ID}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
