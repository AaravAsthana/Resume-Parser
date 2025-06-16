# 1) Base image: slim Python 3.12
FROM python:3.12-slim

# 2) Set workdir
WORKDIR /app

# 3) System dependencies (for pdfplumber, pytesseract, spacy, etc.)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 4) Copy project metadata and install Poetry
COPY pyproject.toml poetry.lock README.md ./
RUN pip install --no-cache-dir poetry \
 && poetry config virtualenvs.create false \
 && poetry install --only main --no-root --no-interaction --no-ansi


# 5) Copy source
COPY . .

# 6) Expose Streamlit port
EXPOSE 8501

# 7) Entry point
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
