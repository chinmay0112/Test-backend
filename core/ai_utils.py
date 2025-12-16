# core/ai_utils.py
import google.generativeai as genai
import os
import json
from google.generativeai.types import HarmCategory, HarmBlockThreshold
# verify the key exists
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from environment variables!")

genai.configure(api_key=api_key)

def generate_questions_from_ai(topic, count, difficulty):
    # Use the stable model alias
    model = genai.GenerativeModel(
        'gemini-flash-latest',
        generation_config={"response_mime_type": "application/json"}
    )
    
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }


    prompt = f"""
    You are an expert exam setter.
    Generate {count} multiple-choice questions on: "{topic}".
    Difficulty: {difficulty}.
    
    IMPORTANT RULES:
    1. Output a VALID JSON array.
    2. Escape any internal quotes in strings (e.g. \\"quoted text\\").
    3. correct_option MUST be exactly one of: "option_a", "option_b", "option_c", or "option_d".

    Keys for each object:
    - "question_text": string
    - "option_a": string
    - "option_b": string
    - "option_c": string
    - "option_d": string
    - "correct_option": string
    - "explanation": string
    """
    
    try:
        response = model.generate_content(prompt)
        
        if not response.parts:
            raise ValueError("AI blocked the response (Safety Filters).")

        text_data = response.text.strip()
        
        # Cleanup markdown if present
        if text_data.startswith("```"):
            text_data = text_data.replace("```json", "").replace("```", "")

        data = json.loads(text_data)
        
        # --- DATA CLEANING FOR DATABASE ---
        cleaned_data = []
        for q in data:
            # 1. Fix correct_option to be single char ('a', 'b', 'c', 'd')
            raw_ans = str(q.get('correct_option', 'a')).lower()
            
            if "option_" in raw_ans:
                clean_ans = raw_ans.replace("option_", "").replace(" ", "") # "option_a" -> "a"
            elif "option" in raw_ans:
                clean_ans = raw_ans.replace("option", "").replace(" ", "") # "option a" -> "a"
            else:
                # If it's just "a" or random text, take the last char
                clean_ans = raw_ans.strip()[-1] if raw_ans else 'a'
            
            # Ensure it is only 1 char
            q['correct_option'] = clean_ans[0] if clean_ans else 'a'
            
            cleaned_data.append(q)
            
        return cleaned_data

    except json.JSONDecodeError as e:
        print(f"\n❌ JSON ERROR. AI Output:\n{text_data}\n")
        raise ValueError(f"AI returned invalid JSON. Check console for details.")
    except Exception as e:
        raise e