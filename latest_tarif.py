import httpx
import asyncio
from dotenv import load_dotenv
import os
from models import Tarif

load_dotenv()

BASE_URL = os.getenv("BASE_URL")

async def get_latest_tarif(token: str) -> Tarif | None:


    url = f"{BASE_URL}/tarif/latest"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            print("Tarif retrieved successfully!")

            data = response.json()
            print(f"Tarif data: {data}")

            my_tarif = Tarif(
                valid_from=data.get("valid_from"),
                valid_to=data.get("valid_to"),
                nettarif=data.get("nettarif"),
                systemtarif=data.get("systemtarif"),
                includingVAT=data.get("includingVAT")
            )

            return my_tarif
        except httpx.HTTPStatusError as e:
            print(f"Tarif retrieval failed: {e}")
            print("Response content:", e.response.text)
            return None