import ast
from asyncio.log import logger
from dataclasses import asdict
import json
from dotenv import load_dotenv
import requests
from login import login
from connector import Connector
from models import ChargeOwner, Charge, Tarif, Tax
import os
import asyncio
from aiohttp import ClientSession
from datetime import datetime, timedelta

from logging import getLogger
import logging
import sys
load_dotenv()

_logger = getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Helper to convert dataclass (with datetime) to JSON-safe dict
def serialize_dataclass(obj):
    def convert(value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    return {k: convert(v) for k, v in asdict(obj).items()}


# Use a far future date as a default
FUTURE_DATE = datetime(9999, 12, 31, 23, 59, 59)

def safe_parse_date(date_str, default):
    try:
        return datetime.fromisoformat(date_str)
    except (TypeError, ValueError):
        return default


_logger = getLogger(__name__)

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise ValueError("BASEURL environment variable is not set. Please check your .env file.")


def insert_tax(token, tax):
    """
    Send the tax and tarif to the server.
    """
    url = f"{BASE_URL}/tax"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
        # Convert Charge object to JSON-serializable dict
    tax_payload = serialize_dataclass(tax)
    response = requests.post(url, headers=headers, json=tax_payload)
    if response.status_code == 200:
        _logger.info("Tax sent successfully.")
    else:
        _logger.error(f"Failed to send tax: {response.status_code} - {response.text}")

def insert_tarif(token, tarif):
    """
    Send the tarif to the server.
    """
    url = f"{BASE_URL}/tarif"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    tarif_payload = serialize_dataclass(tarif)
    response = requests.post(url, headers=headers, json=tarif_payload)
    if response.status_code == 200:
        _logger.info("Tarif sent successfully.")
    else:
        _logger.error(f"Failed to send tarif: {response.status_code} - {response.text}")

async def insert_tax_and_tarif(token, tax_date: datetime, connector: Connector):
    token = token
    tax_tariffs = await connector.async_get_system_tariffs(tax_date)

    for tarrif in tax_tariffs:
        _logger.info(f"Processing tariff: {tarrif}")

        if tarrif.get("Note") == "Elafgift":
            # Convert the tariff to a Tax object
            tax = Tax(
                valid_from=datetime.fromisoformat(tarrif['ValidFrom']),
                valid_to=safe_parse_date(tarrif['ValidTo'], FUTURE_DATE),
                taxammount=tarrif.get("Price", 0.0),
                includingVAT=False
            )
            _logger.info(f"Tax to be inserted: {tax}")
            insert_tax(token, tax)
        elif tarrif.get("Note") == "Systemtarif":
            # Convert the tariff to a Tax object
            Systemtarif = Tarif(
                valid_from=datetime.fromisoformat(tarrif['ValidFrom']),
                valid_to=safe_parse_date(tarrif['ValidTo'], FUTURE_DATE),
                systemtarif=tarrif.get("Price", 0.0),
                nettarif= 0.0,
                includingVAT=False
            )

        elif tarrif.get("Note") == "Transmissions nettarif":
            # Convert the tariff to a Tax object
            nettarif = Tarif(
                valid_from=datetime.fromisoformat(tarrif['ValidFrom']),
                valid_to=safe_parse_date(tarrif['ValidTo'], FUTURE_DATE),
                systemtarif=0.0,
                nettarif=tarrif.get("Price", 0.0),
                includingVAT=False
            )

    _tarif = Tarif(
        valid_from=nettarif.valid_from,
        valid_to=nettarif.valid_to,
        systemtarif=Systemtarif.systemtarif,
        nettarif=nettarif.nettarif,
        includingVAT=False
    )
    
    _logger.info(f"Tariff to be inserted: {_tarif}")

    # Insert the tariff into the database
    insert_tarif(token, _tarif)


