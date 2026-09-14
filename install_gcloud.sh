#!/usr/bin/bash
set -e

echo "🚀 Installing Google Cloud SDK into user home directory..."

INSTALL_DIR="$HOME/.google-cloud-sdk"

# 1. Clean up old installation directory if present
if [ -d "$INSTALL_DIR" ]; then
    echo "🧹 Removing previous installation at $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
fi

# 2. Download installer script locally
curl -sSL https://sdk.cloud.google.com -o /tmp/install_google_sdk.sh

# 3. Execute installation script directly with target parameters
bash /tmp/install_google_sdk.sh --install-dir="$INSTALL_DIR" --disable-prompts

# 4. Clean up downloaded script
rm -f /tmp/install_google_sdk.sh

# 5. Export binary PATH to active environment & .bashrc
SDK_BIN="$INSTALL_DIR/google-cloud-sdk/bin"

if ! grep -q "$SDK_BIN" ~/.bashrc; then
    echo "export PATH=\$PATH:$SDK_BIN" >> ~/.bashrc
fi

export PATH=$PATH:$SDK_BIN

# 6. Verify installation
echo "✅ Installation complete!"
which gcloud
gcloud --version