FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code — v19 (dashboard: prospect-audit moved to #1, updated preview with real output data)
COPY . .

# Ensure default directories exist
RUN mkdir -p temp_docs

EXPOSE 8000

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
