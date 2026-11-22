import asyncio

from sqlalchemy import select

from database.models import Category
from database.session import async_session


INITIAL_CATEGORIES = [
    ("🟢 chatgpt", "ai"),
    ("💎 gemini", "ai"),
    ("⚫ super grok", "ai"),
    ("◈ cursor", "ai"),
    ("V2Ray", "vpn"),
    ("WireGuard", "vpn"),
    ("IP ثابت", "vpn"),
    ("Telegram Premium", "telegram"),
    ("خدمات تلگرام", "telegram"),
    ("VPS ایران", "vps"),
    ("VPS خارج", "vps"),
]


async def main():
    async with async_session() as session:
        for index, (name, section) in enumerate(INITIAL_CATEGORIES, start=1):
            result = await session.execute(
                select(Category).where(
                    Category.name == name,
                    Category.section == section,
                )
            )
            if result.scalar_one_or_none() is not None:
                continue

            session.add(Category(
                name=name,
                section=section,
                sort_order=index,
                is_active=True,
            ))

        await session.commit()
        print("CATEGORIES SEEDED SUCCESSFULLY")


if __name__ == "__main__":
    asyncio.run(main())
