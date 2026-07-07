import json
from openai import OpenAI
from core.prompt_loader import PromptLoader

class AIEngine:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def analyze_and_generate(self, base64_image: str, sku: str, collection: str, function: str, variant: str) -> dict:
        vision_prompt = PromptLoader.load_prompt("product_generator")
        schema_instruction = 'Return JSON with keys: "Size", "Finish", "Primary Colour", "Secondary Colour", "Dimensions", "Image ALT"'
        
        response = self.client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": vision_prompt + "\n" + schema_instruction},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"SKU context: {sku}."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        )
        visual_data = json.loads(response.choices[0].message.content)

        size = visual_data.get("Size", "Standard")
        title = f"Dodó – {collection} | {size}"

        memory_prompt = PromptLoader.load_prompt(
            "memory_profile", 
            size=size, 
            primary_color=visual_data.get("Primary Colour", ""),
            secondary_color=visual_data.get("Secondary Colour", ""),
            finish=visual_data.get("Finish", "Glossy")
        )
        m_instruction = 'Return a JSON array named "memories" containing objects with keys: "memory_order", "memory_title", "sight", "sound", "smell", "touch", "taste", "weather", "tiny_detail"'
        
        m_response = self.client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": memory_prompt + "\n" + m_instruction}]
        )
        memory_data = json.loads(m_response.choices[0].message.content)

        html_prompt = PromptLoader.load_prompt("html_description")
        html_response = self.client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": html_prompt + '\nReturn JSON with key "html_description"'},
                {"role": "user", "content": f"Title: {title}. Visuals: {str(visual_data)}. Memories context: {str(memory_data)}"}
            ]
        )
        html_data = json.loads(html_response.choices[0].message.content)

        seo_prompt = PromptLoader.load_prompt("seo", title=title)
        seo_response = self.client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": seo_prompt + '\nReturn JSON with keys "seo_title", "seo_description", "tags"'}]
        )
        seo_data = json.loads(seo_response.choices[0].message.content)

        return {
            "visual": visual_data,
            "memories": memory_data.get("memories", []),
            "html": html_data,
            "seo": seo_data,
            "title": title
        }