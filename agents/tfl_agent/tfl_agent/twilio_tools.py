import os
from twilio.rest import Client
import logging

def send_twilio_message(msg:str) -> None  :
    # 1. Setup your credentials (make sure these are in your Codespace env)
    account_sid = os.environ['TWILIO_SID']
    auth_token = os.environ['TWILIO_TOKEN']
    client = Client(account_sid, auth_token)
    logging.info(f'About to send:{msg}')

    # 2. Your details
    # Note: Twilio needs the +44 (UK code) and no leading 0
    my_number = '+447799898928' 
    # This is the Twilio Sandbox number
    twilio_number = 'whatsapp:+14155238886'

    # 3. Send the message
    message = client.messages.create(
        from_=twilio_number,
        body=msg,
        to=f'whatsapp:{my_number}'
    )

    print(f"Success! Message sent. ID: {message.sid}")