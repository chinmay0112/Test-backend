# core/ai_utils.py
import google.generativeai as genai
import os
import json

# Configure the API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_questions_from_ai(topic, count, difficulty):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # The Prompt Engineering (Crucial for getting valid JSON)
    prompt = f"""
    You are an expert exam setter for competitive exams (SSC/Banking).
    Generate {count} multiple-choice questions on the topic: "{topic}".
    Difficulty Level: {difficulty}.
    
    Output strictly as a JSON array of objects. Do not include markdown formatting (```json).
    Each object must have these keys:
    - "question_text": The question string
    - "option_a": Option A
    - "option_b": Option B
    - "option_c": Option C
    - "option_d": Option D
    - "correct_option": A single lowercase letter ('a', 'b', 'c', or 'd')
    - "explanation": A detailed explanation of the answer (2-3 sentences)
    
    Ensure the questions are factual and high quality.
    """
    
    try:
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        # Cleanup: Sometimes AI adds markdown ```json ... ``` wrapper
        if text_response.startswith("```"):
            text_response = text_response.replace("```json", "").replace("```", "")
            
        questions_data = json.loads(text_response)
        return questions_data
        
    except Exception as e:
        print(f"AI Generation Error: {e}")
        return []