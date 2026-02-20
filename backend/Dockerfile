FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code — v14 (prospect_audit v4: fixed asyncio.coroutine + f-string backslash, client_name in conclusion)
COPY . .

# Ensure default directories exist
RUN mkdir -p temp_docs

EXPOSE 8000

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
