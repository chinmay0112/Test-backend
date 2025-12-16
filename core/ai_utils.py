# core/ai_utils.py
import google.generativeai as genai
import os
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_questions_from_ai(topic, count, difficulty):
    # Use the model configuration to FORCE JSON
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = f"""
    You are an expert exam setter for competitive exams (SSC/Banking).
    Generate {count} multiple-choice questions on the topic: "{topic}".
    Difficulty Level: {difficulty}.
    
    Output a raw JSON array of objects.
    Each object must have these exact keys:
    - "question_text": string
    - "option_a": string
    - "option_b": string
    - "option_c": string
    - "option_d": string
    - "correct_option": string (Must be exactly "option_a, "option_b", "option_c", or "option_d")
    - "explanation": string
    """
    
    try:
        response = model.generate_content(prompt)
        
        # Since we used response_mime_type="application/json", 
        # we usually don't need to strip markdown, but it's safe to keep the check just in case.
        text_data = response.text
        questions_data = json.loads(text_data)
        
        return questions_data
        
    except Exception as e:
        print(f"AI Generation Error: {e}")
        return []