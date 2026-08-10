import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from langfuse import Langfuse
from backend.config import settings
from backend.prompts.registry import FALLBACK_PROMPTS

def main():
    print("Initializing Langfuse client...")
    langfuse = Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_BASE_URL
    )
    
    for prompt_name, prompt_text in FALLBACK_PROMPTS.items():
        print(f"Pushing {prompt_name} to Langfuse...")
        langfuse.create_prompt(
            name=prompt_name,
            prompt=prompt_text,
            labels=["production"],
            type="text"
        )
        print(f"Successfully pushed {prompt_name}.")
        
    print("All prompts pushed to Langfuse successfully.")

if __name__ == "__main__":
    main()
