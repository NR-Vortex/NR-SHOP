from aiogram.fsm.state import State, StatesGroup


class VPNStates(StatesGroup):
    waiting_username = State()
