# TalentScout – Hiring Assistant (Groq + Streamlit)

A fast screening chatbot for a fictional tech recruitment agency. It gathers candidate basics and generates tailored tech questions from their declared stack, powered by Groq's `llama-3.3-70b-versatile`.

## ✨ Features
- Greeting + context-aware flow
- Collects **Full Name, Email, Phone, Years of Experience, Desired Position(s), Location, Tech Stack**
- Generates **3–5 technical questions per tech**
- **Multilingual**: detects user language and responds accordingly
- **Exit keywords** end gracefully (bye, exit, stop, thanks, …)
- **Sentiment gauge** (bonus) in sidebar
- **CSV saving (opt-in)** with **GDPR options**:
  - Hash **email/phone** before saving
  - **Delete last saved row** button
- **Live CSV preview** in sidebar after saving

## ⚙️ Tech
- Python, Streamlit (UI)
- Groq API (`groq` SDK) – Chat Completions with streaming & JSON mode  
- `dotenv`, `pandas`, `vaderSentiment`, `langdetect`

## 🔐 Privacy
- Data stays local. CSV saving is **opt-in**.
- Hashing for email/phone is enabled by default.
- For demos, avoid real PII or scrub before saving.

## 🚀 Local Setup
1. Create and activate a venv  
   - Windows: `.venv\Scripts\activate`  
   - macOS/Linux: `source .venv/bin/activate`
2. Install deps  
   ```bash
   pip install -r requirements.txt
