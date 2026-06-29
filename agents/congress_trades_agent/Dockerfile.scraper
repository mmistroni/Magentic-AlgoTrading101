# Use python 3.9
FROM python:3.9-slim

# Set working directory to root
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPY EVERYTHING (Includes the 'scripts' folder)
COPY . .

# CRITICAL FIX: Tell Python to look inside the 'scripts' folder for modules
ENV PYTHONPATH="${PYTHONPATH}:/app/scripts"

# Default command
CMD ["python", "scripts/scraper_contracts.py"]