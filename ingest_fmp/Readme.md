This project will migrate all existing finviz functionality to leverage
FMP and other public apis

# install gcloud

# 1. Update and install required dependencies
sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates gnupg curl

# 2. Import the Google Cloud public key
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg

# 3. Add the Google Cloud SDK package repository
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list

# 4. Update package lists and install google-cloud-cli
sudo apt-get update && sudo apt-get install -y google-cloud-cli

# Authenticate with your Google account
gcloud auth login

# Set your default project
gcloud config set project datascience-projects