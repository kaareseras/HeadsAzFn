import httpx
import asyncio
from dotenv import load_dotenv
import os
from models import Tarif, Tax

load_dotenv()

BASE_URL = os.getenv("BASE_URL")

async def get_latest_tax(token: str) -> Tax | None:


    url = f"{BASE_URL}/tax/latest"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            print("Tax retrieved successfully!")

            data = response.json()
            print(f"Tax data: {data}")

            my_tax  = Tax(
                valid_from=data.get("valid_from"),
                valid_to=data.get("valid_to"),
                taxammount=data.get("taxammount"),
                includingVAT=data.get("includingVAT")
            )

            return my_tax
        except httpx.HTTPStatusError as e:
            print(f"Tax retrieval failed: {e}")
            print("Response content:", e.response.text)
            return None