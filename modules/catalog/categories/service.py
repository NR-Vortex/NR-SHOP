from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Category, Product


VALID_SECTIONS = {
    "ai",
    "vpn",
    "telegram",
    "vps",
}


class CategoryAlreadyExistsError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class CategoryHasProductsError(Exception):
    pass


def validate_section(section: str):

    if section not in VALID_SECTIONS:
        raise ValueError("Invalid store section")


# ایجاد دسته بندی
async def create_category(
    session: AsyncSession,
    name: str,
    section: str,
    sort_order: int = 0
):

    name = name.strip()

    if not name:
        raise ValueError("Category name cannot be empty")

    validate_section(section)

    category = Category(
        name=name,
        section=section,
        sort_order=sort_order,
        is_active=True
    )

    session.add(category)

    try:

        await session.commit()
        await session.refresh(category)

    except IntegrityError:

        await session.rollback()

        raise CategoryAlreadyExistsError(
            "Category already exists in this section"
        )

    return category


# نمایش دسته بندی ها
async def get_categories(
    session: AsyncSession,
    active_only: bool = False,
    section: str | None = None
):

    query = select(Category)

    if active_only:

        query = query.where(
            Category.is_active.is_(True)
        )

    if section is not None:

        validate_section(section)

        query = query.where(
            Category.section == section
        )

    query = query.order_by(
        Category.sort_order.asc(),
        Category.id.asc()
    )

    result = await session.execute(query)

    return result.scalars().all()


# دریافت یک دسته بندی
async def get_category(
    session: AsyncSession,
    category_id: int
):

    result = await session.execute(
        select(Category).where(
            Category.id == category_id
        )
    )

    category = result.scalar_one_or_none()

    if not category:
        raise CategoryNotFoundError()

    return category


# ویرایش دسته بندی
async def update_category(
    session: AsyncSession,
    category_id: int,
    name: str | None = None,
    section: str | None = None,
    is_active: bool | None = None,
    sort_order: int | None = None
):

    category = await get_category(
        session,
        category_id
    )

    if name is not None:

        name = name.strip()

        if not name:
            raise ValueError("Category name cannot be empty")

        category.name = name

    if section is not None:

        validate_section(section)

        category.section = section

    if is_active is not None:
        category.is_active = is_active

    if sort_order is not None:
        category.sort_order = sort_order

    try:

        await session.commit()
        await session.refresh(category)

    except IntegrityError:

        await session.rollback()

        raise CategoryAlreadyExistsError(
            "Category already exists in this section"
        )

    return category


# حذف دسته بندی
async def delete_category(
    session: AsyncSession,
    category_id: int
):

    category = await get_category(
        session,
        category_id
    )

    result = await session.execute(
        select(func.count(Product.id)).where(
            Product.category_id == category_id
        )
    )

    product_count = result.scalar_one()

    if product_count > 0:

        raise CategoryHasProductsError(
            "Category contains products"
        )

    await session.delete(category)

    try:

        await session.commit()

    except IntegrityError:

        await session.rollback()

        raise CategoryHasProductsError(
            "Category cannot be deleted"
        )

    return True