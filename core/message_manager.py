from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message


@dataclass
class MessageBatch:
    chat_id: int
    visible: set[int] = field(default_factory=set)
    navigated: bool = False
    active: bool = True
    replacement_requested: bool = False


_current: ContextVar[MessageBatch | None] = ContextVar("navigation_batch", default=None)


class NavigationMessages:
    """Retire bot interface messages after the next page has been shown."""

    def __init__(self):
        self.pages: OrderedDict[tuple[int, int], set[int]] = OrderedDict()

    async def handle(self, handler, event, data):
        callback = isinstance(event, CallbackQuery)
        message = event.message if callback else event
        if not isinstance(message, Message) or message.chat.type != ChatType.PRIVATE:
            return await handler(event, data)

        bot = data["bot"]
        key = (bot.id, message.chat.id)
        batch = MessageBatch(message.chat.id)
        context = _current.set(batch)
        try:
            result = await handler(event, data)
        finally:
            batch.active = False
            _current.reset(context)

        if not batch.visible:
            return result

        previous = self.pages.pop(key, set())
        command = (message.text or "").split(maxsplit=1)
        initial = not callback and bool(command) and command[0].split("@", 1)[0] in {"/start", "/admin"}
        if initial or batch.replacement_requested or (callback and batch.navigated):
            # A surviving keyboard from before a bot restart can also lead to a new page.
            navigation = (event.data or "") if callback else ""
            if navigation.startswith(("shop:", "ai:", "vpn:", "panel:", "rs:plans:", "rs:mine:", "rs:manage", "admin:section:", "admin:hub:", "force_join:")):
                previous.add(message.message_id)
            for message_id in previous - batch.visible:
                try:
                    await bot.delete_message(batch.chat_id, message_id)
                except TelegramAPIError:
                    pass
            previous = set()

        self.pages[key] = set(sorted(previous | batch.visible)[-40:])
        if len(self.pages) > 4096:
            self.pages.popitem(last=False)
        return result

    async def capture(self, make_request, bot, method):
        result = await make_request(bot, method)
        batch = _current.get()
        if not batch or not batch.active or getattr(method, "chat_id", None) != batch.chat_id:
            return result
        name = method.__api_method__
        if name in {"sendMessage", "sendPhoto", "sendDocument", "sendVideo", "sendAnimation", "editMessageText", "editMessageCaption"}:
            if isinstance(result, Message):
                batch.visible.add(result.message_id)
                batch.navigated = True
        return result


def register_navigation(dispatcher, session):
    messages = NavigationMessages()
    session.middleware(messages.capture)
    dispatcher.message.outer_middleware(messages.handle)
    dispatcher.callback_query.outer_middleware(messages.handle)


_last_bot_messages: dict[tuple[int, int], int] = {}


async def send_replacing_message(bot: Bot, chat_id: int, text: str, **kwargs) -> Message:
    batch = _current.get()
    if batch and batch.active and batch.chat_id == chat_id:
        batch.replacement_requested = True
        return await bot.send_message(chat_id, text, **kwargs)

    key = (bot.id, chat_id)
    previous = _last_bot_messages.get(key)
    message = await bot.send_message(chat_id, text, **kwargs)
    _last_bot_messages[key] = message.message_id
    if previous and previous != message.message_id:
        try:
            await bot.delete_message(chat_id, previous)
        except TelegramAPIError:
            pass
    return message
