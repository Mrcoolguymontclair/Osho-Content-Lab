import os
from google import genai

print("--- MODEL DIAGNOSTIC V2 START ---")

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("❌ GEMINI_API_KEY missing.")
    exit()

try:
    client = genai.Client(api_key=api_key)
    pager = client.models.list()

    print("\n✅ CONNECTED! Printing raw model names:")
    print("-" * 30)

    count = 0
    for model in pager:
        # Just print the name, don't check other attributes
        print(f" • {model.name}")
        count += 1

    print("-" * 30)
    print(f"Total models found: {count}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("--- MODEL DIAGNOSTIC V2 END ---")