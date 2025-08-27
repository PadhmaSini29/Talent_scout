# app/helpers.py
from __future__ import annotations
import json, re, os
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # Reads .env -> GROQ_API_KEY

# Recommended production model from Groq supported models page
MODEL_ID = "llama-3.3-70b-versatile"  # fast & solid default on Groq :contentReference[oaicite:4]{index=4}

def get_client() -> Groq:
    # The Groq client reads GROQ_API_KEY env var by default; also accepts api_key=...
    # Docs show basic usage via Groq() and chat.completions.create(...). :contentReference[oaicite:5]{index=5}
    return Groq()

# ------------- Validation helpers -------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[+\d][\d\s().-]{6,}$")

def clean_list(s: str) -> List[str]:
    # split by comma/semicolon/newline
    parts = re.split(r"[,\n;]+", s)
    return [p.strip() for p in parts if p.strip()]

def validate_email(s: str) -> bool:
    return bool(EMAIL_RE.match(s.strip()))

def validate_phone(s: str) -> bool:
    return bool(PHONE_RE.match(s.strip()))

# ------------- Candidate struct -------------
@dataclass
class Candidate:
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    years_experience: Optional[float] = None
    desired_positions: List[str] = field(default_factory=list)
    location: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)

    def as_row(self) -> Dict:
        return {
            "full_name": self.full_name or "",
            "email": self.email or "",
            "phone": self.phone or "",
            "years_experience": self.years_experience if self.years_experience is not None else "",
            "desired_positions": ", ".join(self.desired_positions),
            "location": self.location or "",
            "tech_stack": ", ".join(self.tech_stack),
        }

# ------------- LLM Calls -------------
def llm_chat(messages: List[Dict], stream: bool = True):
    """
    Generic streaming chat call.
    """
    client = get_client()
    return client.chat.completions.create(
        model=MODEL_ID,
        messages=messages,
        stream=stream,  # Streaming supported per docs. :contentReference[oaicite:6]{index=6}
        temperature=0.3,
        max_completion_tokens=800,
    )

def extract_candidate_json(messages: List[Dict]) -> Candidate:
    """
    Ask model to output a strict JSON object containing the candidate fields it has
    seen so far in the conversation. Use JSON Object Mode so we always parse JSON.
    """
    client = get_client()
    resp = client.chat.completions.create(
        model=MODEL_ID,
        messages=messages + [
            {
                "role": "system",
                "content": (
                    "Extract candidate info seen so far. "
                    "Return a JSON object with keys: full_name, email, phone, years_experience, "
                    "desired_positions (array of strings), location, tech_stack (array of strings). "
                    "If a field is unknown, set it to null or an empty array. Return JSON only."
                ),
            }
        ],
        # JSON Object Mode: guarantees valid JSON syntax (not full schema). :contentReference[oaicite:7]{index=7}
        response_format={"type": "json_object"},
        stream=False,
        temperature=0,
        max_completion_tokens=400,
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    cand = Candidate()
    cand.full_name = (data.get("full_name") or None)
    cand.email = (data.get("email") or None)
    cand.phone = (data.get("phone") or None)
    # years_experience: coerce number if present
    ye = data.get("years_experience")
    try:
        cand.years_experience = float(ye) if ye not in (None, "", []) else None
    except Exception:
        cand.years_experience = None
    # arrays
    cand.desired_positions = [s for s in (data.get("desired_positions") or []) if isinstance(s, str)]
    cand.location = (data.get("location") or None)
    cand.tech_stack = [s for s in (data.get("tech_stack") or []) if isinstance(s, str)]
    return cand

def generate_tech_questions(techs: List[str]) -> Dict[str, List[str]]:
    """
    Ask model to write 3–5 targeted questions per technology.
    Return a dict {tech: [q1, q2, ...]}.
    """
    if not techs: return {}
    client = get_client()
    prompt = (
        "Based on the candidate's declared tech stack, generate 3-5 interview questions per item. "
        "Questions should be practical and progressively challenging. "
        "Return strict JSON: { 'TECH': ['Q1','Q2',...] } with every tech provided."
    )
    # Non-streaming + JSON Object mode to parse easily.
    resp = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": "You are a senior technical interviewer."},
            {"role": "user", "content": f"Tech stack: {', '.join(techs)}\n{prompt}"},
        ],
        response_format={"type": "json_object"},
        stream=False,
        temperature=0.2,
        max_completion_tokens=800,
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
        # Ensure list of strings
        fixed = {k: [str(q) for q in v][:5] for k, v in data.items() if isinstance(v, list)}
        return fixed
    except Exception:
        # Fallback shape
        return {t: [f"Describe a project where you used {t}.",
                    f"What are common pitfalls when working with {t}?",
                    f"How would you debug a production issue related to {t}?"] for t in techs}
