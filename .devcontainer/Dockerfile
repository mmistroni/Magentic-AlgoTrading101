# --- STAGE 1: Get the uv binary from its official image ---
# We use this stage only to extract the binary.
FROM ghcr.io/astral-sh/uv:latest AS uv_installer

# --- STAGE 2: Your main devcontainer image build ---
FROM python:3.11-slim-bookworm

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="/opt/poetry/bin:$PATH"

# Define user arguments (standard for dev containers)
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# 1. Install System Dependencies and Create User/Group
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        sudo \
        git \
        openssh-client \
        curl \
        gnupg \
        apt-transport-https \
        ca-certificates \
        lsb-release \
        build-essential \
        libffi-dev \
    # Create the user and group
    && groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash -u $USER_UID -g $USER_GID -m $USERNAME \
    # Add user to sudoers
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Google Cloud SDK
# Add Google Cloud public key and repo
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    # Update and install the SDK
    && apt-get update && apt-get install -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

    
# 3. Install Poetry
RUN curl -sSL https://install.python-poetry.org | python -

# 4. Install uvx (The Corrected Multi-Stage Copy)
# The binaries are located directly in the root of the uv_installer image.
COPY --from=uv_installer /uv /usr/local/bin/uv
COPY --from=uv_installer /uvx /usr/local/bin/uvx
# Switch to the newly created 'vscode' user for security and file ownership
USER $USERNAME

# Set the working directory for your project
WORKDIR /workspaces/${CODESPACE_NAME}

# Command to keep the container running
CMD ["bash"]