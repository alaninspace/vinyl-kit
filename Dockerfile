FROM python:3.12-slim

WORKDIR /app

# Copy requirement files and project config
COPY requirements.txt pyproject.toml README.md ./
COPY src/ ./src/
COPY docs/ ./docs/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "src.docs_web.main:app", "--host", "0.0.0.0", "--port", "8000"]
