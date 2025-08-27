# TalentScout — Hiring Assistant (Groq + Streamlit)

An intelligent screening assistant for a (fictional) tech recruitment agency. TalentScout collects candidate details and generates **tailored technical questions** based on the declared tech stack — built with **Python + Streamlit** and powered by **Groq** LLMs.

> 🎥 **Demo Video:** [https://www.loom.com/share/Hire ](https://www.loom.com/share/a768625b1c1549d793c86cdd61bef750?sid=73ba8fb9-e0d9-4916-bbd9-08265a69f610) 
> 🌐 **Live App (optional):** [https://Talent_Scout.streamlit.app](https://talentscout-6nzkat93gtg8t4uqr8nxuu.streamlit.app/)

---

## ✨ Features

- **Clean chat UI (Streamlit)**
- **Guided intake** of: Full Name, Email, Phone, Years of Experience, Desired Position(s), Location, Tech Stack
- **Tech-aware question generation:** 3–5 questions per technology
- **Context awareness:** conversation history + structured JSON extraction
- **Multilingual**
  - Robust **auto-detection** (ignores tiny/ambiguous texts)
  - **Manual override** (language dropdown)
  - Field prompts localized on the fly
- **GDPR-friendly data handling**
  - Optional local CSV saving (`data/candidates.csv`)
  - SHA-256 **hashing** of email/phone before save
  - **Delete last saved row** button
  - **CSV preview** in sidebar after saving
- **Sentiment gauge** (bonus) in sidebar
- **Graceful exit** on common conversation-ending keywords (English + several Indian languages)

---

## 🧭 How it works

1. The assistant greets the user and asks for fields in a fixed order.
2. After each user turn, the app asks the LLM to output a **strict JSON snapshot** of known fields and merges it with state.
3. When the **tech stack** is provided, it generates **3–5 questions per tech**.
4. Exit keywords (e.g., “bye”, “धन्यवाद”, “நன்றி”) end the chat politely.

---

## 🗂️ Project Structure

```
talentscout/
│
├── app/
│   ├── app.py           # UI, session state, multilingual, saving, preview
│   ├── helpers.py       # Groq API calls, JSON extraction, validators
│   ├── prompts.py       # System prompt, exit keywords, field order/questions
│   └── __init__.py
│
├── data/                # local CSV storage (created at runtime)
│   └── candidates.csv
│
├── .env                 # GROQ_API_KEY=...
├── requirements.txt
├── README.md
└── .gitignore
```

---

## ⚙️ Prerequisites

- Python **3.11+**
- A **Groq API key** → https://console.groq.com/
- (Recommended) **Virtual environment**

---

## 🚀 Quickstart

### 1) Clone & set up
```bash
git clone https://github.com/<you>/talentscout.git
cd talentscout
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

> If you see `No module named 'numpy.rec'`, run:
```bash
pip install --upgrade "numpy>=2.0.0" "pandas>=2.2.2"
```

### 3) Environment variable
Create `.env` in the repo root:
```
GROQ_API_KEY=YOUR_REAL_KEY
```

### 4) Run
```bash
streamlit run app/app.py
```
Open the URL printed in the terminal (e.g., `http://localhost:8501`).

---

## 🧑‍💻 Using the App

1. In the **sidebar**:
   - ✅ “Save anonymized candidate data locally (CSV)”
   - ✅ “Hash email/phone before saving (GDPR-friendly)”
   - (Optional) Pick a language in **Language** dropdown

2. In the chat, enter:
```
Priya Sharma
priya.sharma@example.com
+91 9876543210
5
Backend Developer, Software Engineer
Bangalore, India
Python, Django, PostgreSQL, Docker
```

3. You’ll see **tailored technical questions** per technology.
4. Click **💾 Save Candidate (CSV)** or **✅ Finish & Thank Candidate**:
   - The sidebar shows **Saved Candidates (Preview)**.
   - Click **🗑️ Delete last saved row** to remove the most recent entry.
5. Type `bye` to exit gracefully.

### Multilingual
- **Auto-detect**: The app only switches from English on longer/high-confidence non-English text (to avoid false detection on “hi/ok”).  
  Example to trigger Spanish:
  ```
  Hola, me gustaría comenzar la entrevista técnica ahora.
  ```
- **Manual override**: Select your language in the sidebar (e.g., Hindi “hi”, Tamil “ta”, Spanish “es”).

---

## 🧠 LLM + Prompts

- **System prompt** (in `prompts.py`) pins the assistant’s purpose and language policy.
- **Extraction prompt** (in `helpers.py`) asks the model to return a **single JSON object** containing:  
  `full_name, email, phone, years_experience, desired_positions, location, tech_stack`
- **Question prompt** generates **3–5** questions per declared technology.

This separation keeps behavior **predictable** and **robust**.

---

## 🔐 Data & Privacy

- **Local only**: CSV is stored at `data/candidates.csv`.
- **Opt-in saving**: controlled by a sidebar checkbox.
- **Hashing**: email & phone stored as `hash:<12hex>…` (SHA-256) when enabled.
- **Delete last saved row**: removes the most recent CSV entry.
- **Preview**: sidebar table updates after save.

> For real production use, add explicit consent, retention policy, and right-to-erasure endpoints.

---

## ☁️ Deploy to Streamlit Community Cloud (optional)

1. Push to GitHub (don’t commit `.env`, `.venv`, or `data/`):
```bash
git init
echo ".venv/" >> .gitignore
echo ".env" >> .gitignore
echo "data/" >> .gitignore
git add .
git commit -m "feat: initial TalentScout (Groq + Streamlit)"
git branch -M main
git remote add origin https://github.com/<you>/talentscout.git
git push -u origin main
```

2. Go to **https://share.streamlit.io** → **New app**  
   - Repo: `<you>/talentscout`  
   - Branch: `main`  
   - File: `app/app.py`

3. In **Secrets**, add:
```
GROQ_API_KEY="YOUR_REAL_KEY"
```

4. Deploy → paste the live URL at the top of this README.

---

## 🧩 Troubleshooting

- **`ModuleNotFoundError: vaderSentiment`**  
  `pip install vaderSentiment==3.3.2` (in your active venv).

- **`Preview unavailable: No module named 'numpy.rec'`**  
  `pip install --upgrade "numpy>=2.0.0" "pandas>=2.2.2"`

- **CSV not saved**  
  Ensure the checkbox is **on** and that **Full Name** is filled.  
  Path is `<repo>/data/candidates.csv`. The `data/` folder is auto-created.

- **Language seems random on tiny inputs**  
  This is by design to avoid false positives. Use a **longer sentence** or the **Language** dropdown.

- **Port already in use**  
  `streamlit run app/app.py --server.port 8502`

---

## ✅ Assignment Mapping

- **Functionality/UI**: Streamlit chat interface, clear flow, exit on keywords  
- **Information Gathering**: all required fields with basic validation  
- **Tech Questions**: 3–5 per item in the declared stack  
- **Context Handling**: session history + JSON extraction keeps state coherent  
- **Fallbacks**: validation + clarifying prompts, robust language detection  
- **End Conversation**: graceful closing with thanks/next steps  
- **Prompt Engineering**: dedicated system, extraction, and generation prompts  
- **Data Handling**: local CSV, opt-in, hashing, deletion, preview  
- **Documentation**: this README (+ optional demo video, deploy steps)  

---

## 🛠️ Tech Stack

- Python, Streamlit  
- Groq LLMs (`groq` SDK / Chat Completions)  
- pandas, numpy  
- vaderSentiment (optional sentiment gauge)  
- langdetect (language detection)  
- python-dotenv (env vars)

Recommended versions:
```
streamlit >= 1.32
groq >= 0.11
python-dotenv >= 1.0
pandas >= 2.2.2
numpy >= 2.0.0
vaderSentiment >= 3.3.2
langdetect >= 1.0.9
```

---


