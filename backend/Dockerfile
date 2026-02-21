FROM python:3.11-slim

WORKDIR /app

# Install Node.js (for docx npm package — branded DOCX generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code — v21 (Standalone Page Design Agent + GEMINI_API_KEY)
COPY . .

# Install Node.js dependencies (docx npm package for branded DOCX output)
RUN npm install --omit=dev

# Ensure default directories exist
RUN mkdir -p temp_docs

EXPOSE 8000

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
