import google.generativeai as genai
import yaml
import os

def list_models():
    try:
        # Load keys
        with open("apis/gemini_keys.yaml", "r") as f:
            config = yaml.safe_load(f)
            
        # Try to handle different yaml structures
        keys = config.get("api_keys", [])
        if keys:
            api_key = keys[0]
            genai.configure(api_key=api_key)
            
            print("Available models:")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"- {m.name}")
        else:
             print("No API keys found in apis/gemini_keys.yaml")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_models()
