from .data import PRODUCTS, Product


def get_products(category: str) -> list[Product]:
    return [
        product
        for product in PRODUCTS
        if product.category == category and product.enabled
    ]


def get_product(product_id: str) -> Product | None:
    for product in PRODUCTS:
        if product.id == product_id:
            return product
    return None


def get_product_count(category: str) -> int:
    return len(get_products(category))


def is_product_available(product_id: str) -> bool:
    product = get_product(product_id)
    return bool(product and product.enabled and product.stock > 0)
