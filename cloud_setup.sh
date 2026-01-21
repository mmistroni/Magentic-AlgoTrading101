#!/bin/bash
set -e  # Exit on error

echo "🚀 Starting Cloud Code environment setup..."

# 1. Install System Dependencies (from your Dockerfile + OS fix)
# Explicitly uses libasound2t64 for newer Cloud Shell environments
sudo apt-get update && sudo apt-get install -y \
    libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libxshmfence1 libasound2t64 libnss3

# 2. Install 'uv' (Correcting the Cloud Shell path issues)
# The installer places uv in ~/.local/bin, not ~/.cargo/bin
curl -LsSf https://astral.sh/uv/install.sh | sh

# FIX: Prepend uv to PATH to resolve "shadowed by other commands" warning
# This ensures your new uv is used instead of pre-installed system versions
export PATH="$HOME/.local/bin:$PATH"

# 3. Git Configuration (Local to this environment)
# Prevents prompt for identity during your 'feature agent' work tomorrow
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
# Setup a global ignore for .vscode to keep your repo clean
git config --global core.excludesfile ~/.gitignore_global
echo ".vscode/" >> ~/.gitignore_global

# 4. Setup Virtual Environment (Replicating your devcontainer postCreateCommand)
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment with uv..."
    uv venv .venv
    source .venv/bin/activate
    
    echo "📥 Installing dependencies from requirements.txt..."
    uv pip install -r requirements.txt
    
    # Install ipykernel as requested in your devcontainer.json
    echo "📓 Configuring Jupyter Kernel..."
    python -m ipykernel install --user --name=magentic_algo_venv --display-name "Magentic Algo VEnv"
fi

echo "✅ Cloud Code Environment Ready!"
echo "💡 Tip: Run 'source .venv/bin/activate' to start working."