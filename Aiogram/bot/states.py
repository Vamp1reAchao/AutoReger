from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_country = State()
    waiting_for_count = State()
    waiting_for_confirmation = State()
    registering_accounts = State()

class ProxyStates(StatesGroup):
    waiting_for_proxy_file = State()

class CountryStates(StatesGroup):
    exporting_countries = State()
