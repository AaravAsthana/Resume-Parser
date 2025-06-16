# Resume Parser Pro

A local/streamlit‐based resume parsing application with:

- PDF text + hyperlink extraction (PyMuPDF, pdfplumber, OCR fallback)  
- Section detection (experience, education, skills, etc.)  
- Name, email, phone, LinkedIn & GitHub link extraction via regex & NER  
- Skill extraction & optional company‑supplied or JD‑derived keyword matching  
- ATS score calculation & animated gauge/bar display  
- Company–Position pair extraction (regex + Google Gemini fallback)  
- Export JSON, Excel; interactive per‑resume viewer in Streamlit  
- Dockerfile + Poetry for reproducible local or container use  

---

## 📁 Project Layout

```text
Resume_Parser/
├── Dockerfile
├── README.md
├── pyproject.toml
├── poetry.lock
├── app.py
├── src/
│   ├── __init__.py
│   ├── extractor.py
│   └── pipeline.py
├── assets/
│   └── logo.png
├── requirements.txt
└── resumes/           # drop your PDF resumes here
```
## 🚀 Quickstart

### 📦 Installation

1.  **Clone the repo**
    
    ```bash
    `git clone https://github.com/AaravAsthana/Resume-Parser.git cd Resume-Parser` 
    ```
2.  **Create & activate a virtualenv**
    
    ```bash
    `python3.12 -m venv .venv source .venv/bin/activate # macOS/Linux .venv\Scripts\activate # Windows PowerShell` 
    ```
3.  **Install dependencies**
    
    ```bash
    `pip install --upgrade pip
    pip install -r requirements.txt` 
    
    > This will pull in everything—including the spaCy model wheel listed in `requirements.txt`—so you won’t need to manually `python -m spacy download en_core_web_sm`.
    ```
4.  **(Optional) Docker**  
    If you prefer Docker:
    
    ```bash
    docker build -t resume-parser:latest .
    docker run -p 8501:8501 resume-parser:latest 
    ```
    Then open [http://localhost:8501](http://localhost:8501) in your browser.
    

----------

## 🔑 Environment Variables

-   Copy `.env.example` to `.env` and fill in:
    
   ``` ini    
    GOOGLE_API_KEY=your-api-key 
  ```  
-   **On Streamlit Cloud**, add the same key under **Settings → Secrets** as TOML:
    
 ```toml
  GOOGLE_API_KEY = "your-api-key"
 ```
----------
## 🚀 Running Locally

With pip:

```bash
streamlit run app.py
```

With Poetry:
```bash
poetry run streamlit run app.py
```
Then open http://localhost:8501 in your browser. 

----------

## 🐳 Docker

1.  **Build image** (must have `Dockerfile` in project root):
    
    ```bash
    `docker build -t resume-parser-image:latest .` 
    ```
2.  **Run container** (map port, pass API key):
    
   ```bash
    docker run -p 8501:8501 \
	    -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
	     resume-parser-image:latest 
```
3.  Browse to [http://localhost:8501](http://localhost:8501).

    > _(For future‐proofing)_

```dockerfile
# Dockerfile snippet
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN apt-get update && apt-get install -y tesseract-ocr libgl1-mesa-glx && \
    pip install --no-cache-dir -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"] 
```

----------

## ⚙️ Configuration & Usage

-   **Company Inputs**: enter comma‑separated “required skills” or upload a plain‑text JD.
    
-   **Upload Resumes**: drop one or more PDFs, click **Process Resumes**.
    
-   **Sidebar**: shows progress bar, clickable list of parsed resumes.
    
-   **Main View**: per‑resume PDF embed + animated ATS gauge/bar + details table + per‑field scroll for long text.
    
-   **Download**: Excel export of all parsed resumes or single‑resume CSV view.
    

----------

## 🛠️ How It Works

1.  **extractor.py**
    
    -   `extract_text_and_links()` pulls text & link URIs from PDF (PyMuPDF), falls back to `pdfplumber` or OCR.
        
    -   Regex + spaCy for name, email, phone, LinkedIn/GitHub.
        
    -   Section split via heading keywords.
        
    -   Regex + Google Gemini to pull Company–Position pairs.
        
2.  **pipeline.py**
    
    -   Invokes extractor, builds skill list.
        
    -   Loads “required skills” (UI input or `company_skills.json`) + JD phrases.
        
    -   Matches resume skills vs. required set → ATS score %.
        
    -   Returns structured dict per resume.
        
3.  **app.py**
    
    -   Streamlit front‑end, PDF embed, controls, animated gauge/bar, table UI, download buttons.
        

----------
## 📝 What’s Inside

- `extractor.py` / `pipeline.py`: Resume parsing logic, company skill & JD keyword matching, ATS‑score calculation.

- `app.py`: Streamlit UI with file uploader, ATS donut animation, resume viewer, and downloadable Excel.

- `requirements.txt`: All PyPI dependencies including spaCy’s `en_core_web_sm` wheel.

- `pyproject.toml`: Poetry manifest, if you prefer that route.
----------
## 📝 Future / Docker Tips

-   **Adding README.md** ensures Poetry can package the project (otherwise use `--no-root`).
    
-   To rebuild after code changes:
    
    ```bash
    docker build -t resume-parser-image:latest .
    docker run -p 8501:8501 -e GOOGLE_API_KEY="$GOOGLE_API_KEY" resume-parser-image:latest 
    ```
-   **Common pitfalls**:
    
    -   `.env` not loaded → missing API key errors
        
    -   spaCy model not installed → run `spacy download en_core_web_sm`
        
    -   Docker context missing `Dockerfile` → ensure you’re in project root
        

----------
## 🤝 Contributing
Feel free to open issues or PRs. If you add new features, please update this README accordingly.

----------
## 📄 License

MIT © 2025 Aarav Asthana
