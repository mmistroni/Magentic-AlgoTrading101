#!/bin/bash
# 1. Install System Dependencies (from your Dockerfile)
sudo apt-get update && sudo apt-get install -y \
    libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libxshmfence1

# 2. Install 'uv' (from your Dockerfile stage 1)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# 3. Setup Virtual Environment (from your devcontainer postCreateCommand)
if [ ! -d ".venv" ]; then
    uv venv .venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
    # Install ipykernel as requested in your devcontainer.json
    python -m ipykernel install --user --name=magentic_algo_venv --display-name "Magentic Algo VEnv"
fi

echo "✅ Cloud Code Environment Ready!"s