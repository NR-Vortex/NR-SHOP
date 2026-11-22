from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    waiting_initial_message = State()
    waiting_customer_reply = State()
    waiting_admin_reply = State()
