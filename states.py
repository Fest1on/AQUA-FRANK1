from aiogram.fsm.state import State, StatesGroup


class OrderProcess(StatesGroup):
    waiting_for_name = State()
    waiting_for_manual_qty = State()
    waiting_for_bottle_exchange = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_payment = State()
    waiting_for_confirmation = State()


class AdminProcess(StatesGroup):
    waiting_for_broadcast = State()
