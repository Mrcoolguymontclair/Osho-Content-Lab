import os
import google.generativeai as genai

print("1. Checking API Key...")
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ ERROR: GEMINI_API_KEY is missing from Secrets!")
    exit(1)
print("✅ API Key found.")

print("2. Configuring Gemini...")
try:
    genai.configure(api_key=api_key)
    print("✅ Configuration successful.")
except Exception as e:
    print(f"❌ Configuration Failed: {e}")
    exit(1)

print("3. Testing Generation...")
try:
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content("Say hello!")
    print(f"✅ SUCCESS! Gemini says: {response.text}")
except Exception as e:
    print(f"❌ Generation Failed: {e}")
    print("\nSUGGESTION: You might need to check if your code uses genai.Client (new) or genai.GenerativeModel (standard).")

