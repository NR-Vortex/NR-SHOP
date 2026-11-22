from dataclasses import dataclass


@dataclass
class Product:
    id: str
    category: str
    title: str
    description: str
    price: int
    stock: int = 0
    enabled: bool = True
    image_url: str | None = None


PRODUCTS: list[Product] = []
