---
title: Personal AI Studio
emoji: 🧠
colorFrom: green
colorTo: red
sdk: docker
app_port: 8501
app_file: app.py
pinned: false
license: mit
---

# 🧠 Personal AI Studio

**STT, LLM, RAG, local knowledge search, Excel summaries, image metadata, and source-grounded answers in one Streamlit workspace.**

Public app: https://jeonghwanju-personal-ai-studio.hf.space

GitHub: https://github.com/coding-jhj/Personal-AI-Studio

---

## ✨ Highlights

| Area | What It Does |
| --- | --- |
| 🎙 Voice | Audio upload STT with OpenAI transcription models |
| 🧠 LLM | Gemini, OpenAI, and local fallback answer generation |
| 🔎 RAG | TF-IDF based local retrieval with visible source cards |
| 📊 Data | Excel summaries and local document scanning |
| 🖼 Media | Photo metadata indexing from the `photos/` folder |
| 🛡 Safety | Works without API keys and never commits local secrets |

---

## 🧩 Default Models

```env
GEMINI_MODEL=gemini-3.5-flash
OPENAI_MODEL=gpt-5.5
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
```

You can override these in the app sidebar or deployment secrets.

---

## 🚀 Run Locally

```powershell
cd C:\RAG
pip install -r requirements.txt
streamlit run app.py
```

Optional local `.env`:

```env
GOOGLE_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash

OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.5
OPENAI_STT_MODEL=gpt-4o-mini-transcribe
```

---

## 🌐 Deploy

This repository is ready for **Hugging Face Spaces Docker SDK**.

Required files:

- `Dockerfile`
- `requirements.txt`
- `README.md`
- `app.py`
- `.streamlit/config.toml`

Secrets should be configured in the hosting platform, not committed to GitHub.

Use `.streamlit/secrets.example.toml` as the template.

---

## 🛡 Security

The repository intentionally excludes:

- `.env`
- `.streamlit/secrets.toml`
- class materials
- screenshots
- local cache files

The public repo contains only the app and deployment files needed to run **Personal AI Studio**.
