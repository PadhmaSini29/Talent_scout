# app/app.py
import streamlit as st
import pandas as pd
from pathlib import Path
import hashlib
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from langdetect import detect, detect_langs, LangDetectException, DetectorFactory

from prompts import SYSTEM_PROMPT, EXIT_KEYWORDS, FIELD_ORDER, FIELD_QUESTIONS
from helpers import (
    llm_chat, extract_candidate_json, generate_tech_questions,
    Candidate, validate_email, validate_phone, clean_list
)

# Make langdetect deterministic
DetectorFactory.seed = 0

# ---------------------------- App / Paths ----------------------------
st.set_page_config(page_title="TalentScout - Hiring Assistant", page_icon="🧭", layout="centered")
analyzer = SentimentIntensityAnalyzer()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH = DATA_DIR / "candidates.csv"

# Language code → nice name (ISO 639-1 for langdetect)
LANG_NAMES = {
    # English + major Indian languages
    "en": "English", "hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "ml": "Malayalam", "kn": "Kannada", "mr": "Marathi", "pa": "Punjabi",
    "gu": "Gujarati", "or": "Odia", "as": "Assamese", "ur": "Urdu",
    # A few common world languages
    "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese",
    "it": "Italian", "ru": "Russian", "ja": "Japanese", "zh-cn": "Chinese (Simplified)"
}

# ---------------------------- Session State ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! I’m TalentScout. I’ll collect a few details and ask tech questions to begin your screening."},
    ]
if "candidate" not in st.session_state:
    st.session_state.candidate = Candidate()
if "ended" not in st.session_state:
    st.session_state.ended = False
if "tech_questions" not in st.session_state:
    st.session_state.tech_questions = {}
if "saved_rows" not in st.session_state:
    st.session_state.saved_rows = 0
if "lang" not in st.session_state:
    st.session_state.lang = "en"  # default English
if "hashed_pii" not in st.session_state:
    st.session_state.hashed_pii = False

# ---------------------------- Sidebar ----------------------------
with st.sidebar:
    st.markdown("### ⚙️ Settings & Privacy")
    save_opt = st.checkbox(
        "Save anonymized candidate data locally (CSV)",
        value=False,
        help=f"Saves to {CSV_PATH}"
    )
    st.session_state.hashed_pii = st.checkbox(
        "Hash email/phone before saving (GDPR-friendly)", value=True,
        help="SHA-256 hashes of email & phone will be stored instead of raw values."
    )

    # Manual language override (helps with Hinglish etc.)
    st.markdown("### 🌐 Language")
    codes = sorted(LANG_NAMES.keys())
    selected = st.selectbox(
        "Auto-detected language (you can override):",
        options=["auto"] + codes,
        format_func=lambda c: "Auto" if c == "auto" else f"{LANG_NAMES.get(c, c)} ({c})",
        index=(["auto"] + codes).index(st.session_state.lang) if st.session_state.lang in codes else 0
    )
    if selected != "auto" and selected != st.session_state.lang:
        st.session_state.lang = selected
        st.session_state.messages.insert(1, {
            "role": "system",
            "content": f"From now on, respond in {LANG_NAMES.get(selected, selected)}. Keep answers concise and friendly."
        })

    st.caption("We only store data locally on your machine. For demos, use anonymized data.")

    # Data management utilities
    colA, colB = st.columns(2)
    with colA:
        if st.button("🔄 Start New Candidate"):
            st.session_state.messages = st.session_state.messages[:1] + [
                {"role": "assistant", "content": "Hi again! Let’s start fresh. I’ll collect your details and then ask a few technical questions."}
            ]
            st.session_state.candidate = Candidate()
            st.session_state.tech_questions = {}
            st.session_state.ended = False
    with colB:
        delete_disabled = not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0
        if st.button("🗑️ Delete last saved row", disabled=delete_disabled):
            try:
                df = pd.read_csv(CSV_PATH)
                if len(df) > 0:
                    df = df.iloc[:-1]
                    df.to_csv(CSV_PATH, index=False, encoding="utf-8")
                    st.success("Last row deleted.")
                else:
                    st.info("CSV is empty.")
            except Exception as e:
                st.error(f"Failed to delete last row: {e}")

    # CSV preview if file exists
    if CSV_PATH.exists():
        try:
            st.markdown("#### 📄 Saved Candidates (Preview)")
            prev = pd.read_csv(CSV_PATH)
            st.dataframe(prev, use_container_width=True, height=200)
        except Exception as e:
            st.caption(f"Preview unavailable: {e}")

# ---------------------------- Helpers ----------------------------
def show_chat():
    for m in st.session_state.messages[1:]:
        with st.chat_message("assistant" if m["role"] == "assistant" else "user"):
            st.write(m["content"])

def next_missing_field(c: Candidate):
    for f in FIELD_ORDER:
        val = getattr(c, f)
        if (f in ("desired_positions", "tech_stack") and not val) or (
            f not in ("desired_positions", "tech_stack") and not val
        ):
            return f
    return None

def append_assistant(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})
    with st.chat_message("assistant"):
        st.write(text)

def end_conversation():
    st.session_state.ended = True
    append_assistant("Thanks! That’s all for now. Our team will review your information and contact you about next steps. 👋")

def hash_if_needed(value: str) -> str:
    """Return SHA-256(hex) if hashing is enabled; otherwise raw value."""
    if not value:
        return value
    if not st.session_state.hashed_pii:
        return value
    h = hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()
    return f"hash:{h[:12]}…"

def save_candidate_row(candidate: Candidate) -> bool:
    """Append the candidate to CSV_PATH safely (with optional hashing)."""
    try:
        row_dict = candidate.as_row()
        row_dict["email"] = hash_if_needed(row_dict["email"])
        row_dict["phone"] = hash_if_needed(row_dict["phone"])
        row = pd.DataFrame([row_dict])

        if CSV_PATH.exists():
            row.to_csv(CSV_PATH, mode="a", header=False, index=False, encoding="utf-8")
        else:
            row.to_csv(CSV_PATH, index=False, encoding="utf-8")
        return True
    except Exception as e:
        st.error(f"Failed to save CSV: {e}")
        return False

# ---------- Robust language detection (ignore short/low-confidence text) ----------
def _clean_alpha_spaces(text: str) -> str:
    return "".join(ch for ch in text if ch.isalpha() or ch.isspace())

def guess_language_code(text: str) -> str | None:
    """
    Robust, language-agnostic detector.

    Returns the top ISO-639-1 code (e.g., 'hi', 'ta', 'ar', 'zh-cn') iff:
      - The text has enough signal:
          • >= 10 alphabetic chars for Latin-script text, OR
          • >= 3 alphabetic chars if it contains any non-Latin letters (e.g., देवनागरी, العربية)
      - The top detected language has probability >= 0.80
      - The top language is not English ('en')
    Otherwise returns None (keep English).
    """
    sanitized = _clean_alpha_spaces(text)
    if not sanitized:
        return None

    # Heuristic: allow shorter threshold for non-Latin scripts
    has_non_latin = any(ord(ch) > 127 and ch.isalpha() for ch in sanitized)
    alpha_count = sum(1 for ch in sanitized if ch.isalpha())
    min_len = 3 if has_non_latin else 10
    if alpha_count < min_len:
        return None

    try:
        candidates = detect_langs(sanitized)  # e.g., [hi:0.92, en:0.06]
        if not candidates:
            return None
        top = max(candidates, key=lambda lp: lp.prob)
        # Accept ANY supported language code from langdetect (not just those in LANG_NAMES)
        if top.lang != "en" and top.prob >= 0.80:
            return top.lang
    except LangDetectException:
        pass

    return None


def detect_and_set_language(user_text: str):
    """
    Robust language detection:
    - Skip very short messages (like 'hi')
    - Only switch if high-confidence, supported, non-English detection
    """
    if st.session_state.lang != "en":  # already set or manually overridden
        return
    code = guess_language_code(user_text)
    if not code:
        return
    st.session_state.lang = code
    lang_name = LANG_NAMES.get(code, code)
    st.session_state.messages.insert(1, {
        "role": "system",
        "content": f"From now on, respond in {lang_name}. Keep answers concise and friendly."
    })
    with st.sidebar:
        st.success(f"Language detected: {lang_name}")

def localized_question(text: str) -> str:
    """
    Translate field prompts ONLY if we have a supported non-English language.
    Otherwise, return the English prompt as-is.
    """
    code = st.session_state.lang
    if not code or code == "en" or code not in LANG_NAMES:
        return text
    lang_name = LANG_NAMES.get(code, code)
    msgs = [
        {"role": "system", "content": f"Translate the following short prompt into {lang_name}. Output only the translation."},
        {"role": "user", "content": text},
    ]
    try:
        resp = llm_chat(msgs, stream=False)
        return resp.choices[0].message.content.strip() if resp and resp.choices else text
    except Exception:
        return text

# ---------------------------- Main UI ----------------------------
st.title("🧭 TalentScout — Hiring Assistant (Groq)")
st.caption("Built with Streamlit + Groq’s fast LLM API. This assistant collects basic info and generates tailored technical questions.")

show_chat()

if not st.session_state.ended:
    user_input = st.chat_input("Type here… (say 'bye' to end)")
else:
    user_input = None

if user_input:
    detect_and_set_language(user_input)

    # Sentiment (bonus): quick gauge in sidebar
    s = analyzer.polarity_scores(user_input)["compound"]
    mood = "🙂 positive" if s > 0.2 else ("😐 neutral" if s >= -0.2 else "🙁 negative")
    with st.sidebar:
        st.caption(f"Sentiment guess: **{mood}**")

    # Early end?
    if user_input.strip().lower() in EXIT_KEYWORDS:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        if save_opt and st.session_state.candidate.full_name:
            if save_candidate_row(st.session_state.candidate):
                st.success(f"Saved to {CSV_PATH}")
                # Preview update
                try:
                    prev = pd.read_csv(CSV_PATH)
                    st.sidebar.dataframe(prev, use_container_width=True, height=200)
                except Exception:
                    pass
        end_conversation()
        st.stop()

    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Extract candidate snapshot
    cand_snapshot = extract_candidate_json(st.session_state.messages)
    c = st.session_state.candidate

    if cand_snapshot.full_name:
        c.full_name = cand_snapshot.full_name.strip()
    if cand_snapshot.email and validate_email(cand_snapshot.email):
        c.email = cand_snapshot.email.strip()
    if cand_snapshot.phone and validate_phone(cand_snapshot.phone):
        c.phone = cand_snapshot.phone.strip()
    if cand_snapshot.years_experience is not None:
        c.years_experience = cand_snapshot.years_experience
    if cand_snapshot.desired_positions:
        c.desired_positions = [p for p in cand_snapshot.desired_positions if p]
    if cand_snapshot.location:
        c.location = cand_snapshot.location.strip()
    if cand_snapshot.tech_stack:
        c.tech_stack = [t for t in cand_snapshot.tech_stack if t]

    # Ask for missing fields (localized)
    missing = next_missing_field(c)
    if missing:
        q = FIELD_QUESTIONS[missing]
        append_assistant(localized_question(q))
        st.stop()

    # Generate tech questions (printed in current language by LLM)
    if c.tech_stack and not st.session_state.tech_questions:
        qs = generate_tech_questions(c.tech_stack)
        st.session_state.tech_questions = qs
        # Stream a short acknowledgement
        ack_msgs = st.session_state.messages[:1] + [
            {"role": "assistant", "content": "Great, I’ll generate a few tailored questions on your stack."}
        ]
        stream = llm_chat(ack_msgs, stream=True)
        with st.chat_message("assistant"):
            placeholder = st.empty()
            acc = ""
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                acc += token
                placeholder.write(acc)
        with st.chat_message("assistant"):
            st.markdown("**Here are your tailored questions (answer any you like):**")
            for tech, items in qs.items():
                st.markdown(f"- **{tech}**")
                for i, q in enumerate(items, 1):
                    st.markdown(f"    {i}. {q}")
        st.stop()

    # Otherwise continue conversation
    stream = llm_chat(st.session_state.messages, stream=True)
    with st.chat_message("assistant"):
        acc = ""
        for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            acc += token
            st.write(acc)

# ---------------------------- Footer ----------------------------
col1, col2 = st.columns(2)

with col1:
    if st.button("✅ Finish & Thank Candidate"):
        if save_opt and st.session_state.candidate.full_name:
            if save_candidate_row(st.session_state.candidate):
                st.success(f"Saved to {CSV_PATH}")
                # Live preview after save
                try:
                    prev = pd.read_csv(CSV_PATH)
                    st.sidebar.dataframe(prev, use_container_width=True, height=200)
                except Exception:
                    pass
        end_conversation()

with col2:
    save_disabled = not st.session_state.candidate.full_name or not save_opt
    if st.button("💾 Save Candidate (CSV)", disabled=save_disabled):
        if save_candidate_row(st.session_state.candidate):
            st.session_state.saved_rows += 1
            st.success(f"Saved to {CSV_PATH} (total saves this session: {st.session_state.saved_rows})")
            # Live preview after save
            try:
                prev = pd.read_csv(CSV_PATH)
                st.sidebar.dataframe(prev, use_container_width=True, height=200)
            except Exception:
                pass

st.caption("Type 'bye' to end anytime.")
