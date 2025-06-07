import httpx
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
USER_NAME = os.getenv("USER_NAME")
PASS_WORD = os.getenv("PASS_WORD")
BASE_URL = os.getenv("BASE_URL")

async def login():


    url = f"{BASE_URL}/auth/login"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    data = {
        "username": USER_NAME,
        "password": PASS_WORD,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, data=data, headers=headers)
            response.raise_for_status()
            print("Login successful!")
            return response.json().get("access_token")
        except httpx.HTTPStatusError as e:
            print(f"Login failed: {e}")
            print("Response content:", e.response.text)
            return None
