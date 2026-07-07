from core.schema import ProductSchema

class SchemaValidator:
    @staticmethod
    def validate_product(product: ProductSchema) -> bool:
        if not product.sku or not product.collection or not product.function:
            return False
        if not product.title.startswith("Dodó –"):
            return False
        try:
            float(product.price)
        except ValueError:
            return False
        return True