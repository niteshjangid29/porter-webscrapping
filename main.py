from fastapi import FastAPI, HTTPException
from selenium.common.exceptions import TimeoutException, WebDriverException
from typing import Literal
from pydantic import BaseModel, Field

from porter_api.app import scrape_h2_heading
from porter_api.core import PorterAPI
from porter_api.exceptions import PorterAPIError

app = FastAPI(
    title="Porter Scraper API",
    description="An API to scrape delivery quotes from Porter.in using Selenium.",
    version="1.0.0",
)


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