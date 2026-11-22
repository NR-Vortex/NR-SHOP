from aiogram.fsm.state import (
    State,
    StatesGroup
)


class CheckoutStates(StatesGroup):

    waiting_discount_code = State()

    waiting_receipt = State()

    waiting_rejection_reason = State()

    waiting_support_message = State()
    waiting_ai_email = State()
    waiting_ai_login_code = State()
