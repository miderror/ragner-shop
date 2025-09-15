from aiogram.fsm.state import State, StatesGroup


class OrderState(StatesGroup):
    quantity = State()
    pubg_id = State()
    username = State()
    user_id = State()


class TopUpState(StatesGroup):
    amount = State()
    ruble_amount = State()
