import asyncio
from logging import getLogger
import logging
import os
import sys
from dotenv import load_dotenv
import requests
from login import login
from datetime import datetime, timedelta


_logger = getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise ValueError("BASEURL environment variable is not set. Please check your .env file.")



def get_nordpool_spotprices(date = None):
    """
    Fetches the Nord Pool spot prices from the API.
    """
    #date = "2025-05-28"  # Default to a specific date if not provided

    _logger.info(f"Fetching Nord Pool spot prices for date: {date}")
    

    url = f"https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices?currency=DKK&date={date}&market=DayAhead&deliveryArea=DK1,DK2"

    _logger.debug(f"Requesting URL: {url}")

    headers = {}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        _logger.info("Nord Pool spot prices fetched successfully.")
    else:
        _logger.error(f"Failed to fetch Nord Pool spot prices: {response.status_code} - {response.text}")

    return response


def upload(token,prices):
    """
    Uploads the fetched prices to the database.
    """
    _logger.info("Uploading prices to the database...")

    # Here you would implement the logic to upload prices to your database
    # For now, we just log the prices
    _logger.debug(f"Prices: {prices}")

    url = f"{BASE_URL}/spotprice/nordpool"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    tarif_payload = prices
    response = requests.post(url, headers=headers, json=tarif_payload)
    if response.status_code == 200:
        _logger.info("pricedata sent successfully.")
    else:
        _logger.error(f"Failed to send pricedata: {response.status_code} - {response.text}")




async def insert_spotprices(spotdate: datetime, token):
    _logger.info(f"Processing date: {spotdate}")
    prices = get_nordpool_spotprices(spotdate)
    upload(token, prices.json())

