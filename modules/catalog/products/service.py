from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Product, Category, ProductGroup


class ProductNotFoundError(Exception):
    pass


class ProductCategoryNotFoundError(Exception):
    pass


class ProductAlreadyExistsError(Exception):
    pass


class ProductGroupNotFoundError(Exception):
    pass


class ProductGroupCategoryMismatchError(Exception):
    pass


async def validate_product_group(
    session: AsyncSession,
    category_id: int,
    group_id: int,
):
    result = await session.execute(
        select(ProductGroup).where(ProductGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if group is None:
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
    name: str,
    price: int,
    description: str | None = None,
    group_id: int | None = None,
    account_type: str = "shared",
):

    name = name.strip()

    if not name:
        raise ValueError("Product name cannot be empty")

    if price < 0:
        raise ValueError("Price cannot be negative")
    if account_type not in {"shared", "dedicated"}:
        raise ValueError("account_type must be shared or dedicated")

    # بررسی وجود دسته بندی
    result = await session.execute(
        select(Category).where(
            Category.id == category_id
        )
    )

    category = result.scalar_one_or_none()

    if not category:
        raise ProductCategoryNotFoundError()

    if group_id is not None:
        await validate_product_group(session, category_id, group_id)

    product = Product(
        category_id=category_id,
        group_id=group_id,
        name=name,
        description=description,
        price=price,
        is_active=True,
        account_type=account_type
    )

    session.add(product)

    try:
        await session.commit()
        await session.refresh(product)

    except IntegrityError:
        await session.rollback()

        raise ProductAlreadyExistsError(
            "Product already exists in this category"
        )

    return product


# ==============================
# GET ALL PRODUCTS
# ==============================

async def get_products(
    session: AsyncSession,
    category_id: int | None = None,
    active_only: bool = False
    ,group_id: int | None = None
    ,account_type: str | None = None
):

    query = select(Product)

    if category_id is not None:

        query = query.where(
            Product.category_id == category_id
        )

    if active_only:

        query = query.where(
            Product.is_active.is_(True)
        )

    if group_id is not None:
        query = query.where(Product.group_id == group_id)

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
    is_active: bool | None = None
    ,group_id: int | None = None
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
        await validate_product_group(session, product.category_id, group_id)
    product.group_id = group_id
    if account_type is not None:
        if account_type not in {"shared", "dedicated"}:
            raise ValueError("account_type must be shared or dedicated")
        product.account_type = account_type

    try:
        await session.commit()
        await session.refresh(product)

    except IntegrityError:
        await session.rollback()

        raise ProductAlreadyExistsError(
            "Product already exists"
        )

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
