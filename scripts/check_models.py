import os
import sys

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai is not installed.")
    sys.exit(1)

# Configure API Key
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    API_KEY = input("Enter your Gemini API Key to test: ").strip()

if not API_KEY:
    print("API Key is required.")
    sys.exit(1)

genai.configure(api_key=API_KEY)

print(f"Testing API Key: {API_KEY[:6]}...{API_KEY[-6:]}")
print("Fetching available models...")

try:
    models = genai.list_models()
    count = 0
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f" - {m.name}")
            count += 1
    
    if count == 0:
        print("No models support generateContent for this key.")
    else:
        print(f"\nSUCCESS! Found {count} available models.")
except Exception as e:
    print("\n--- ERROR ---")
    print(e)
    print("-------------\n")
    print("If you see an 'API key not valid' or similar error, it means the key is invalid or has been deactivated/entered incorrectly.")
