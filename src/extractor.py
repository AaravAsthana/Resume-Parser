import os
import re
import json
from typing import List, Tuple, Optional,Dict

import fitz               # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
import spacy
from dotenv import load_dotenv
import google.generativeai as genai

# ─── Load Secrets & Initialize LLM ─────────────────────────────────────────────
load_dotenv()  # reads .env in project root
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY in environment")

# configure Gemini via Generative AI Studio
genai.configure(api_key=API_KEY)
# use the “pro” variant (1.5) on free tier
GENIE_MODEL = genai.GenerativeModel("gemini-1.5-flash")

# ─── Constants ────────────────────────────────────────────────────────────────
SECTION_KEYWORDS = {
    "profile": ["profile", "summary", "objective"],
    "experience": ["experience", "professional experience", "work experience", "employment history", "work history"],
    "education": ["education", "academic background", "qualifications"],
    "skills": ["skills", "skill set", "technical skills", "competencies"],
    "projects": ["projects", "personal projects", "portfolio"],
    "certifications": ["certifications", "licenses", "credentials"],
    "achievements": ["achievements", "awards", "honors"],
    "activities": ["activities", "extracurricular activities", "volunteer work"]
}


EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
PHONE_REGEX = (
    r"(?:\+?\d{1,3}[-.\s]*)?"      # country code
    r"(?:\(?\d{2,4}\)?[-.\s]*)?"   # area code
    r"\d{3,4}[-.\s]?\d{3,4}"       # number
    r"(?:\s*(?:x|ext\.?)\s*\d{1,5})?"  # extension
)

LINKEDIN_REGEX = r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s/]+(?:/[^\s/]+)?"
GITHUB_REGEX   = r"^(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+/?$"

# load spaCy NER model
nlp = spacy.load("en_core_web_sm")


# ─── Text & Link Extraction ──────────────────────────────────────────────────
def extract_text_and_links(path: str) -> Tuple[str, List[str]]:
    """Extract full text plus all hyperlink URIs via PyMuPDF, fallback/pdfplumber, then OCR."""
    text, links = "", set()
    doc = fitz.open(path)
    for page in doc:
        text += page.get_text()
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                links.add(uri.rstrip("/"))
    if len(text) < 50:
        # fallback to pdfplumber
        with pdfplumber.open(path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    if len(text) < 50:
        # OCR fallback
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text += "\n" + pytesseract.image_to_string(img)
    return text, list(links)


# ─── Sectioning Utilities ────────────────────────────────────────────────────
def split_lines(text: str) -> List[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def debug_headings(lines: List[str]) -> List[Tuple[int, str, str]]:
    hs = []
    for i, ln in enumerate(lines):
        low = ln.lower()
        for sec, kws in SECTION_KEYWORDS.items():
            if any(low.startswith(k) for k in kws):
                hs.append((i, ln, sec))
                break
    return hs


def find_section_bounds(
    heads: List[Tuple[int, str, str]], target: str
) -> Tuple[Optional[int], Optional[int]]:
    for idx, (ln, _, sec) in enumerate(heads):
        if sec == target:
            start = ln + 1
            end = heads[idx + 1][0] if idx + 1 < len(heads) else None
            return start, end
    return None, None


def extract_section(
    lines: List[str], start: Optional[int], end: Optional[int]
) -> Optional[str]:
    if start is None or start >= len(lines):
        return None
    return "\n".join(lines[start : (end or len(lines))]).strip()


# ─── Field Extractors ────────────────────────────────────────────────────────
def extract_name(lines: List[str]) -> Optional[str]:
    # 1–4 capitalized tokens
    pat = r"^[A-Z][a-zA-Z’'-]+(?:\s+[A-Z][a-zA-Z’'-]+){0,3}$"
    for ln in lines[:10]:
        if re.match(pat, ln):
            return ln
    # spaCy PERSON fallback
    doc = nlp(" ".join(lines[:50]))
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return None


def extract_email(text: str) -> Optional[str]:
    m = re.search(EMAIL_REGEX, text)
    if m:
        return m.group()
    m2 = re.search(r"mailto:([^)\s]+)", text, flags=re.IGNORECASE)
    return m2.group(1) if m2 else None


def extract_phone(text: str) -> Optional[str]:
    m = re.search(PHONE_REGEX, text)
    if not m:
        return None
    raw = m.group()
    digits = re.sub(r"\D", "", raw)
    return raw.strip() if len(digits) >= 10 else None


def extract_linkedin(text: str, links: List[str]) -> Optional[str]:
    # prefer real hyperlink URIs
    for uri in links:
        if re.match(LINKEDIN_REGEX, uri):
            return uri
    m = re.search(LINKEDIN_REGEX, text)
    return m.group().rstrip("/") if m else None


def extract_github(text: str, links: List[str]) -> Optional[str]:
    for uri in links:
        if re.match(GITHUB_REGEX, uri):
            return uri
    m = re.search(GITHUB_REGEX, text, flags=re.IGNORECASE)
    return m.group().rstrip("/") if m else None


def extract_skills(section: Optional[str]) -> List[str]:
    if not section:
        return []
    text = section.lower()
    tokens = re.findall(r'\b[a-zA-Z][a-zA-Z0-9.+#-]{2,}\b', text)
    return list(dict.fromkeys(tokens))

# ─── Company–Position Extraction ─────────────────────────────────────────────
def extract_companies_positions_regex(experience: str) -> List[str]:
    """
    After experience is extracted, look only at lines ≤6 words with no commas, no dates,
    and no “hackathon”. Then apply patterns for:
      1. Inline "Position at Company"
      2. Inline "Company - Position" or "Company: Position"
      3. Multi-line adjacent: Company⏎Position or Position⏎Company
    Returns only Company-Position strings, deduped in original order.
    """
    if not experience:
        return []

    # 1. Pre-split & filter lines
    raw_lines = [l.strip() for l in experience.splitlines() if l.strip()]
    filt = []
    for l in raw_lines:
        # exclude locations, dates, hackathons, overly long lines
        if ',' in l:
            continue
        if re.search(r"\b20\d{2}\b", l):
            continue
        if 'hackathon' in l.lower():
            continue
        if len(l.split()) > 6:
            continue
        filt.append(l)

    pairs = []
    joined = "\n".join(filt)

    # helper to add a comp-pos pair only once
    def add_pair(comp: str, pos: str):
        comp, pos = comp.strip(), pos.strip()
        if comp and pos:
            pair = f"{comp}-{pos}"
            if pair not in pairs:
                pairs.append(pair)

    # 2. Inline "Position at Company"
    for pos, comp in re.findall(
        r"([A-Z][\w/&+\s'’-]{2,}?)\s+at\s+([A-Z][\w.&()'’\-\s]+)",
        joined
    ):
        add_pair(comp, pos)

    # 3. Inline "Company - Position" or "Company: Position"
    for comp, pos in re.findall(
        r"([A-Z][\w.&()'’\-\s]+?)\s*[-:]\s*([A-Z][\w/&+\s'’-]{2,})",
        joined
    ):
        add_pair(comp, pos)

    # 4. Multi-line adjacent detection
    for i in range(len(filt) - 1):
        first, second = filt[i], filt[i + 1]
        # Company then Position
        if (re.match(r"[A-Z][\w.&()'’\-\s]+$", first)
            and re.match(r"[A-Z][\w/&+\s'’-]{2,}$", second)):
            add_pair(first, second)
        # Position then Company
        if (re.match(r"[A-Z][\w/&+\s'’-]{2,}$", first)
            and re.match(r"[A-Z][\w.&()'’\-\s]+$", second)):
            add_pair(second, first)

    return pairs


def extract_companies_positions_gemini(experience: str) -> List[str]:
    """Primary extractor via Gemini; falls back to regex if anything fails."""
    if not experience:
        return []

    prompt = (
        "You are a parser. Given the following EXPERIENCE section from a resume, "
        "output _only_ a JSON array of objects with exactly two keys: "
        "\"company\" and \"position\".\n\n"
        "EXPERIENCE:\n"
        f"{experience}\n\n"
        "OUTPUT:\n"
    )

    print("↪ [Gemini] Sending prompt…")
    try:
        resp = GENIE_MODEL.generate_content(prompt)
        raw = resp.text.strip() 
        print("🔍 [Gemini] Raw output:", raw)
    except Exception as e:
        print(f"❌ [Gemini] API error: {e}. Falling back to regex.")
        return extract_companies_positions_regex(experience)

    # strip echoed prompt if present
     # 1) Remove triple‑backtick fences, optionally with “json” label
    #    e.g. ```json\n[ … ]\n```
    raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()

    # 2) Also remove any leading/trailing single backticks
    raw = raw.strip("`").strip()

    # 3) Now parse
    try:
        arr = json.loads(raw)
        pairs = [f"{c['company']}-{c['position']}" for c in arr]
        print(f"✅ [Gemini] Parsed {len(pairs)} pairs.")
        return pairs
    except Exception as e:
        print(f"❌ [Gemini] JSON parse error after stripping fences: {e}. Falling back to regex.")
        return extract_companies_positions_regex(experience)
    

def extract_jd_phrases(jd_text: str, max_phrases: int = 20) -> List[str]:
    """
    Use Gemini to pull out the top `max_phrases` key skills/phrases
    from the job description text, returning a lowercase list.
    """
    if not jd_text or not GENIE_MODEL:
        return []

    prompt = (
        f"You are a keyword extraction assistant. "
        f"Given the following job description, extract the top {max_phrases} distinct "
        "skills or requirement phrases as a JSON array of strings.\n\n"
        "JOB DESCRIPTION:\n"
        f"{jd_text}\n\n"
        "OUTPUT (strictly JSON list of strings):"
    )

    try:
        resp = GENIE_MODEL.generate_content(prompt)
        raw = resp.text.strip()
        # strip any code fences
        raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
        phrases = json.loads(raw)
        # normalize
        return [p.lower() for p in phrases][:max_phrases]
    except Exception as e:
        print(f"❌ [Gemini] JD keyword extraction failed: {e}")
        return []


def load_job_description(path: str = "job_description.txt") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""

def load_company_skills(path="company_skills.json") -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [s.lower() for s in data.get("required_skills", [])]
    except FileNotFoundError:
        return []
def extract_jd_keyword_weights(jd_text: str, keywords: List[str]) -> Dict[str, float]:
    """
    Prompt Gemini to rate each keyword 0–1 based on its importance in the JD.
    Returns a dict {keyword: weight}.
    """
    prompt = (
        "You are an assistant that ranks how important each skill is "
        "for this job description.  Output strictly JSON mapping each "
        "keyword to a weight between 0 and 1 (higher means more critical).\n\n"
        f"JOB DESCRIPTION:\n{jd_text}\n\n"
        f"KEYWORDS:\n{json.dumps(keywords, indent=2)}\n\n"
        "OUTPUT:\n"
    )
    try:
        resp = GENIE_MODEL.generate_content(prompt)
        raw = resp.text.strip()
        raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
        weights = json.loads(raw)
        # ensure floats and lowercase keys
        return {k.lower(): float(v) for k, v in weights.items() if k.lower() in map(str.lower, keywords)}
    except Exception as e:
        print("⚠️ Gemini weight extraction failed:", e)
        # fallback to equal weights
        return {k.lower(): 1.0 for k in keywords}
