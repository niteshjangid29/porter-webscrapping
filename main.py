from fastapi import FastAPI, HTTPException
from selenium.common.exceptions import TimeoutException, WebDriverException

from app import scrape_h2_heading

app = FastAPI(
    title="Porter Scraper API",
    description="An API to scrape delivery quotes from Porter.in using Selenium.",
    version="1.0.0",
)


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