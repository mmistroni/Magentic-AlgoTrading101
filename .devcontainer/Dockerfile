# Use a base image that includes Python.
# You can choose a specific Python version if needed, e.g., python:3.10-slim-bookworm
FROM python:3.11-slim-bookworm

# Add necessary packages for user creation (sudo, git, openssh-client are common for dev containers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    git \
    openssh-client \
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
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Poetry
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PATH="$POETRY_HOME/bin:$PATH"

# Install Poetry
# Ensure curl is installed before using it for the Poetry script, then clean up.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -sSL https://install.python-poetry.org | python - \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

# Switch to the newly created 'vscode' user for subsequent commands and the default shell
USER $USERNAME

# Set the working directory for your project inside the Codespace
WORKDIR /workspaces/${CODESPACE_NAME}

# Command to keep the container running
CMD ["bash"]
