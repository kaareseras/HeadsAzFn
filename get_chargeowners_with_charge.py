import httpx
from dotenv import load_dotenv
import os
import logging
from models import ChargeownerLatestCharge

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

load_dotenv()

BASE_URL = os.getenv("BASE_URL")


async def load_chargeowners_with_last_charge(token) -> list[ChargeownerLatestCharge] | None:
    """Load charge owners from the CHARGEOWNERS dictionary."""

    url = f"{BASE_URL}/chargeowner/with-latest-charge"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    chargeowners = []

    try:
        response.raise_for_status()  # Raises an HTTPStatusError for bad responses
        if response.status_code == 200:          
            for _chargeowner in response.json():
                _logger.info(f"Loaded charge owner: {_chargeowner}")

                chargeowner = ChargeownerLatestCharge(
                    id=_chargeowner.get("id"),
                    glnnumber=_chargeowner.get("glnnumber"),
                    compagny=_chargeowner.get("compagny"),
                    chargetype=_chargeowner.get("chargetype"),
                    chargetypecode=_chargeowner.get("chargetypecode", None),
                    valid_from=_chargeowner.get("valid_from", None),
                    valid_to=_chargeowner.get("valid_to", None),
                )

                chargeowners.append(chargeowner)
            return chargeowners
    except httpx.HTTPStatusError as e:
        print(f"Charges retrieval failed: {e}")
        print("Response content:", e.response.text)
        _logger.error(f"Failed to load charge owners: {response.status_code} {response.text}")
        return None
