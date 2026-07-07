import json
import os
from supabase import create_client, Client
from core.schema import ProductSchema

class DatabaseManager:
    def __init__(self):
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_path, "config", "config.json")
        
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        self.url: str = config["supabase"]["url"]
        self.key: str = config["supabase"]["key"]
        self.client: Client = create_client(self.url, self.key)

    def save_product_flow(self, product: ProductSchema, csv_filename: str) -> str:
        prod_data = {
            "sku": product.sku,
            "collection": product.collection,
            "size": product.size,
            "function": product.function,
            "title": product.title,
            "subtitle": product.subtitle,
            "character": product.character,
            "html_description": product.html_description,
            "seo_title": product.seo_title,
            "seo_description": product.seo_description
        }
        prod_res = self.client.table("products").insert(prod_data).execute()
        product_id = prod_res.data[0]["id"]

        if product.memories:
            memory_batch = []
            for m in product.memories:
                memory_batch.append({
                    "product_id": product_id,
                    "memory_order": m.memory_order,
                    "memory_title": m.memory_title,
                    "sight": m.sight,
                    "sound": m.sound,
                    "smell": m.smell,
                    "touch": m.touch,
                    "taste": m.taste,
                    "weather": m.weather,
                    "tiny_detail": m.tiny_detail
                })
            self.client.table("memory_profiles").insert(memory_batch).execute()

        img_data = {
            "product_id": product_id,
            "filename": product.image_filename,
            "public_url": product.image_public_url,
            "alt_text": product.image_alt
        }
        self.client.table("images").insert(img_data).execute()

        export_data = {
            "product_id": product_id,
            "csv_filename": csv_filename
        }
        self.client.table("exports").insert(export_data).execute()
        
        return product_id