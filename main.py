import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from core.config import settings
from core.logging_config import setup_logging
from core.loader import register_routers

from modules.admin.agency_bots import supervise
from modules.force_join.middleware import ForceJoinMiddleware


logger = logging.getLogger("NR_SHOP")


async def main():

    setup_logging(settings.LOG_LEVEL)

    session = AiohttpSession(
        proxy=settings.BOT_PROXY
    )

    from core.button_theme import style_keyboard
    session.middleware(style_keyboard)
    bot = Bot(
        token=settings.BOT_TOKEN.get_secret_value(),
        session=session,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    dp = Dispatcher()

    # فعال سازی عضویت اجباری
    dp.message.outer_middleware(
        ForceJoinMiddleware()
    )

    dp.callback_query.outer_middleware(
        ForceJoinMiddleware()
    )

    # ثبت ماژول ها
    register_routers(dp)

    logger.info("NR SHOP BOT STARTED")

    agencies = asyncio.create_task(supervise(bot))
    try:

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    finally:

        agencies.cancel()
        await asyncio.gather(agencies, return_exceptions=True)
        await bot.session.close()

        logger.info("NR SHOP BOT STOPPED")


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("NR SHOP STOPPED")
