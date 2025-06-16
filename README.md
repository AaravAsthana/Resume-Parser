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
│   ├── extractor.py
│   └── pipeline.py
├── assets/
│   └── logo.png
└── resumes/           # drop your PDF resumes here
```
## 🚀 Quickstart

### Prerequisites

-   Python 3.12
    
-   [Poetry](https://python-poetry.org/)
    
-   (Optional) Docker
    


### 1. Clone & Install

```bash

git clone https://github.com/<your‑username>/resume-parser.git cd resume-parser # create & activate virtualenv, install deps poetry install # download spaCy model poetry run python -m spacy download en_core_web_sm 
```

### 2. Configure
Create a `.env` file in project root:

```ini
GOOGLE_API_KEY=your_google_ai_studio_api_key
``` 

Put your PDF resumes into the `resumes/` folder.

### 3. Run Locally

```bash
poetry run streamlit run app.py
``` 

Then open [http://localhost:8501](http://localhost:8501) in your browser.

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

## 📄 License

MIT © 2025 Aarav Asthana