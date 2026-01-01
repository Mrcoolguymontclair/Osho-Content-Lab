import os
import sys

# Force unbuffered output so you see prints immediately
sys.stdout.reconfigure(line_buffering=True)

print("--- DIAGNOSTIC START ---")

# 1. Check Library
try:
    from google import genai
    print("✅ Library 'google-genai' is installed.")
except ImportError:
    print("❌ ERROR: Library 'google-genai' is NOT installed.")
    print("Run this in Shell: pip install google-genai")
    sys.exit(1)

# 2. Check API Key
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY is missing from Secrets.")
    print("Go to Tools > Secrets on the left and add GEMINI_API_KEY.")
    sys.exit(1)
else:
    print(f"✅ GEMINI_API_KEY found (starts with: {api_key[:4]}...)")

# 3. Test Connection
print("Testing connection to Gemini 1.5 Flash...")
try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents='Say "Hello Replit!" if you can hear me.'
    )
    print(f"\n🎉 SUCCESS! Gemini responded:\n{response.text}")
except Exception as e:
    print(f"\n❌ CONNECTION ERROR: {str(e)}")
    print("Double check that your API Key is valid and has access to Gemini 1.5 Flash.")

print("--- DIAGNOSTIC END ---")