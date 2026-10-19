#!/bin/bash
set -e

# Ensure we are in the directory where the script lives
cd "$(dirname "$0")"

echo "🧹 Cleaning up any old virtual environment..."
rm -rf .fmp_venv

echo "🐍 Creating fresh virtual environment (.venv)..."
python3 -m venv .fmp_venv

echo "⬆️ Upgrading core pip tools..."
.fmp_venv/bin/pip install --upgrade pip setuptools wheel

echo "📦 Installing package in editable mode & development dependencies..."
.fmp_venv/bin/pip install -e .
.fmp_venv/bin/pip install -r requirements-dev.txt

echo "✅ Environment setup complete! To activate your virtual environment, run:"
echo "source ingest_fmp/.venv/bin/activate"