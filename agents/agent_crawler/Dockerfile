FROM python:3.13-slim

# 1. Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libasound2t64 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- CRITICAL FIX: Set Global Playwright Path ---
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 2. Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r requirements.txt

# 3. Install Playwright Browsers to the GLOBAL path
# We run this as root so it can create the folder
RUN playwright install chromium --with-deps

# 4. Security: Setup user and fix permissions for the browser folder
RUN adduser --disabled-password --gecos "" myuser && \
    chown -R myuser:myuser /app && \
    chown -R myuser:myuser /ms-playwright

USER myuser
COPY . .

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]