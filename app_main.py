import ast
from datetime import datetime, timedelta
import azure.functions as func
import logging
from connector import Connector
from latest_tarif import get_latest_tarif
from latest_tax import get_latest_tax
from login import login
from watermark import get_watermark
from listdates import listdates
from get_chargeowners_with_charge import load_chargeowners_with_last_charge
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
INSERT_SPORTPICE_SW = False

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

FUTURE_DATE = datetime(9999, 12, 31, 23, 59, 59)

def do_continue(_date: datetime) -> bool:
    """ Check if the date is in the future or today.
    """
    today = datetime.now()
    if _date < today or _date == FUTURE_DATE:
        return True
    return False

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

        async with ClientSession() as session:
            connector = Connector(session)

            # Get Chargeowners with thir lates charge and see # if they have valid_from and valid_to dates
            chargeowners_with_latest_charges = await load_chargeowners_with_last_charge(token)

            for chargeowner in chargeowners_with_latest_charges:
                if not chargeowner.valid_from:
                    #Fecting first available charge for the chargeowner
                    charge = await connector.async_get_tariffs(chargeowner, chargeowner.chargetypecode,True)
                    tariff = charge['tariffs']
                    logging.info(f"Got charges for {chargeowner.glnnumber}: {charge}")
                    chargeowner.valid_from = tariff['ValidFrom']
                    chargeowner.valid_to = tariff['ValidTo']
                    chargeowner.is_checked = True
                    logging.info(f"Inserting charge for {chargeowner.glnnumber} with valid from {chargeowner.valid_from} to {chargeowner.valid_to}")
                    await insert_charge(charge, chargeowner, token)
                

            # Iterate over chargeowners with their latest charges and check if newer values are available
            # If valid_to is FUTURE_DATE, then we need to check if there are new charges available
            # If valid_to is not FUTURE_DATE, then we need to check if there are new charges available from valid_to date
            for chargeowner in chargeowners_with_latest_charges:

                _date = datetime.fromisoformat(chargeowner.valid_to)
                while do_continue(_date):
                    logging.info(f"Next charge date: {_date}")
                    if chargeowner.valid_to == FUTURE_DATE and chargeowner.is_checked:
                        logging.info(f"Charge owner {chargeowner.glnnumber} is already checked and valid to future date, skipping.")
                        break
                    elif chargeowner.valid_to == FUTURE_DATE and not chargeowner.is_checked:
                        logging.info(f"Charge owner {chargeowner.glnnumber} is not checked, checking for new charges.")
                        date_str = _date.strftime("%Y-%m-%d")
                        charge = await connector.async_get_tariffs(chargeowner, chargeowner.chargetypecode,False, date_str)
                        tariff = charge['tariffs']
                        if tariff['ValidFrom'] != chargeowner.valid_from:
                            chargeowner.valid_from = tariff['ValidFrom']
                            chargeowner.valid_to = tariff['ValidTo']
                            chargeowner.is_checked = True
                            logging.info(f"Inserting charge for {chargeowner.glnnumber} with valid from {chargeowner.valid_from} to {chargeowner.valid_to}")
                            await insert_charge(charge, chargeowner, token)
                            if chargeowner.valid_to is not None:
                                _date = datetime.fromisoformat(chargeowner.valid_to)
                        else:
                            logging.info(f"Charge for {chargeowner.glnnumber} is already valid from {chargeowner.valid_from} to {chargeowner.valid_to}, skipping.")
                            break
                    else:
                        logging.info(f"Charge owner {chargeowner.glnnumber} is less than {_date}, checking for new charges.")
                        charge = await connector.async_get_tariffs(chargeowner, chargeowner.chargetypecode,False, _date)
                        tariff = charge['tariffs']
                        if not tariff:
                            logging.info(f"No charges found for {chargeowner.glnnumber} on {_date}, skipping.")
                            break
                        chargeowner.valid_from = tariff['ValidFrom']
                        chargeowner.valid_to = tariff['ValidTo']
                        chargeowner.is_checked = True
                        logging.info(f"Inserting charge for {chargeowner.glnnumber} with valid from {chargeowner.valid_from} to {chargeowner.valid_to}")
                        await insert_charge(charge, chargeowner, token)
                        if chargeowner.valid_to is None:
                            logging.info(f"Charge owner {chargeowner.glnnumber} has no valid to date, setting to future date.")
                            chargeowner.valid_to = FUTURE_DATE.isoformat()
                        if _date == datetime.fromisoformat(chargeowner.valid_to):
                            logging.info(f"Charge owner {chargeowner.glnnumber} is fully updated to EDS {_date}, skipping.")
                            break
                        _date = datetime.fromisoformat(chargeowner.valid_to)
                        
                        




    if INSERT_SYSTEM_TARIFF_AND_TAX_SW:
        latest_tarif_valid_to, latest_tax_valid_to, qdate, is_default = await get_latest_date(token)

        first_default = is_default

        while qdate < datetime.now():
            async with ClientSession() as session:
                logging.info(f"Latest tarif is valid until {latest_tarif_valid_to}")
                logging.info(f"Latest tax is valid until {latest_tax_valid_to}")
                logging.info(f"inserting system tariff and tax.")
                connector = Connector(session)
                await insert_tax_and_tarif(token, latest_tarif_valid_to, connector)
                logging.info(f"System tariff and tax inserted successfully.")
                latest_tarif_valid_to, latest_tax_valid_to, qdate, is_default = await get_latest_date(token)
                if first_default and is_default:
                    logging.info(f"Default date used for tarif and tax: {qdate}")
                    break


    if INSERT_SPORTPICE_SW:
        spotprices_date = listdates(watermark.spotprices_max_date)
        for _date in spotprices_date:
            logging.info(f"Next spot price date: {_date}")
            await insert_spotprices(_date, token)
        
                
    return func.HttpResponse(f"Token: {watermark}, This HTTP triggered function executed successfully.")

async def get_latest_date(token):
    latest_tarif_db = await get_latest_tarif(token)
    latest_tax_db = await get_latest_tax(token)

        # Convert valid_to to datetime if it's a string
    latest_tarif_valid_to = latest_tarif_db.valid_to
    latest_tax_valid_to = latest_tax_db.valid_to

    if isinstance(latest_tarif_valid_to, str):
        latest_tarif_valid_to = datetime.fromisoformat(latest_tarif_valid_to)
    if isinstance(latest_tax_valid_to, str):
        latest_tax_valid_to = datetime.fromisoformat(latest_tax_valid_to)

    qdate = min(latest_tarif_valid_to, latest_tax_valid_to)
    is_default = False

    if qdate == datetime(9999, 12, 31, 23, 59, 59):
        qdate = datetime.now() - timedelta(days=1)
        is_default = True
    return latest_tarif_valid_to,latest_tax_valid_to,qdate,is_default

import asyncio

if __name__ == "__main__":
    asyncio.run(data_get_load())
