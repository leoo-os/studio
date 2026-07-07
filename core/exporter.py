import pandas as pd
from core.schema import ProductSchema

class ShopifyExporter:
    TEMPLATE_COLUMNS = [
        "Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type", "Tags", "Published",
        "Option1 Name", "Option1 Value", "Option1 Linked To", "Option2 Name", "Option2 Value", "Option2 Linked To",
        "Option3 Name", "Option3 Value", "Option3 Linked To", "Variant SKU", "Variant Grams", "Variant Inventory Tracker",
        "Variant Inventory Qty", "Variant Inventory Policy", "Variant Fulfillment Service", "Variant Price",
        "Variant Compare At Price", "Variant Requires Shipping", "Variant Taxable", "Unit Price Total Measure",
        "Unit Price Total Measure Unit", "Unit Price Base Measure", "Unit Price Base Measure Unit", "Variant Barcode",
        "Image Src", "Image Position", "Image Alt Text", "Gift Card", "SEO Title", "SEO Description",
        "Collection (product.metafields.custom.collection)", "Dimensions (product.metafields.custom.dimensions)",
        "Finish (product.metafields.custom.finish)", "Function (product.metafields.custom.function)",
        "Material (product.metafields.custom.material)", "Pattern (product.metafields.custom.pattern)",
        "Primary Color (product.metafields.custom.primary_color)", "Secondary Color (product.metafields.custom.secondary_color)",
        "Variant (product.metafields.custom.variant)", "Character (product.metafields.leoo.character)",
        "Status"
    ]

    @classmethod
    def generate_csv_buffer(cls, product: ProductSchema) -> str:
        product_row = {col: "" for col in cls.TEMPLATE_COLUMNS}
        
        handle = product.title.lower().replace(' ', '-').replace('|', '').replace('–', '-').replace('--', '-')
        while '--' in handle:
            handle = handle.replace('--', '-')
        handle = handle.strip('-')

        product_row["Handle"] = handle
        product_row["Title"] = product.title
        product_row["Body (HTML)"] = product.html_description
        product_row["Vendor"] = "Leoo"
        product_row["Type"] = "Object"
        product_row["Tags"] = ", ".join(product.tags)
        product_row["Published"] = "true"
        product_row["Status"] = "active"
        
        product_row["Variant SKU"] = product.sku
        product_row["Variant Inventory Tracker"] = "shopify"
        product_row["Variant Inventory Qty"] = product.inventory_qty
        product_row["Variant Inventory Policy"] = "deny"
        product_row["Variant Fulfillment Service"] = "manual"
        product_row["Variant Price"] = product.price
        product_row["Variant Requires Shipping"] = "true"
        product_row["Variant Taxable"] = "true"
        product_row["Gift Card"] = "false"
        
        product_row["SEO Title"] = product.seo_title
        product_row["SEO Description"] = product.seo_description
        
        product_row["Collection (product.metafields.custom.collection)"] = product.collection
        product_row["Dimensions (product.metafields.custom.dimensions)"] = product.dimensions
        product_row["Finish (product.metafields.custom.finish)"] = product.finish
        product_row["Function (product.metafields.custom.function)"] = product.function
        product_row["Material (product.metafields.custom.material)"] = product.material
        product_row["Pattern (product.metafields.custom.pattern)"] = ""
        product_row["Primary Color (product.metafields.custom.primary_color)"] = product.primary_color
        product_row["Secondary Color (product.metafields.custom.secondary_color)"] = product.secondary_color
        product_row["Variant (product.metafields.custom.variant)"] = product.variant_name
        product_row["Character (product.metafields.leoo.character)"] = product.character

        product_row["Image Src"] = product.image_public_url
        product_row["Image Position"] = 1
        product_row["Image Alt Text"] = product.image_alt

        df = pd.DataFrame([product_row], columns=cls.TEMPLATE_COLUMNS)
        return df.to_csv(index=False, encoding="utf-8-sig")