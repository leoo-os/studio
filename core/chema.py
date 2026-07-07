from typing import List, Optional
from pydantic import BaseModel, Field

class MemoryItem(BaseModel):
    memory_order: int
    memory_title: str
    sight: Optional[str] = ""
    sound: Optional[str] = ""
    smell: Optional[str] = ""
    touch: Optional[str] = ""
    taste: Optional[str] = ""
    weather: Optional[str] = ""
    tiny_detail: Optional[str] = ""

class ProductSchema(BaseModel):
    sku: str
    collection: str
    size: str
    function: str
    title: str
    subtitle: Optional[str] = ""
    finish: str
    primary_color: str
    secondary_color: Optional[str] = ""
    dimensions: Optional[str] = ""
    character: Optional[str] = ""
    html_description: str
    seo_title: str
    seo_description: str
    tags: List[str] = Field(default_factory=list)
    image_filename: str
    image_public_url: str
    image_alt: Optional[str] = ""
    memories: List[MemoryItem] = Field(default_factory=list)
    price: str
    inventory_qty: int
    material: str = "Ceramic"
    variant_name: Optional[str] = ""