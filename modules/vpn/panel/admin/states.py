from aiogram.fsm.state import State, StatesGroup


class VPNPanelStates(StatesGroup):
    name = State(); url = State(); username = State(); password = State()
    trial_volume = State(); trial_duration = State()
