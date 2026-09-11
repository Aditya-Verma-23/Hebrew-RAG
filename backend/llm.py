"""
llm.py
------
LLM integration using Groq API (or any OpenAI-compatible endpoint).
Uses standard OpenAI completion endpoints and streaming format.
"""

import os
import json
import requests
from typing import List, Dict, Any, Generator
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
LLM_API_KEY = os.getenv("GROQ_API_KEY", os.getenv("LLM_API_KEY", ""))

HEBREW_SYSTEM_PROMPT = """אתה עוזר מחקרי מומחה לספרות עברית. תפקידך הוא לענות על שאלות בעברית בצורה מדויקת ומפורטת, בהתבסס אך ורק על הקטעים מהטקסט שסופקו לך.

הנחיות:
1. ענה תמיד בעברית, אלא אם כן המשתמש שאל בשפה אחרת.
2. הסתמך רק על המידע בקטעי הטקסט המצורפים.
3. אם המידע אינו מופיע בקטעים, ציין זאת בבירור: "המידע לא נמצא בטקסט הנתון."
4. ציין את מקור המידע (שם הפרק) בתשובתך.
5. כתוב בצורה בהירה ומסודרת.
6. אל תמציא מידע שאינו מופיע בטקסט."""


def _format_context(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        chapter_title = meta.get("chapter_title", f"קטע {i}")
        book_title = meta.get("book_title", "")
        
        header = f"[מקור {i}: {chapter_title}"
        if book_title:
            header += f" | {book_title}"
        header += "]"
        
        context_parts.append(f"{header}\n{chunk['text']}")
    
    return "\n\n---\n\n".join(context_parts)


def generate_answer(
    query: str,
    chunks: List[Dict[str, Any]],
    model: str = LLM_MODEL,
    temperature: float = 0.1,
    max_tokens: int = 1024,
    stream: bool = False,
) -> str:
    """Generate a Hebrew answer using the REST API."""
    context = _format_context(chunks)
    
    user_message = f"""להלן קטעים רלוונטיים מהטקסט:

{context}

---

שאלה: {query}

אנא ענה על השאלה בהתבסס על הקטעים שסופקו."""
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": HEBREW_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
            stream=stream,
        )
        response.raise_for_status()
        
        if stream:
            return _stream_response(response)
        else:
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    except requests.exceptions.ConnectionError:
        return "שגיאה: לא ניתן להתחבר לשרת ה-LLM."
    except requests.exceptions.Timeout:
        return "שגיאה: פסק הזמן של הבקשה. נסה שוב עם שאלה קצרה יותר."
    except Exception as e:
        return f"שגיאה בהפקת תשובה: {str(e)}"


def _stream_response(response) -> Generator[str, None, None]:
    """Stream response tokens from OpenAI/Groq SSE format."""
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8', errors='replace')
            if line_str.startswith("data: "):
                data_str = line_str[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    if "choices" in data and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                except json.JSONDecodeError:
                    continue


def generate_answer_streaming(
    query: str,
    chunks: List[Dict[str, Any]],
    model: str = LLM_MODEL,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> Generator[str, None, None]:
    """Generate a streaming Hebrew answer."""
    context = _format_context(chunks)
    
    user_message = f"""להלן קטעים רלוונטיים מהטקסט:

{context}

---

שאלה: {query}

אנא ענה על השאלה בהתבסס על הקטעים שסופקו."""
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": HEBREW_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        with requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=180,
            stream=True,
        ) as response:
            if not response.ok:
                yield f"שגיאה: {response.status_code} - {response.text}"
                return
                
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8', errors='replace')
                    if line_str.startswith("data: "):
                        data_str = line_str[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue
    
    except requests.exceptions.ConnectionError:
        yield "שגיאה: לא ניתן להתחבר לשרת ה-LLM."
    except Exception as e:
        yield f"שגיאה: {str(e)}"


def check_ollama_status() -> Dict[str, Any]:
    """Check API readiness (renamed for compat)."""
    return {
        "running": bool(LLM_API_KEY),
        "model": LLM_MODEL,
        "model_available": True,
        "available_models": [LLM_MODEL],
    }
