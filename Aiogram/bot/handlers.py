import os
import json
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.keyboards import (
    get_main_menu,
    get_proxy_choice_keyboard,
    get_proxy_management_keyboard,
    get_back_keyboard,
    get_cancel_keyboard,
    get_confirmation_keyboard,
    get_country_keyboard
)
from bot.states import RegistrationStates, ProxyStates, CountryStates
from services.getsms import GetSMSAPI
from services.telegram_client import TelegramAccountRegistrator
from services.proxy_manager import ProxyManager
from config import Config
from utils.validators import validate_country_id
import asyncio

logger = logging.getLogger(__name__)

config = Config()
getsms = GetSMSAPI(config.GETSMS_API_KEY)
registrator = TelegramAccountRegistrator()
proxy_manager = ProxyManager()

router = Router()

def is_admin(user_id: int) -> bool:
    return user_id == config.ADMIN_ID

async def send_session_file(bot, chat_id: int, session_file: str):
    session_path = os.path.join(config.SESSION_DIR, session_file)
    if os.path.exists(session_path):
        try:
            document = FSInputFile(session_path, filename=session_file)
            await bot.send_document(chat_id, document, caption=f"📁 Session file: {session_file}")
        except Exception as e:
            logger.error(f"Failed to send session file: {e}")
            await bot.send_message(chat_id, f"❌ Ошибка отправки файла сессии: {e}")

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    welcome_text = (
        "🚀 <b>AutoReger - Автоматическая регистрация</b>\n\n"
        "💎 Профессиональный инструмент для массовой регистрации Telegram аккаунтов\n"
        "⚡ Быстро • Надежно • Безопасно\n\n"
        "🎯 <b>Выберите действие:</b>"
    )

    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n💫 Добро пожаловать в RegerAiogram\n🎯 <b>Выберите действие:</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )

@router.callback_query(F.data == "register_accounts")
async def register_accounts_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_for_country)

    text = (
        "🎯 <b>Регистрация аккаунтов</b>\n\n"
        "🌍 Выберите страну для получения номеров:\n"
        "📝 Введите <code>ID страны</code> или <code>0</code> для любой страны\n\n"
        "💡 <i>Используйте команду 'Экспорт стран' для получения списка ID</i>"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(RegistrationStates.waiting_for_country)
async def process_country_input(message: Message, state: FSMContext):
    if not message.text or not validate_country_id(message.text.strip()):
        await message.answer(
            "⚠️ <b>Неверный формат!</b>\n\n📝 Введите корректный ID страны (только цифры)\n💡 Пример: <code>7</code> для России или <code>0</code> для любой страны",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    country_id = message.text.strip()

    loading_msg = await message.answer(
        "🔍 <b>Анализ данных...</b>\n\n💰 Получаем актуальные цены\n🌍 Проверяем доступность номеров\n⏳ Пожалуйста, подождите...",
        parse_mode="HTML"
    )

    try:
        price, country_name = await getsms.get_price_and_country_name(country_id)

        await state.update_data(country_id=country_id, price=price, country_name=country_name)
        await state.set_state(RegistrationStates.waiting_for_count)

        text = (
            f"✅ <b>Страна выбрана успешно!</b>\n\n"
            f"🌍 <b>Страна:</b> {country_name}\n"
            f"💰 <b>Стоимость номера:</b> <code>{price:.2f}₽</code>\n\n"
            f"📊 <b>Укажите количество аккаунтов</b>\n"
            f"📝 Введите число от <code>1</code> до <code>{config.MAX_ACCOUNTS_PER_BATCH}</code>\n\n"
            f"💡 <i>Рекомендуем начать с небольшого количества</i>"
        )

        await loading_msg.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )

    except Exception as e:
        logger.error(f"Failed to get price: {e}")
        await loading_msg.edit_text(
            f"🚫 <b>Ошибка получения данных</b>\n\n⚠️ {str(e)}\n\n💡 <b>Попробуйте:</b>\n• Другой ID страны\n• Проверить баланс GetSMS\n• Обратиться в поддержку",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )

@router.message(RegistrationStates.waiting_for_count)
async def process_count_selection(message: Message, state: FSMContext):
    if not message.text or not message.text.isdigit():
        await message.answer(
            "⚠️ <b>Неверный формат!</b>\n\n📝 Введите корректное число\n💡 Пример: <code>5</code> для регистрации 5 аккаунтов",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    count = int(message.text.strip())

    if count < 1 or count > config.MAX_ACCOUNTS_PER_BATCH:
        await message.answer(
            f"⚠️ <b>Неверное количество!</b>\n\n📊 Допустимый диапазон: <code>1-{config.MAX_ACCOUNTS_PER_BATCH}</code>\n💡 Введите число в указанном диапазоне",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
        return

    data = await state.get_data()
    price = data.get('price', 0)
    country_name = data.get('country_name', 'Неизвестно')
    total_cost = price * count

    try:
        balance = await getsms.get_balance()
        can_afford = balance >= total_cost

        await state.update_data(count=count, total_cost=total_cost)
        await state.set_state(RegistrationStates.waiting_for_confirmation)
        await proxy_manager.load_proxies()
        proxy_stats = proxy_manager.get_stats()

        text = (
            f"👨‍💻 <b>developer:</b> <a href='https://t.me/AutoZelenka'>RW Project</a>\n"
            f"📊 <b>Подтверждение заказа</b>\n\n"
            f"🌍 <b>Страна:</b> {country_name}\n"
            f"📱 <b>Количество:</b> {count} аккаунтов\n"
            f"💰 <b>Цена за номер:</b> {price:.2f}₽\n"
            f"💳 <b>Общая стоимость:</b> <code>{total_cost:.2f}₽</code>\n"
            f"💰 <b>Ваш баланс:</b> <code>{balance:.2f}₽</code>\n"
            f"{'✅' if can_afford else '❌'} <b>Достаточно средств:</b> {'Да' if can_afford else 'Нет'}\n\n"
            f"🔧 <b>Прокси:</b> {proxy_stats.get('working_proxies', 0)} доступно\n"
        )

        if can_afford:
            text += "✅ Подтвердите регистрацию аккаунтов:"
        else:
            text += "❌ Недостаточно средств на балансе!"

        keyboard = get_confirmation_keyboard("registration") if can_afford else get_cancel_keyboard()

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Failed to check balance: {e}")
        await message.answer(
            f"❌ <b>Ошибка проверки баланса</b>\n\n{str(e)}",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )

@router.callback_query(F.data == "confirm_registration")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    country_id = data.get('country_id', '0')
    count = data.get('count', 1)
    country_name = data.get('country_name', 'Неизвестно')

    await register_accounts_with_live_updates(
        callback.bot,
        callback.message,
        country_id,
        count,
        country_name,
        state
    )

async def register_accounts_with_live_updates(bot, message, country_id: str, count: int, country_name: str, state: FSMContext):
    successful_accounts = []
    failed_accounts = []
    current_logs = []

    def add_log(text: str):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        current_logs.append(f"[{timestamp}] {text}")
        if len(current_logs) > 15:
            current_logs.pop(0)

    async def update_message():
        logs_text = "\n".join(current_logs[-10:]) if current_logs else "Подготовка..."

        message_text = (
            f"🚀 <b>Регистрация аккаунтов</b>\n\n"
            f"🌍 Страна: {country_name}\n"
            f"📊 Аккаунтов: {count}\n"
            f"✅ Успешно: {len(successful_accounts)}\n"
            f"❌ Ошибок: {len(failed_accounts)}\n\n"
            f"📝 <b>Логи:</b>\n"
            f"<code>{logs_text}</code>"
        )

        try:
            await message.edit_text(message_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to update message: {e}")

    add_log("🚀 Запускаю параллельную регистрацию аккаунтов...")
    await update_message()

    def registration_log_callback(log_message: str):
        add_log(log_message)
        asyncio.create_task(update_message_safe())

    async def update_message_safe():
        try:
            await update_message()
        except Exception as e:
            logger.error(f"Failed to update message: {e}")

    try:
        results = await registrator.register_multiple_accounts_parallel(
            count=count,
            country_id=country_id,
            first_name="AutoZelenka",
            last_name="User",
            log_callback=registration_log_callback
        )

        for result in results:
            if result['status'] == 'success':
                successful_accounts.append(result)

                if result.get('session_file'):
                    add_log(f"📁 Отправляю файл сессии для аккаунта #{result.get('account_number', '?')}...")
                    await update_message()
                    await send_session_file(bot, message.chat.id, result['session_file'])
                    add_log("✅ Файл сессии отправлен")
                    await update_message()
            else:
                failed_accounts.append(result)

    except Exception as e:
        logger.error(f"Parallel registration failed: {e}")
        add_log(f"❌ Критическая ошибка регистрации: {str(e)}")
        await update_message()

    await state.clear()
    add_log("🏁 Регистрация завершена!")
    await update_message()

    summary_text = (
        f"🏁 <b>Регистрация завершена!</b>\n\n"
        f"🌍 <b>Страна:</b> {country_name}\n"
        f"📊 <b>Итоги:</b>\n"
        f"✅ Успешно: {len(successful_accounts)}\n"
        f"❌ Ошибок: {len(failed_accounts)}\n"
        f"📋 Всего: {count}\n\n"
    )

    if successful_accounts:
        summary_text += "🎉 <b>Успешные регистрации:</b>\n"
        for result in successful_accounts:
            summary_text += f"📱 <code>{result['phone']}</code> ✅\n"

    if failed_accounts:
        summary_text += "\n❌ <b>Неудачные попытки:</b>\n"
        for result in failed_accounts[:3]:
            phone = result.get('phone', 'Номер не получен')
            summary_text += f"📱 {phone}: {result['message'][:50]}...\n"

        if len(failed_accounts) > 3:
            summary_text += f"... и еще {len(failed_accounts) - 3} ошибок\n"

    await message.edit_text(
        summary_text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

async def register_account_with_live_updates(country_id: str, proxy_string: str, first_name: str, last_name: str, logger_callback):
    try:
        await logger_callback("🔍 Поиск доступного номера...")
        phone, order_id = await getsms.get_number(country_id)

        if not phone or not order_id:
            await logger_callback("❌ Не удалось получить номер")
            return {'status': 'error', 'message': 'Failed to get phone number', 'phone': None}

        await logger_callback(f"✅ Получен номер: {phone}")

        if proxy_string:
            await logger_callback("🔗 Настройка прокси...")
            await logger_callback("✅ Прокси настроен")

        await logger_callback("📁 Создание сессии...")
        await logger_callback("🤖 Инициализация клиента Telegram...")
        await logger_callback("🌐 Подключение к Telegram...")

        result = await registrator.register_account_with_name(
            country_id=country_id,
            proxy_string=proxy_string,
            first_name=first_name,
            last_name=last_name
        )

        if 'steps' in result:
            for step in result['steps']:
                await logger_callback(step)
                await asyncio.sleep(0.3)

        return result

    except Exception as e:
        await logger_callback(f"❌ Ошибка: {str(e)}")
        return {'status': 'error', 'message': str(e), 'phone': None}


@router.callback_query(F.data == "check_balance")
async def check_balance(callback: CallbackQuery):
    try:
        balance = await getsms.get_balance()
        text = f"💰 <b>Баланс GetSMS</b>\n\n💵 Текущий баланс: <code>{balance}₽</code>"
    except Exception as e:
        logger.error(f"Failed to check balance: {e}")
        text = f"❌ <b>Ошибка получения баланса</b>\n\n{str(e)}"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "export_countries")
async def export_countries(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌍 <b>Экспорт списка стран</b>\n\n⏳ Получение данных...",
        parse_mode="HTML"
    )

    try:
        countries = await getsms.get_countries()

        if not countries:
            await callback.message.edit_text(
                "❌ <b>Ошибка</b>\n\nНе удалось получить список стран.",
                parse_mode="HTML",
                reply_markup=get_back_keyboard()
            )
            return

        countries_file = config.COUNTRIES_FILE
        with open(countries_file, 'w', encoding='utf-8') as f:
            json.dump(countries, f, ensure_ascii=False, indent=2)

        text_file = "data/countries.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("ID -- Страна\n")
            f.write("-" * 20 + "\n")
            for country in countries:
                f.write(f"{country.get('id', 'N/A')} -- {country.get('name', 'N/A')}\n")

        document = FSInputFile(text_file, filename="countries.txt")
        await callback.message.answer_document(
            document,
            caption=f"🌍 <b>Список стран</b>\n\nВсего стран: <code>{len(countries)}</code>",
            parse_mode="HTML"
        )

        await callback.message.edit_text(
            f"✅ <b>Список стран экспортирован</b>\n\nВсего стран: <code>{len(countries)}</code>",
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Failed to export countries: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка экспорта</b>\n\n{str(e)}",
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )

@router.callback_query(F.data == "manage_proxies")
async def manage_proxies(callback: CallbackQuery):
    loaded_count = await proxy_manager.load_proxies()
    stats = proxy_manager.get_stats()

    text = (
        f"🔧 <b>Управление прокси</b>\n\n"
        f"📁 Загружено: <code>{loaded_count}</code>\n"
        f"✅ Рабочих: <code>{stats['working']}</code>\n"
        f"⏳ Используется: <code>{stats['used']}</code>\n\n"
        f"Выберите действие:"
    )

    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_proxy_management_keyboard()
        )
    except Exception:
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_proxy_management_keyboard()
        )

@router.callback_query(F.data == "test_proxies")
async def test_proxies(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧪 <b>Тестирование прокси</b>\n\n⏳ Загрузка прокси...",
        parse_mode="HTML"
    )

    try:
        loaded_count = await proxy_manager.load_proxies()

        if loaded_count == 0:
            await callback.message.edit_text(
                "❌ <b>Прокси не найдены</b>\n\nЗагрузите файл прокси для тестирования.",
                parse_mode="HTML",
                reply_markup=get_back_keyboard()
            )
            return

        await callback.message.edit_text(
            f"🧪 <b>Тестирование прокси</b>\n\n⏳ Тестирование {loaded_count} прокси...",
            parse_mode="HTML"
        )

        working_count = await proxy_manager.test_all_proxies()

        stats = proxy_manager.get_stats()

        text = (
            f"✅ <b>Тестирование завершено</b>\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"📁 Загружено: <code>{stats['total_loaded']}</code>\n"
            f"✅ Рабочих: <code>{stats['working_proxies']}</code>\n"
            f"❌ Нерабочих: <code>{stats['total_loaded'] - stats['working_proxies']}</code>\n"
            f"📋 Доступно: <code>{stats['available_proxies']}</code>"
        )

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Failed to test proxies: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка тестирования</b>\n\n{str(e)}",
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )

@router.callback_query(F.data == "proxy_stats")
async def proxy_stats(callback: CallbackQuery):
    try:
        await proxy_manager.load_proxies()
        stats = proxy_manager.get_stats()

        text = (
            f"📊 <b>Статистика прокси</b>\n\n"
            f"📁 Загружено: <code>{stats['total_loaded']}</code>\n"
            f"✅ Рабочих: <code>{stats['working_proxies']}</code>\n"
            f"🔄 Использовано: <code>{stats['used_proxies']}</code>\n"
            f"📋 Доступно: <code>{stats['available_proxies']}</code>"
        )

    except Exception as e:
        logger.error(f"Failed to get proxy stats: {e}")
        text = f"❌ <b>Ошибка получения статистики</b>\n\n{str(e)}"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "reset_proxies")
async def reset_proxies(callback: CallbackQuery):
    proxy_manager.reset_used_proxies()

    await callback.message.edit_text(
        "✅ <b>Список использованных прокси сброшен</b>\n\nВсе прокси снова доступны для использования.",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "show_stats")
async def show_stats(callback: CallbackQuery):
    try:
        balance = await getsms.get_balance()

        await proxy_manager.load_proxies()
        proxy_stats = proxy_manager.get_stats()

        session_files = 0
        if os.path.exists(config.SESSION_DIR):
            session_files = len([f for f in os.listdir(config.SESSION_DIR) if f.endswith('.session')])

        text = (
            f"📊 <b>Общая статистика</b>\n\n"
            f"💰 <b>GetSMS баланс:</b> <code>{balance}₽</code>\n\n"
            f"🔧 <b>Прокси:</b>\n"
            f"📁 Загружено: <code>{proxy_stats['total_loaded']}</code>\n"
            f"✅ Рабочих: <code>{proxy_stats['working_proxies']}</code>\n"
            f"📋 Доступно: <code>{proxy_stats['available_proxies']}</code>\n\n"
            f"📱 <b>Сессии:</b> <code>{session_files}</code> файлов"
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        text = f"❌ <b>Ошибка получения статистики</b>\n\n{str(e)}"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "upload_proxies")
async def upload_proxies(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProxyStates.waiting_for_proxy_file)

    await callback.message.edit_text(
        "📁 <b>Загрузка прокси</b>\n\n"
        "Отправьте файл с прокси в формате:\n"
        "<code>ip:port:username:password</code>\n\n"
        "По одному прокси на строку.",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(ProxyStates.waiting_for_proxy_file, F.document)
async def process_proxy_file(message: Message, state: FSMContext):
    await state.clear()

    if not message.document:
        await message.answer(
            "❌ Пожалуйста, отправьте файл с прокси.",
            reply_markup=get_cancel_keyboard()
        )
        return

    try:
        file = await message.bot.get_file(message.document.file_id)
        if not file.file_path:
            raise Exception("Could not get file path")

        file_content = await message.bot.download_file(file.file_path)
        if not file_content:
            raise Exception("Could not download file")

        content = file_content.read().decode('utf-8')

        new_proxies = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                new_proxies.append(line)

        existing_proxies = []
        try:
            with open(config.PROXY_FILE, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        existing_proxies.append(line)
        except FileNotFoundError:
            pass

        all_proxies = list(set(existing_proxies + new_proxies))

        with open(config.PROXY_FILE, 'w', encoding='utf-8') as f:
            f.write("# Proxy file format: ip:port:username:password\n")
            f.write("# Example:\n")
            f.write("# 192.168.1.1:8080:user:pass\n")
            f.write("# 10.0.0.1:3128:admin:secret\n\n")
            f.write("# Add your proxies below (one per line)\n")
            f.write("# Lines starting with # are ignored\n\n")
            for proxy in all_proxies:
                f.write(f"{proxy}\n")

        loaded_count = await proxy_manager.load_proxies()

        added_count = len(new_proxies)
        valid_new = [p for p in new_proxies if p in proxy_manager.proxies]

        text = (
            f"✅ <b>Прокси добавлены</b>\n\n"
            f"📁 Новых прокси: <code>{added_count}</code>\n"
            f"✅ Валидных: <code>{len(valid_new)}</code>\n"
            f"📊 Всего в файле: <code>{loaded_count}</code>\n\n"
            f"💡 Используйте 'Тестировать прокси' для проверки их работоспособности."
        )

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )

    except Exception as e:
        logger.error(f"Failed to process proxy file: {e}")
        await message.answer(
            f"❌ <b>Ошибка загрузки файла</b>\n\n{str(e)}",
            parse_mode="HTML",
            reply_markup=get_back_keyboard()
        )

def register_handlers(dp):
    dp.include_router(router)