from aiogram.fsm.state import State, StatesGroup


class PartnershipStates(StatesGroup):
    full_name = State()
    contact = State()
    field = State()
    description = State()
