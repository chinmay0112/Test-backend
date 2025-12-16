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
        'gemini-2.0-flash-lite',
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    You are an expert exam setter.
    Generate {count} multiple-choice questions on: "{topic}".
    Difficulty: {difficulty}.
    
    Output a raw JSON array of objects.
    Keys:
    - "question_text": string
    - "option_a": string
    - "option_b": string
    - "option_c": string
    - "option_d": string
    - "correct_option": string (must be "option_a", "option_b", "option_c", or "option_d")
    - "explanation": string
    """
    
    # REMOVED the try/except block so errors will show in the Admin UI
    response = model.generate_content(prompt)
    
    # Check if response was blocked by safety filters
    if not response.parts:
        raise ValueError(f"AI blocked the response. Reason: {response.prompt_feedback}")

    text_data = response.text
    return json.loads(text_data)