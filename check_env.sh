#!/bin/bash

# --- 1. API Key Check ---
echo "🔍 Checking API Keys..."
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ ERROR: GOOGLE_API_KEY is not set."
else
    echo "✅ GOOGLE_API_KEY is present."
fi

if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "⚠️  WARNING: GOOGLE_CLOUD_PROJECT is not set (Optional for Google AI, required for Vertex AI)."
else
    echo "✅ Project ID: $GOOGLE_CLOUD_PROJECT"
fi

# --- 2. Python & Virtual Env Check ---
echo -e "\n🔍 Checking Python Environment..."
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  WARNING: You are NOT in a virtual environment."
else
    echo "✅ Active Environment: $VIRTUAL_ENV"
fi

# --- 3. Playwright & Browser Check ---
echo -e "\n🔍 Checking Playwright Dependencies..."
if command -v playwright &> /dev/null; then
    echo "✅ Playwright command found."
    # Check if chromium is actually installed
    if playwright install --help | grep -q "chromium"; then
        echo "✅ Playwright CLI ready."
    fi
else
    echo "❌ ERROR: Playwright is not installed in the current PATH."
fi

# --- 4. Linux System Library Check (The "Cloud Shell Trap") ---
echo -e "\n🔍 Checking Linux System Libraries (for crawl4ai)..."
MISSING_LIBS=0
for lib in libnss3 libatk1.0-0 libasound2t64 libgbm1; do
    if dpkg -s $lib &> /dev/null; then
        echo "✅ $lib is installed."
    else
        echo "❌ MISSING: $lib"
        MISSING_LIBS=$((MISSING_LIBS + 1))
    fi
done

if [ $MISSING_LIBS -gt 0 ]; then
    echo -e "\n💡 FIX: Run 'sudo playwright install-deps' using the full path to your venv playwright."
fi

echo -e "\n--- Environment Check Complete ---"