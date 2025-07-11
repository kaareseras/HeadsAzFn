import ast
from datetime import datetime
import azure.functions as func
import logging
from connector import Connector
from login import login
from watermark import get_watermark
from listdates import listdates
from get_chargeowners import load_chargeowners
from insert_charges import insert_charge
from models import Watermark, ChargeOwner, Charge
from aiohttp import ClientSession
from insert_tax_tarrifs import insert_tax_and_tarif
from spotprice import insert_spotprices
import os
from dotenv import load_dotenv



load_dotenv()

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise ValueError("BASEURL environment variable is not set. Please check your .env file.")

print(f"BASE_URL: {BASE_URL}")


INSERT_CHARGE_SW = True
INSERT_SYSTEM_TARIFF_AND_TAX_SW = True
INSERT_SPORTPICE_SW = True

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

async def data_get_load() -> None:
    logging.info('Python HTTP trigger function processed a request.')

    # Attempt to log in and retrieve the token
    token = await login()

    if not token:
        return func.HttpResponse(
            "Login failed. Please check your credentials.",
            status_code=401
        )
    logging.info(f"Token received")

    # Attempt to retrieve the watermark using the token
    logging.info(f"Retrieving watermark with token: {token}")

    watermark = await get_watermark(token)

    if not watermark:
        return func.HttpResponse(
            "Failed to retrieve watermark.",
            status_code=500
        )
    
    if INSERT_CHARGE_SW:

        # Get Chargeowners
        chargeowners = await load_chargeowners(token)

        if not chargeowners:
            return func.HttpResponse(
                "Failed to retrieve charge owners.",
                status_code=500
            )


        charges_date = listdates(watermark.charges_max_date)

        #Get and insert Charges
        if charges_date:
            async with ClientSession() as session:
                connector = Connector(session)
                for _date in charges_date:
                    logging.info(f"Next charge date: {_date}")
                    for chargeowner in chargeowners:
                        parsed_list = ast.literal_eval(chargeowner.chargetypecode)
                        for chargetypecode in parsed_list:
                            logging.info(f"Charge Owner: {chargeowner.glnnumber}, Company: {chargeowner.compagny}, Charge Type: {chargeowner.chargetype}")
                            charge = await connector.async_get_tariffs(chargeowner, chargetypecode, _date)
                            logging.info(f"Charges for {chargeowner.glnnumber} on {_date}: {charge}")
                            if charge:                     
                                await insert_charge(charge, chargeowner, token)
                                await asyncio.sleep(0.5)
    
    if INSERT_SYSTEM_TARIFF_AND_TAX_SW:
        system_tariffs_date = listdates(watermark.taxes_max_date)
        async with ClientSession() as session:
            connector = Connector(session)
            for _date in system_tariffs_date:
                await insert_tax_and_tarif(token, _date, connector)
    
    if INSERT_SPORTPICE_SW:
        spotprices_date = listdates(watermark.spotprices_max_date)
        for _date in spotprices_date:
            logging.info(f"Next spot price date: {_date}")
            await insert_spotprices(_date, token)
        
                
    return func.HttpResponse(f"Token: {watermark}, This HTTP triggered function executed successfully.")

import asyncio

if __name__ == "__main__":
    asyncio.run(data_get_load())
