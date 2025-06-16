import os
import json
import csv
import re
from typing import List, Tuple, Optional,Dict
from src.extractor import (
    extract_text_and_links,
    split_lines,
    debug_headings,
    find_section_bounds,
    extract_section,
    extract_name,
    extract_email,
    extract_phone,
    extract_linkedin,
    extract_github,
    extract_skills,
    extract_companies_positions_gemini,
    extract_jd_phrases,
    load_job_description,
    load_company_skills,
    extract_jd_keyword_weights
)



# ─── Configuration ────────────────────────────────────────────────────────────
RESUME_DIR  = "resumes"        # put your PDFs here
OUTPUT_JSON = "output.json"
OUTPUT_CSV  = "output.csv"

def process_resume(path: str, jd_path: Optional[str] = None, company_skills: Optional[List[str]] = None) -> dict:
    print(f"\n📄 Processing: {os.path.basename(path)}")
    text, links = extract_text_and_links(path)

    print("  • Splitting lines & detecting sections…")
    lines = split_lines(text)
    heads = debug_headings(lines)

    # Sections
    exp_s, exp_e = find_section_bounds(heads, "experience")
    edu_s, edu_e = find_section_bounds(heads, "education")
    skl_s, skl_e = find_section_bounds(heads, "skills")

    experience = extract_section(lines, exp_s, exp_e)
    education  = extract_section(lines, edu_s, edu_e)
    skills     = extract_skills(extract_section(lines, skl_s, skl_e))
     
     
        # ─── ATS logic ─────────────────────────────────────────────────
    jd_text      = load_job_description(jd_path) if jd_path else ""
    jd_phrases   = extract_jd_phrases(jd_text)

    # Combine UI-inputted skills + JD phrases
    required_set = set(company_skills or []) | set(jd_phrases)
    # 1) get list of required keywords
    required = list(required_set)

    # 2) get weights from Gemini
    weights = extract_jd_keyword_weights(jd_text, required)

    # 3) scan resume text for frequency
    text_lower = text.lower()
    freqs = {k: len(re.findall(rf"\b{re.escape(k)}\b", text_lower)) for k in required}

    # 4) cap freq at 3
    freqs = {k: min(v, 3) for k, v in freqs.items()}

    # 5) compute weighted score
    num = sum(weights[k] * freqs[k] for k in required if freqs[k] > 0)
    den = sum(weights[k] * 3 for k in required)  # max possible
    ats_score = round((num / den) * 100, 1) if den > 0 else None

    # 6) matched keywords
    matched = [k for k in required if freqs[k] > 0]




    print(f"    – Skills found: {len(skills)}")

    # Basic fields
    name     = extract_name(lines)
    email    = extract_email(text)
    phone    = extract_phone(text)
    linkedin = extract_linkedin(text, links)
    github   = extract_github(text, links)
    print(f"    – Name: {name}")
    print(f"    – Email: {email}")
    print(f"    – Phone: {phone}")
    print(f"    – LinkedIn: {linkedin}")
    print(f"    – GitHub: {github}")

    # Company–Position
    comps = extract_companies_positions_gemini(experience or "")

    return {
        "file_name": os.path.basename(path),
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "skills": skills,
        "required_skills": required,
        "keyword_weights": weights,
        "keyword_freqs": freqs,
        "matched_skills": matched,
        "ats_score": ats_score,
        "experience_section": experience,
        "companies_positions": comps,
        "education_section": education,
        
    }


def main():
    os.makedirs(RESUME_DIR, exist_ok=True)
    files = [
        f
        for f in os.listdir(RESUME_DIR)
        if f.lower().endswith(".pdf")
    ]
    print(f"🔍 Found {len(files)} resumes in {RESUME_DIR}")

    results = []
    for idx, fn in enumerate(files, 1):
        print(f"\n=== {idx}/{len(files)} ===")
        res = process_resume(os.path.join(RESUME_DIR, fn))
        results.append(res)

    # Write JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as jf:
        json.dump(results, jf, indent=2, ensure_ascii=False)
    print(f"\n✅ Wrote {OUTPUT_JSON}")

    # Write CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=list(results[0].keys()))
        writer.writeheader()
        for r in results:
            r["skills"]              = ";".join(r["skills"])
            r["companies_positions"] = "|".join(r["companies_positions"])
            writer.writerow(r)
    print(f"✅ Wrote {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
