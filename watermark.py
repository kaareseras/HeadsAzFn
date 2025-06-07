import httpx
import asyncio
from dotenv import load_dotenv
import os
from models import Watermark

load_dotenv()

BASE_URL = os.getenv("BASE_URL")

async def get_watermark(token: str) -> Watermark | None:


    url = f"{BASE_URL}/watermark"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            print("Watermark retrieved successfully!")

            data = response.json()
            print(f"Watermark data: {data}")

            my_watermark = Watermark(
                spotprices_max_date=data.get("spotprices_max_date"),
                charges_max_date=data.get("charges_max_date"),
                taxes_max_date=data.get("taxes_max_date"),
                tarifs_max_date=data.get("tarifs_max_date")
            )

            return my_watermark
        except httpx.HTTPStatusError as e:
            print(f"Watermark retrieval failed: {e}")
            print("Response content:", e.response.text)
            return None