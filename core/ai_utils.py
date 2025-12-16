# core/ai_utils.py
import google.generativeai as genai
import os
import json

# verify the key exists
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from environment variables!")

genai.configure(api_key=api_key)

def generate_questions_from_ai(topic, count, difficulty):
    model = genai.GenerativeModel(
        'gemini-flash-latest',
        generation_config={"response_mime_type": "application/json"}
    )
    
    # IMPROVED PROMPT: Explicitly asking to escape quotes
    prompt = f"""
    You are an expert exam setter.
    Generate {count} multiple-choice questions on: "{topic}".
    Difficulty: {difficulty}.
    
    IMPORTANT JSON RULES:
    1. Output a VALID JSON array of objects.
    2. Do NOT use markdown formatting (no ```json ... ```).
    3. If a question contains quotes (e.g., "quote"), escape them properly (e.g., \\"quote\\").
    4. Ensure all keys and string values are enclosed in double quotes.

    Keys for each object:
    - "question_text": string
    - "option_a": string
    - "option_b": string
    - "option_c": string
    - "option_d": string
    - "correct_option": string (must be exactly "option_a", "option_b", "option_c", or "option_d")
    - "explanation": string
    """
    
    response = model.generate_content(prompt)
    
    if not response.parts:
        raise ValueError("AI blocked the response due to safety filters.")

    text_data = response.text.strip()

    # SAFETY: Clean up markdown just in case the model ignores instructions
    if text_data.startswith("```json"):
        text_data = text_data.replace("```json", "").replace("```", "")
    
    try:
        return json.loads(text_data)
    except json.JSONDecodeError as e:
        # DEBUGGING: Print the bad text so you can see it in your terminal
        print("\n❌ JSON DECODE ERROR! The AI returned this raw text:")
        print(text_data)
        print("----------------------------------------------------\n")
        raise ValueError(f"AI returned invalid JSON: {str(e)}. Check server console for raw output.")