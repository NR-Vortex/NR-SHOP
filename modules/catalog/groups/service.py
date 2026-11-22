from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    Product,
    Category,
    ProductGroup
)


class ProductNotFoundError(Exception):
    pass


class ProductCategoryNotFoundError(Exception):
    pass


class ProductGroupNotFoundError(Exception):
    pass


class ProductGroupCategoryMismatchError(Exception):
    pass


class ProductAlreadyExistsError(Exception):
    pass


class ProductGroupAlreadyExistsError(Exception):
    pass


class ProductGroupHasProductsError(Exception):
    pass


async def create_product_group(
    session: AsyncSession,
    category_id: int,
    name: str,
    sort_order: int = 0,
):
    name = name.strip()
    if not name:
        raise ValueError("Product group name cannot be empty")

    result = await session.execute(
        select(Category).where(Category.id == category_id)
    )
    if result.scalar_one_or_none() is None:
        raise ProductCategoryNotFoundError()

    group = ProductGroup(
        category_id=category_id,
        name=name,
        sort_order=sort_order,
        is_active=True,
    )
    session.add(group)
    try:
        await session.commit()
        await session.refresh(group)
    except IntegrityError:
        await session.rollback()
        raise ProductGroupAlreadyExistsError(
            "Product group already exists in this category"
        )
    return group


async def get_product_group(session: AsyncSession, group_id: int):
    result = await session.execute(
        select(ProductGroup).where(ProductGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if group is None:
        raise ProductGroupNotFoundError()
    return group


async def get_product_groups(
    session: AsyncSession,
    category_id: int | None = None,
    active_only: bool = False,
):
    query = select(ProductGroup)

    if category_id is not None:
        query = query.where(ProductGroup.category_id == category_id)

    if active_only:
        query = query.where(ProductGroup.is_active.is_(True))

    query = query.order_by(ProductGroup.sort_order.asc(), ProductGroup.id.asc())
    result = await session.execute(query)
    return result.scalars().all()


async def delete_product_group(session: AsyncSession, group_id: int):
    group = await get_product_group(session, group_id)
    result = await session.execute(
        select(Product.id).where(Product.group_id == group_id).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        raise ProductGroupHasProductsError("Product group contains products")

    await session.delete(group)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ProductGroupHasProductsError("Product group cannot be deleted")
    return True


async def validate_product_group(
    session: AsyncSession,
    category_id: int,
    group_id: int
):

    result = await session.execute(
        select(ProductGroup).where(
            ProductGroup.id == group_id
        )
    )

    group = result.scalar_one_or_none()

    if not group:
        raise ProductGroupNotFoundError()

    if group.category_id != category_id:
        raise ProductGroupCategoryMismatchError()

    return group


# ==============================
# CREATE PRODUCT
# ==============================

async def create_product(
    session: AsyncSession,
    category_id: int,
    group_id: int,
    name: str,
    price: int,
    description: str | None = None
):

    name = name.strip()

    if not name:
        raise ValueError("Product name cannot be empty")

    if price < 0:
        raise ValueError("Price cannot be negative")

    result = await session.execute(
        select(Category).where(
            Category.id == category_id
        )
    )

    category = result.scalar_one_or_none()

    if not category:
        raise ProductCategoryNotFoundError()

    await validate_product_group(
        session,
        category_id,
        group_id
    )

    product = Product(
        category_id=category_id,
        group_id=group_id,
        name=name,
        description=description,
        price=price,
        is_active=True
    )

    session.add(product)

    try:

        await session.commit()
        await session.refresh(product)

    except IntegrityError:

        await session.rollback()

        raise ProductAlreadyExistsError()

    return product


# ==============================
# GET PRODUCTS
# ==============================

async def get_products(
    session: AsyncSession,
    category_id: int | None = None,
    active_only: bool = False,
    group_id: int | None = None
):

    query = select(Product)

    if category_id is not None:

        query = query.where(
            Product.category_id == category_id
        )

    if group_id is not None:

        query = query.where(
            Product.group_id == group_id
        )

    if active_only:

        query = query.where(
            Product.is_active.is_(True)
        )

    query = query.order_by(
        Product.id.desc()
    )

    result = await session.execute(query)

    return result.scalars().all()


# ==============================
# GET SINGLE PRODUCT
# ==============================

async def get_product(
    session: AsyncSession,
    product_id: int
):

    result = await session.execute(
        select(Product).where(
            Product.id == product_id
        )
    )

    product = result.scalar_one_or_none()

    if not product:
        raise ProductNotFoundError()

    return product


# ==============================
# UPDATE PRODUCT
# ==============================

async def update_product(
    session: AsyncSession,
    product_id: int,
    name: str | None = None,
    description: str | None = None,
    price: int | None = None,
    is_active: bool | None = None,
    group_id: int | None = None
):

    product = await get_product(
        session,
        product_id
    )

    if name is not None:

        name = name.strip()

        if not name:
            raise ValueError("Product name cannot be empty")

        product.name = name

    if description is not None:
        product.description = description

    if price is not None:

        if price < 0:
            raise ValueError("Price cannot be negative")

        product.price = price

    if is_active is not None:
        product.is_active = is_active

    if group_id is not None:

        await validate_product_group(
            session,
            product.category_id,
            group_id
        )

        product.group_id = group_id

    try:

        await session.commit()
        await session.refresh(product)

    except IntegrityError:

        await session.rollback()

        raise ProductAlreadyExistsError()

    return product


# ==============================
# DELETE PRODUCT
# ==============================

async def delete_product(
    session: AsyncSession,
    product_id: int
):

    product = await get_product(
        session,
        product_id
    )

    await session.delete(product)

    await session.commit()

    return True
