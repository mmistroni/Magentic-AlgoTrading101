FROM python:3.13-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 🔥 FIX FOR ADK ISSUE #4601: Grant write permissions to the ADK browser config assets folder
RUN mkdir -p /usr/local/lib/python3.13/site-packages/google/adk/cli/browser/assets/config/ && \
    chmod -R 777 /usr/local/lib/python3.13/site-packages/google/adk/cli/browser/assets/config/


RUN adduser --disabled-password --gecos "" myuser && \
    chown -R myuser:myuser /app

COPY . .

USER myuser

ENV PATH="/home/myuser/.local/bin:$PATH"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]