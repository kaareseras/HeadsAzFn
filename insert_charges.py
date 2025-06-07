from dataclasses import asdict
from datetime import datetime, timedelta
import os

from dotenv import load_dotenv
from models import Charge
import requests

load_dotenv()

# Use a far future date as a default
FUTURE_DATE = datetime(9999, 12, 31, 23, 59, 59)

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise ValueError("BASEURL environment variable is not set. Please check your .env file.")


def safe_parse_date(value, default=None):
    if value is None:
        return default
    return datetime.fromisoformat(value)
    
    # Helper to convert dataclass (with datetime) to JSON-safe dict
def serialize_dataclass(obj):
    def convert(value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value
    return {k: convert(v) for k, v in asdict(obj).items()}

async def insert_charge(tariff, owner, token):
    """Insert the tariff into the database."""
    # Implement your logic to insert the tariff into the database
    # For example, you can use an ORM or raw SQL to insert the tariff
    # Return True if the insert was successful  , False otherwise


    tariffs = tariff['tariffs']
    charge = Charge(
        chargeowner_id=owner.id,
        charge_type=tariffs['ChargeType'],
        charge_type_code=tariffs['ChargeTypeCode'],
        note=tariffs['Note'],
        description=tariffs['Description'],
        valid_from = safe_parse_date(tariffs['ValidFrom']),
        valid_to = safe_parse_date(tariffs.get('ValidTo'), FUTURE_DATE),
        **{f'price{i}': tariffs.get(f'price{i-1}', 0.0) for i in range(1, 25)}
    )

    # Convert Charge object to JSON-serializable dict
    charge_payload = serialize_dataclass(charge)

    print (f"Inserting charge: {charge_payload}")

    # Send POST request
    url = f"{BASE_URL}/charge"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json=charge_payload)

    # Optional: check response
    if response.ok:
        print("Charge submitted successfully.")
    else:
        print(f"Error: {response.status_code} - {response.text}")