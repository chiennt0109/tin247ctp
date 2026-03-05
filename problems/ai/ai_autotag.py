# path: problems/ai/ai_autotag.py
import openai

def ai_suggest_metadata(statement: str):
    """
    G?i OpenAI d? g?i ý code, tags, difficulty.
    B?n có th? thay b?ng LLM n?i b? n?u mu?n.
    """
    prompt = f"""
    Hãy phân tích d? bài sau và tr? v? JSON g?m 3 tru?ng:
    {{
      "code": "Mã ng?n g?i ý (VD: SUMARR01)",
      "difficulty": "Easy/Medium/Hard",
      "tags": ["nh?ng ch? d? chính"]
    }}
    Ð? bài:
    {statement}
    """
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        import json
        content = completion.choices[0].message["content"]
        return json.loads(content)
    except Exception:
        return {"code": "AUTO001", "difficulty": "Medium", "tags": ["General"]}
