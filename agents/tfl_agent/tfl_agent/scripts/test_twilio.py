import os
from twilio.rest import Client

client = Client(os.environ['TWILIO_SID'], os.environ['TWILIO_TOKEN'])

# Fetch the last message sent
last_message = client.messages.list(limit=1)[0]

print(f"Status: {last_message.status}")
if last_message.error_code:
    print(f"Error Code: {last_message.error_code}")
    print(f"Error Message: {last_message.error_message}")
else:
    print("No error code reported. Check your WhatsApp 'Archived' or 'Spam' folders.")