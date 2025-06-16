# 1) Base image
FROM python:3.12-slim

# 2) Set working directory
WORKDIR /app

# 3) Copy pyproject for Poetry install
COPY pyproject.toml poetry.lock ./

# 4) Install Poetry & dependencies
RUN pip install poetry \
 && poetry config virtualenvs.create false \
 # only install the "main" group (i.e. no dev-dependencies)
 && poetry install --only main --no-interaction

# 5) Copy all your code
COPY . /app

# 6) Expose Streamlit port
EXPOSE 8501

# 7) Default command
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
