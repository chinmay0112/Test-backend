# check_models.py
import google.generativeai as genai
import os

# 1. PASTE YOUR KEY DIRECTLY BELOW inside the quotes
api_key = "AIzaSyD5UTqOr-brCBHOcgvcGdcgh_d0vKGmgNw"

try:
    genai.configure(api_key=api_key)
    print("Checking for available models...\n")
    
    found_flash = False
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            if "gemini-1.5-flash" in m.name:
                found_flash = True
    
    print("\n------------------------------------------------")
    if found_flash:
        print("✅ SUCCESS: 'gemini-1.5-flash' is available!")
    else:
        print("❌ ERROR: 'gemini-1.5-flash' was NOT found in your list.")
        print("Try using 'gemini-pro' or update your library: pip install -U google-generativeai")

except Exception as e:
    print(f"Error connecting to Google: {e}")