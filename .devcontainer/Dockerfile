# Use a base image that includes Python.
# You can choose a specific Python version if needed, e.g., python:3.10-slim-bookworm
FROM python:3.11-slim-bookworm

# Set environment variables for non-interactive installations
ENV DEBIAN_FRONTEND=noninteractive

# Add necessary packages for user creation (sudo, git, openssh-client)
# AND common dependencies needed for gcloud SDK (curl, gnupg, apt-transport-https, ca-certificates, lsb-release)
# AND build-essential (often needed for Python packages like cffi/cryptography that Poetry might install)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    git \
    openssh-client \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    lsb-release \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create the 'vscode' user and group with UID/GID 1000 (standard for dev containers)
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the group and user, add to sudoers, and install libffi-dev (often needed for Python packages)
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash -u $USER_UID -g $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y libffi-dev \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/* # Clean up apt lists again after this install

# --- Start Google Cloud SDK Installation ---
# Add Google Cloud public key
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

# Add the Cloud SDK distribution URI to the apt sources list
RUN echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list

# Update the apt-get package list and install the Cloud SDK
RUN apt-get update && apt-get install -y google-cloud-sdk

# Install optional components if needed (e.g., kubectl, gsutil)
# Uncomment the line below if you need these:
# RUN apt-get install -y google-cloud-sdk-gke-gcloud-auth-plugin google-cloud-sdk-app-engine-python
# --- End Google Cloud SDK Installation ---

# Set environment variables for Poetry
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="$POETRY_HOME/bin:$PATH"

# Install Poetry
# Ensure curl is installed before using it for the Poetry script, then clean up.
# Curl is already installed from the gcloud SDK dependencies.
RUN curl -sSL https://install.python-poetry.org | python - \
    && rm -rf /var/lib/apt/lists/* # Clean up apt lists again, if any were generated

# Switch to the newly created 'vscode' user for subsequent commands and the default shell
USER $USERNAME

# Set the working directory for your project inside the Codespace
# CODESPACE_NAME is a Dev Container variable, use that directly
WORKDIR /workspaces/${CODESPACE_NAME}

# Command to keep the container running
CMD ["bash"]
