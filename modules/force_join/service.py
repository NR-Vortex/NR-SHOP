import logging

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError

from .config import required_channels


logger = logging.getLogger(__name__)


class MembershipCheckError(Exception):
    pass


async def get_missing_channels(
    bot: Bot,
    user_id: int
):

    missing_channels = []

    active_channels = [
        channel
        for channel in required_channels()
        if channel.enabled
    ]

    for channel in active_channels:

        try:

            member = await bot.get_chat_member(
                chat_id=channel.chat_id,
                user_id=user_id
            )

            is_member = member.status in {
                ChatMemberStatus.CREATOR,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.MEMBER
            }

            if member.status == ChatMemberStatus.RESTRICTED:
                is_member = member.is_member

            if not is_member:
                missing_channels.append(channel)

        except TelegramAPIError as error:

            logger.exception(
                "Channel membership check failed: %s",
                channel.title
            )

            raise MembershipCheckError(
                "Unable to verify channel membership"
            ) from error

    return missing_channels