import os

class PromptLoader:
    @staticmethod
    def load_prompt(prompt_name: str, **kwargs) -> str:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_path, "prompts", f"{prompt_name}.md")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"A keresett prompt fájl nem található: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if kwargs:
            content = content.format(**kwargs)
        return content