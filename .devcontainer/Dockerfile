# --- STAGE 1: Get the uv binary from its official image ---
FROM ghcr.io/astral-sh/uv:latest AS uv_installer

# --- STAGE 2: Main build ---
FROM python:3.11-slim-bookworm

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="/opt/poetry/bin:$PATH"

# Define user arguments
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# 1. Install System Dependencies + PLAYWRIGHT LIBRARIES
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        sudo git curl gnupg apt-transport-https ca-certificates \
        lsb-release build-essential libffi-dev \
        # --- Essential Playwright/Chromium Dependencies ---
        libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
        libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
        libcairo2 libasound2 libxshmfence1 libnss3 \
    # Create the user and group
    && groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash -u $USER_UID -g $USER_GID -m $USERNAME \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Google Cloud SDK
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Poetry & uv (from Stage 1)
RUN curl -sSL https://install.python-poetry.org | python -
COPY --from=uv_installer /uv /usr/local/bin/uv
COPY --from=uv_installer /uvx /usr/local/bin/uvx

# 4. Pre-install Playwright Browser (Optional but recommended for speed)
# We do this as root so it goes into /root/.cache/ms-playwright
RUN pip install playwright && playwright install chromium

# Switch to the 'vscode' user
USER $USERNAME
WORKDIR /workspaces/${CODESPACE_NAME}

# Command to keep the container running
CMD ["bash"]