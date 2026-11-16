# Use official lightweight Python image matching Python 3.11
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system build essentials if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies including pandas, ta, requests, google-cloud-bigquery, etc.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your project files into the container
COPY . .

# Ensure Python output is unbuffered so logs stream instantly to Cloud Logging
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Execution entrypoint for your Cloud Run Job
# Replace 'main.py' or 'run_pipeline.py' with your actual job runner script
# Execution entrypoint for your Cloud Run Job pointing to ingest_fmp/main.py
CMD ["python", "src/ingest_fmp/main.py"]