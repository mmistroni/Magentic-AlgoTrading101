import google.cloud.logging

# Initialize the client
client = google.cloud.logging.Client()
logger = client.logger("tfl-manual-test")

# The string MUST match what you put in your Alert Query
test_message = "TFL_NOTIFICATION: Testing my new phone alert system!"

print("Sending test log...")
logger.log_text(test_message, severity="INFO")
print("Done. Check your phone in 1-2 minutes.")