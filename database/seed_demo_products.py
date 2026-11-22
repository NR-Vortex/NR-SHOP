import asyncio

from sqlalchemy import select

from database.session import async_session
from database.models import Category, Product, ProductGroup


DEMO_DATA = {

    "ChatGPT Plus": [
        ("اشتراکی ۴ نفره", 1697000),
        ("اشتراکی ۶ نفره", 1397000),
        ("اشتراکی اقتصادی", 898000),
        ("اختصاصی فوری", 6097000),
    ],

    "ChatGPT Pro": [
        ("اشتراکی Webapp", 3497000),
        ("اختصاصی ۵ نفر", 29788150),
        ("اختصاصی ۲۰ نفر", 45000000),
    ],

    "ChatGPT Go": [
        ("اشتراک اختصاصی", 2450000),
    ],

}


async def main():

    async with async_session() as session:

        # پیدا کردن دسته بندی ChatGPT

        result = await session.execute(
            select(Category).where(
                Category.section == "ai",
                Category.name.ilike("%chatgpt%")
            )
        )

        category = result.scalar_one_or_none()

        if not category:
            print("CHATGPT CATEGORY NOT FOUND!")
            return

        print("CATEGORY:", category.name)

        total_products = 0

        for group_index, (group_name, products) in enumerate(
            DEMO_DATA.items(),
            start=1
        ):

            # پیدا کردن یا ساخت گروه

            result = await session.execute(
                select(ProductGroup).where(
                    ProductGroup.category_id == category.id,
                    ProductGroup.name == group_name
                )
            )

            group = result.scalar_one_or_none()

            if not group:

                group = ProductGroup(
                    category_id=category.id,
                    name=group_name,
                    is_active=True,
                    sort_order=group_index
                )

                session.add(group)
                await session.flush()

                print("GROUP CREATED:", group_name)

            # ثبت محصولات

            for product_name, price in products:

                result = await session.execute(
                    select(Product).where(
                        Product.category_id == category.id,
                        Product.name == product_name
                    )
                )

                product = result.scalar_one_or_none()

                if product:
                    print("PRODUCT EXISTS:", product_name)
                    continue

                product = Product(
                    category_id=category.id,
                    group_id=group.id,
                    name=product_name,
                    description=f"محصول آزمایشی NR SHOP - {product_name}",
                    price=price,
                    is_active=True
                )

                session.add(product)

                total_products += 1

                print("PRODUCT CREATED:", product_name)

        await session.commit()

        print("\n==============================")
        print("NR SHOP DEMO DATA READY!")
        print("NEW PRODUCTS:", total_products)
        print("==============================")


if __name__ == "__main__":
    asyncio.run(main())