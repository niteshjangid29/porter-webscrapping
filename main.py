import os
from fastapi import FastAPI, HTTPException
from selenium.common.exceptions import TimeoutException, WebDriverException
from typing import Literal
from pydantic import BaseModel, Field
import requests
import json
import boto3
import time
import uuid
from botocore.exceptions import ClientError
import threading

from porter_api.app import scrape_h2_heading
from porter_api.core import PorterAPI
from porter_api.exceptions import PorterAPIError

app = FastAPI(
    title="Porter Scraper API",
    description="An API to scrape delivery quotes from Porter.in using Selenium.",
    version="1.0.0",
)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

API_URL = "https://backend.railse.com/porter"

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

        print(f"Quote result for reference_id {reference_id}: {quote_result}")

        if not quote_result.get("success"):
            print(f"   -> Scraping failed for reference_id: {reference_id}. Error: {quote_result.get('error')}")
            # Do not delete the message, let it be re-processed after visibility timeout
            return True
        
        quotes_list = quote_result.get("quotes", [])
        if not quotes_list:
            print(f"  -> No quotes found to save for reference_id: {reference_id}. Marking as complete.")
            return True # Nothing to save, so the message is successfully processed
        
        save_payload = {
            "name": name,
            "phone": phone,
            "pickup_address": pickup_address,
            "drop_address": drop_address,
            "city": city,
            "service_type": service_type,
            "reference_id": reference_id,
            "reference_type": reference_type,
            "quotes": quotes_list
        }

        print(f"  -> Saving {len(quotes_list)} quotes for reference_id: {reference_id}...")

        response = requests.post(f"{API_URL}/save-quote", json=save_payload)

        print("Response = ", response)

        if response.status_code == 200:
            print(f"  -> Successfully processed and saved quotes for reference_id: {reference_id}")
            return True
        else:
            print(f"  -> FAILED to save quotes. Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"An error occurred while processing the message: {e}")
        return False

def poll_sqs_queue():
    """
    The main loop for the SQS consumer. This function will run in a background thread.
    """
    print("SQS Polling thread started...")
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, SQS_QUEUE_URL]):
        print("AWS/SQS environment variables not configured. SQS thread exiting.")
        return

    sqs = boto3.client(
        'sqs',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    while True:
        try:
            receive_attempt_id = str(uuid.uuid4())
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                MessageAttributeNames=['All'],
                ReceiveRequestAttemptId=receive_attempt_id
            )
            messages = response.get('Messages', [])
            if not messages:
                continue

            for message in messages:
                if process_message(message):
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=message['ReceiptHandle']
                    )
        except ClientError as e:
            print(f"A Boto3 client error occurred in SQS thread: {e}")
            time.sleep(10)
        except Exception as e:
            print(f"An unexpected error occurred in SQS thread: {e}")
            time.sleep(20)

# --- FastAPI Startup Event ---

@app.on_event("startup")
async def startup_event():
    """
    On application startup, this function launches the SQS polling
    function in a separate, non-blocking thread.
    """
    print("Application startup...")
    thread = threading.Thread(target=poll_sqs_queue)
    thread.daemon = True  # Allows main thread to exit even if this thread is running
    thread.start()
    print("SQS consumer thread launched in the background.")

class QuoteRequest(BaseModel):
    """Defines the structure for a quote request."""
    name: str = Field(..., example="Amit Shah", description="Your full name.")
    phone: str = Field(..., example="9876543210", description="A valid 10-digit phone number.")
    pickup_address: str = Field(..., example="Koramangala, Bangalore", description="The pickup location address or pincode.")
    drop_address: str = Field(..., example="Indiranagar, Bangalore", description="The drop-off location address or pincode.")
    city: Literal["Bangalore", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Pune"] = Field(..., example="Bangalore")
    service_type: Literal["trucks", "two_wheelers", "packers_and_movers"] = Field(default="trucks", example="trucks")


@app.get("/")
def read_root():
    """A root endpoint to confirm the API is running."""
    return {
        "message": "Welcome to the Porter Scraper API!",
        "status": "ok",
        "usage_docs": "/docs"
    }

@app.get("/test", tags=["Testing"])
def test_endpoint():
    """
    A test endpoint to verify Selenium functionality.
    It calls the scraper function to get the text of the first <h2> element from porter.in.
    """
    try:
        heading_text = scrape_h2_heading()
        return {"heading_text": heading_text}

    except TimeoutException:
        print("Error: Timed out waiting for the h2 element to appear.")
        raise HTTPException(
            status_code=404, 
            detail="Could not find the h2 element on the page within the time limit."
        )
    except WebDriverException as e:
        print(f"WebDriverException: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred with the Selenium WebDriver: {e}"
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred: {e}"
        )


@app.post("/quote", tags=["Scraping"])
async def get_quote_endpoint(request: QuoteRequest):
    """
    Takes pickup and drop details and returns a delivery quote from Porter.in.
    """
    try:
        print(f"Received quote request for {request.name} in {request.city}")
        
        # Initialize the PorterAPI with data from the request.
        # headless=True is essential for running in Docker.
        api = PorterAPI(name=request.name, phone=request.phone, headless=True)

        # Call the get_quote method from your core scraping logic
        quote_result = api.get_quote(
            pickup_address=request.pickup_address,
            drop_address=request.drop_address,
            city=request.city,
            service_type=request.service_type,
        )

        # The scraper returns a dictionary with a 'success' key.
        # We check this to determine the outcome.
        if quote_result.get("success"):
            print(f"Successfully retrieved quotes for {request.name}.")

            # # Calling the /update endpoint to update the quote in the backend.
            # try:
            #     print("Calling the backend API to update the quote...")
            #     response = requests.post(API_URL, json=quote_result)
            #     response.raise_for_status()  # Raise an error for HTTP errors
            # except requests.RequestException as e:
            #     print(f"Error updating quote in backend: {e}")
            #     raise HTTPException(
            #         status_code=500,
            #         detail="Failed to update quote in backend."
            #     )

            return quote_result
        else:
            # If the scrape was not successful, the scraper returns a
            # structured error message which we can pass to the user.
            print(f"Scraping failed: {quote_result.get('error')}")
            raise HTTPException(
                status_code=400, # Bad Request
                detail=quote_result
            )

    except PorterAPIError as e:
        # This catches validation errors, like an invalid phone number.
        print(f"Validation Error: {e}")
        raise HTTPException(status_code=422, detail=str(e)) # Unprocessable Entity
    except Exception as e:
        # This is a catch-all for any other unexpected errors during the process.
        print(f"An unexpected error occurred in /quote endpoint: {e}")
        raise HTTPException(
            status_code=500, # Internal Server Error
            detail=f"An unexpected internal error occurred. Please check the server logs."
        )