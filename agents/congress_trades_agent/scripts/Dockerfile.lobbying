# Use python 3.9
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements from the parent directory relative to your build context
#COPY ../requirements.txt .

# Copy everything from your current folder directly into /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt


# Match your path configuration so Python finds your modules
ENV PYTHONPATH="${PYTHONPATH}:/app"

# Ensure Python output is streamed directly to Cloud Run logs without buffering
ENV PYTHONUNBUFFERED=1

# Run your exact daily downloader script
CMD ["python", "lobbying_daily_scrape.py"]