# --- STAGE 1: Get the uv binary from its official image ---
FROM ghcr.io/astral-sh/uv:latest AS uv_installer

# --- STAGE 2: Main build ---
FROM python:3.11-slim-bookworm

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PATH="/home/vscode/.local/bin:$PATH"

# Define user arguments
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# 1. Install System Dependencies + Playwright Libraries
RUN apt-get update -o Acquire::Retries=3 && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        sudo git curl gnupg apt-transport-https ca-certificates \
        lsb-release build-essential libffi-dev \
        libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
        libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
        libcairo2 libasound2 libxshmfence1 && \
    groupadd --gid ${USER_GID} ${USERNAME} && \
    useradd -s /bin/bash -u ${USER_UID} -g ${USER_GID} -m ${USERNAME} && \
    echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} && \
    chmod 0440 /etc/sudoers.d/${USERNAME} && \
    mkdir -p /ms-playwright && chown -R ${USERNAME}:${USERNAME} /ms-playwright && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Install Google Cloud SDK (Fixed Keyring Setup)
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /etc/apt/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update -o Acquire::Retries=3 \
    && apt-get install -y --no-install-recommends google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

# 3. Copy uv binaries from Stage 1
COPY --from=uv_installer /uv /usr/local/bin/uv
COPY --from=uv_installer /uvx /usr/local/bin/uvx

# 4. Install Playwright browser as the vscode user
USER $USERNAME
WORKDIR /workspaces

RUN uv pip install --system playwright \
    && playwright install chromium

CMD ["bash"]