from pydantic import BaseModel, field_validator
import re
# Your tool would then look like this:
from twilio.rest import Client
import os

# Your credentials (store these in your Codespace .env!)
account_sid = os.environ['TWILIO_SID']
auth_token = os.environ['TWILIO_TOKEN']
client = Client(account_sid, auth_token)



class NotificationRequest(BaseModel):
    phone_number: str
    message: str

    @field_validator('phone_number')
    @classmethod
    def format_to_e164(cls, v: str) -> str:
        # Remove all non-numeric characters except '+'
        clean_v = re.sub(r'[^\d+]', '', v)
        
        # If it starts with 07 (standard UK), replace 0 with +44
        if clean_v.startswith('07'):
            return '+44' + clean_v[1:]
        
        # Ensure it starts with + if it's already got the country code
        if not clean_v.startswith('+'):
            return '+' + clean_v
            
        return clean_v


def send_whatsapp_update(message_body: str, to_number: str):
    # For WhatsApp, Twilio requires the 'whatsapp:' prefix
    # Your 'from_' number is usually a Twilio Sandbox number for testing
    message = client.messages.create(
        from_='whatsapp:+14155238886', # Twilio Sandbox Number
        body=message_body,
        to=f'whatsapp:{to_number}'
    )
    return f"Message sent! SID: {message.sid}"