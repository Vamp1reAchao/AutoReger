"""Telegram client service for account registration"""

import os
import logging
import asyncio
from typing import Optional, Dict, Tuple, List, Callable
from telethon import TelegramClient
from telethon.errors import (
    PhoneNumberInvalidError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    FloodWaitError,
    PhoneNumberBannedError,
    ApiIdInvalidError
)
from config import Config
from services.getsms import GetSMSAPI
from services.proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

class TelegramAccountRegistrator:

    def __init__(self):
        self.config = Config()
        self.getsms = GetSMSAPI(self.config.GETSMS_API_KEY)
        self.proxy_manager = ProxyManager()

    async def register_account_with_callback(self, country_id: str = "0", proxy_string: Optional[str] = None,
                                           first_name: str = "User", last_name: str = "Telegram",
                                           log_callback: Optional[Callable] = None) -> Dict:
        def log(message: str):
            logger.info(message)
            if log_callback:
                log_callback(message)

        result = {
            'status': 'error',
            'message': 'Unknown error',
            'phone': None,
            'session_file': None,
            'proxy_used': proxy_string,
            'first_name': first_name,
            'last_name': last_name,
            'steps': []
        }

        client = None
        order_id = None

        try:
            log('📞 Покупаю номер телефона...')
            phone, order_id = await self.getsms.get_number(country_id)

            if not phone or not order_id:
                log('❌ Не удалось купить номер телефона от GetSMS')
                result['message'] = 'Failed to get phone number from GetSMS'
                return result

            result['phone'] = phone
            log(f'✅ Купил номер телефона: {phone}')

            proxy_config = None
            if proxy_string:
                log(f'🔗 Настраиваю прокси: {proxy_string.split(":")[0]}:***')
                proxy_config = self.proxy_manager.get_proxy_config(proxy_string)
                if not proxy_config:
                    log('❌ Неверная конфигурация прокси')
                    result['message'] = 'Invalid proxy configuration'
                    return result
                log('✅ Прокси настроен успешно')

            log('📁 Создаю файл сессии...')
            session_name = f"session_{phone.replace('+', '')}"
            session_path = os.path.join(self.config.SESSION_DIR, session_name)

            log('🤖 Инициализирую клиент Telegram...')
            if proxy_config:
                client = TelegramClient(
                    session_path,
                    self.config.API_ID,
                    self.config.API_HASH,
                    proxy=proxy_config
                )
                log("✅ Клиент создан с прокси")
            else:
                client = TelegramClient(
                    session_path,
                    self.config.API_ID,
                    self.config.API_HASH
                )
                log("✅ Клиент создан без прокси")

            log('🌐 Подключаюсь к серверам Telegram...')
            await client.connect()
            log('✅ Подключение к Telegram установлено')

            log("🔍 Проверяю авторизацию номера...")
            if await client.is_user_authorized():
                log('❌ Номер уже зарегистрирован в Telegram')
                result['status'] = 'error'
                result['message'] = 'Phone number already registered'
                return result

            log('📱 Отправляю запрос на SMS код...')
            sent_code = await client.send_code_request(phone)
            log('✅ Запрос на SMS код отправлен')

            log('⏳ Жду SMS код (3 минуты)...')
            sms_code = await self.getsms.wait_for_sms(order_id, timeout=180)

            if not sms_code:
                log('❌ SMS код не пришел за 3 минуты - отменяю заказ')
                await self.getsms.finish_order(order_id)
                result['message'] = 'SMS code timeout - order cancelled'
                return result

            log(f'✅ Получил SMS код: {sms_code}')

            try:
                log('🔑 Регистрирую аккаунт с SMS кодом...')
                await client.sign_up(code=sms_code, first_name=first_name, last_name=last_name)
                log(f'✅ Аккаунт успешно зарегистрирован как {first_name} {last_name}!')

                me = await client.get_me()

                result['status'] = 'success'
                result['message'] = f'Account registered successfully as {first_name} {last_name}'
                result['session_file'] = f"{session_name}.session"
                log(f'🌟 Регистрация завершена! ID: {me.id}')

                return result

            except SessionPasswordNeededError:
                log('❌ Требуется пароль двухфакторной аутентификации')
                result['message'] = 'Account has 2FA enabled'
                return result

            except PhoneCodeInvalidError:
                log('❌ Неверный SMS код')
                result['message'] = 'Invalid SMS code'
                return result

        except PhoneNumberInvalidError:
            log('❌ Неверный номер телефона')
            result['message'] = 'Invalid phone number'

        except PhoneNumberBannedError:
            log('❌ Номер телефона заблокирован в Telegram')
            result['message'] = 'Phone number is banned'

        except ApiIdInvalidError:
            log('❌ Неверный API ID или Hash')
            result['message'] = 'Invalid API ID or Hash'

        except FloodWaitError as e:
            log(f'❌ Telegram FloodWait: нужно ждать {e.seconds} секунд')
            result['message'] = f'Flood wait: {e.seconds} seconds'

        except Exception as e:
            log(f'❌ Неизвестная ошибка: {str(e)}')
            result['message'] = f'Registration failed: {str(e)}'

        finally:
            if client and hasattr(client, 'disconnect'):
                try:
                    if client.is_connected():
                        await client.disconnect()
                        log("✅ Клиент Telegram отключен")
                except Exception as e:
                    logger.error(f"Ошибка при отключении клиента: {e}")

            if order_id and result['status'] != 'success':
                try:
                    await self.getsms.finish_order(order_id)
                    log(f"✅ Заказ SMS {order_id} отменен")
                except Exception as e:
                    log(f"❌ Ошибка отмены заказа: {e}")

        return result

    async def register_multiple_accounts_parallel(self, count: int, country_id: str = "0", 
                                                first_name: str = "User", last_name: str = "Telegram",
                                                log_callback: Optional[Callable] = None) -> List[Dict]:
        def log(message: str):
            logger.info(message)
            if log_callback:
                log_callback(message)

        if count > self.config.MAX_ACCOUNTS_PER_BATCH:
            count = self.config.MAX_ACCOUNTS_PER_BATCH

        log("🔍 Загружаю прокси...")
        await self.proxy_manager.load_proxies()

        if not self.proxy_manager.proxies:
            log("❌ Прокси не найдены в файле")
            return []

        log(f"🧪 Тестирую {len(self.proxy_manager.proxies)} прокси...")
        await self.proxy_manager.test_all_proxies()

        working_count = len(self.proxy_manager.working_proxies)
        log(f"✅ Найдено {working_count} рабочих прокси")

        if working_count < count:
            log(f"⚠️ Рабочих прокси ({working_count}) меньше чем аккаунтов ({count})")
            count = working_count

        if count == 0:
            log("❌ Нет рабочих прокси для регистрации")
            return []

        selected_proxies = []
        available_proxies = self.proxy_manager.working_proxies.copy()

        for i in range(count):
            if available_proxies:
                proxy = available_proxies.pop(0)
                selected_proxies.append(proxy)
                log(f"🔗 Аккаунт #{i+1} будет использовать прокси: {proxy.split(':')[0]}:***")
            else:
                log(f"❌ Не хватает прокси для аккаунта #{i+1}")
                break

        log(f"🚀 Начинаю параллельную регистрацию {len(selected_proxies)} аккаунтов...")

        tasks = []
        for i, proxy in enumerate(selected_proxies):
            account_num = i + 1

            def make_account_log_callback(account_number):
                def account_log(message):
                    log(f"[Аккаунт #{account_number}] {message}")
                return account_log

            account_log_callback = make_account_log_callback(account_num)

            task = asyncio.create_task(
                self.register_account_with_callback(
                    country_id=country_id,
                    proxy_string=proxy,
                    first_name=first_name,
                    last_name=last_name,
                    log_callback=account_log_callback
                )
            )
            tasks.append(task)

        log("⏳ Жду завершения всех регистраций...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = 0
        failed = 0
        final_results = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log(f"❌ Аккаунт #{i+1} завершился с ошибкой: {str(result)}")
                final_results.append({
                    'status': 'error',
                    'message': str(result),
                    'phone': None,
                    'account_number': i+1
                })
                failed += 1
            elif isinstance(result, dict):
                result['account_number'] = i+1
                final_results.append(result)
                if result['status'] == 'success':
                    successful += 1
                    log(f"✅ Аккаунт #{i+1} успешно зарегистрирован: {result['phone']}")
                else:
                    failed += 1
                    log(f"❌ Аккаунт #{i+1} не удался: {result['message']}")

        log(f"🏁 Параллельная регистрация завершена: {successful} успешно, {failed} неудачно")
        return final_results

    async def register_account(self, country_id: str = "0", proxy_string: Optional[str] = None) -> Dict:
        return await self.register_account_with_callback(country_id, proxy_string)

    async def register_account_with_name(self, country_id: str = "0", proxy_string: Optional[str] = None,
                                       first_name: str = "User", last_name: str = "Telegram") -> Dict:
        return await self.register_account_with_callback(country_id, proxy_string, first_name, last_name)

    async def register_multiple_accounts(self, count: int, country_id: str = "0", use_proxies: bool = True) -> List[Dict]:
        if use_proxies:
            return await self.register_multiple_accounts_parallel(count, country_id)
        else:
            results = []
            for i in range(count):
                result = await self.register_account_with_callback(country_id, None)
                results.append(result)
            return results