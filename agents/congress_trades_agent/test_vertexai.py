from google import genai

# Initialize client using Vertex AI backend
client = genai.Client(
    vertexai=True,
    #enterprise=True,
    project="datascience-projects",
    location="global"
)

print('----- checking all models....')
for model in client.models.list():
    print(model.name)



# Test with standard Vertex AI Flash model endpoint
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Hello! Confirm connection to Vertex AI."
)

print("Response:", response.text)