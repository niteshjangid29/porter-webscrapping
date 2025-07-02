import boto3
import time
import json
from botocore.exceptions import ClientError
from config import Config
import requests

from porter_api.core import PorterAPI
from porter_api.exceptions import PorterAPIError

API_URL = "http://localhost:8080/porter"

def process_message(message: dict):
    print(f"Processing message: {message['MessageId']}")
    try:
        body = json.loads(message['Body'])
        print(f"Message body: {body}")

        name = body.get('name')
        phone = body.get('phone')
        pickup_address = body.get('pickup_address')
        drop_address = body.get('drop_address')
        city = body.get('city')
        service_type = body.get('service_type')
        reference_id = body.get('reference_id')
        reference_type = body.get('reference_type')

        if not all([pickup_address, drop_address, reference_id, reference_type]):
            print("Required fields are missing. Skipping message.")
            return True # Mark as processed to avoid re-queueing a bad message
        
        api = PorterAPI(
            name=name,
            phone=phone,
            headless=True  # Set to True for headless mode, useful for production
        )

        quote_result = api.get_quote(
            pickup_address=pickup_address,
            drop_address=drop_address,
            city=city,
            service_type=service_type,
        )

        if not quote_result.get("success"):
            print(f"   -> Scraping failed for reference_id: {reference_id}. Error: {quote_result.get('error')}")
            # Do not delete the message, let it be re-processed after visibility timeout
            return False
        
        quotes_list = quote_result.get("quotes", [])
        if not quotes_list:
            print(f"  -> No quotes found to save for reference_id: {reference_id}. Marking as complete.")
            return True # Nothing to save, so the message is successfully processed
        
        base_payload = {
            "name": name,
            "phone": phone,
            "pickup_address": pickup_address,
            "drop_address": drop_address,
            "city": city,
            "service_type": service_type,
            "reference_id": reference_id,
            "reference_type": reference_type,
        }

        for quote in quotes_list:
            save_payload = base_payload.copy()
            save_payload['quote'] = quote

            response = requests.post(
                API_URL + "/save-quote", # Using the new endpoint
                json=save_payload
            )

            if response.status_code != 200:
                print(f"  -> FAILED to save quote for {quote.get('vehicle_name')}. Status: {response.status_code}, Response: {response.text}")
                return False # If any quote fails to save, stop and requeue the whole message

        # If the loop completes, all quotes were saved successfully
        print(f"  -> All {len(quotes_list)} quotes saved successfully for reference_id: {reference_id}")
        return True # Signal that the SQS message can be deleted
    except Exception as e:
        print(f"An error occurred while processing the message: {e}")
        return False


def main():

    print("Starting SQS consumer...")

    sqs = boto3.client(
        'sqs',
        region_name = Config.AWS_REGION,
        aws_access_key_id = Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key = Config.AWS_SECRET_ACCESS_KEY
    )

    # Run an CRON job every 2 minutes to poll the SQS queue
    while True:
        try:
            receive_attempt_id = str(int(time.time()))

            response = sqs.receive_message(
                QueueUrl= Config.SQS_QUEUE_URL,
                MaxNumberOfMessages=1,  # Process one message at a time
                WaitTimeSeconds=20,  # Long polling for 20 seconds
                MessageAttributeNames=['All'],
                ReceiveRequestAttemptId=receive_attempt_id                
            )

            messages = response.get('Messages', [])

            if not messages:
                print("No messages in the queue. Waiting for new messages...")
                continue

            for message in messages:
                if process_message(message):
                    print(f"Message processed successfully. Deleting: {message['MessageId']}")
                    sqs.delete_message(
                        QueueUrl=Config.SQS_QUEUE_URL,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                else:
                    print(f"Message processing failed. It will become visible again after timeout: {message['MessageId']}")

        except ClientError as e:
            print(f"A Boto3 client error occurred: {e}")
            time.sleep(10) # Wait before retrying
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            time.sleep(20) # Wait longer for unexpected errors