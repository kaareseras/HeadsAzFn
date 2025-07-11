from __future__ import annotations
from aiohttp import ClientSession
from async_retrying_ng import RetryError, retry
from logging import getLogger
from datetime import datetime
from models import ChargeOwner


_LOGGER = getLogger(__name__)

SOURCE_NAME = "Energi Data Service Tariffer"

REGIONS = [
    "DK1",
    "DK2",
    "FIXED",
]

BASE_URL = "https://api.energidataservice.dk/dataset/DatahubPricelist"

__all__ = ["Connector", "REGIONS", "CHARGEOWNERS"]

class Connector:
    """Energi Data Service API."""
    def __init__(
        self, client: ClientSession, chargeowner: ChargeOwner | None = None
    ) -> None:
        """Init API connection to Energi Data Service."""
        self._chargeowner = chargeowner
        self._tariffs = {}
        self._additional_tariff = {}
        self._all_tariffs = {}
        self._all_additional_tariffs = {}
        self.status = 418
        self.client = client

    @property
    def tariffs(self):
        """Return the tariff data."""

        tariffs = {
            "tariffs": self._tariffs,
        }

        return tariffs

    def additional_tariffs(self):
        """Return the additional tariff data."""

        tariffs = {
            "tariffs": self._additional_tariff,
        }

        return tariffs


    @staticmethod
    def _header() -> dict:
        """Create default request header."""
        data = {"Content-Type": "application/json"}
        return data
    
    async def async_get_tariffs(self, chargeowner: ChargeOwner, chargetypecode: str, get_first: bool, date: datetime | None = None) -> dict:
        """Get tariff from Eloverblik API."""

        if date is None:
            _LOGGER.debug("No date provided, using current date for tariff check.")
            check_date = (datetime.utcnow()).strftime("%Y-%m-%d")
        else:
            _LOGGER.debug("Using provided date for tariff check: %s", date)
            check_date = date.strftime("%Y-%m-%d")

        try:
            chargeowner = chargeowner
            
            limit = "limit=2500"
            
            objfilter = 'filter=%7B"chargetypecode": ["{}"],"gln_number": ["{}"],"chargetype": {}%7D'.format(  # pylint: disable=consider-using-f-string
                chargetypecode,
                chargeowner.glnnumber,
                chargeowner.chargetype.replace("'", '"'),
                )
            
            if get_first:
                sort = "sort=ValidFrom asc"
            else:
                sort = "sort=ValidFrom desc"

            query = f"{objfilter}&{sort}&{limit}"
            resp = await self.async_call_api(query)

            if len(resp) == 0:
                _LOGGER.warning(
                    "Could not fetch tariff data from Energi Data Service DataHub!"
                )
                return
            else:
                # We got data from the DataHub - update the dataset

                self._all_tariffs = resp

            if get_first:
                check_date = self._all_tariffs[0]["ValidFrom"].split("T")[0]
                _LOGGER.debug("Using first tariff date: %s", check_date)

            

            tariff_data = {}
            for entry in self._all_tariffs:
                if self.__entry_in_range(entry, check_date):
                    _LOGGER.debug("Found possible dataset: %s", entry)
                    baseprice = 0
                    for key, val in entry.items():
                        if key == "Price1":
                            baseprice = val
                        if "Price" in key:
                            hour = "price" + str(int("".join(filter(str.isdigit, key))) - 1)

                            current_val = val if val is not None else baseprice

                            # if len(tariff_data) == 24:
                            #     current_val += tariff_data[hour]

                            tariff_data.update({hour: current_val})
                        if key == "ValidTo":
                            tariff_data.update({"ValidTo": val})
                        if key == "ValidFrom":
                            tariff_data.update({"ValidFrom": val})
                        if key == "Note":
                            tariff_data.update({"Note": val})
                        if key == "Description":
                            tariff_data.update({"Description": val})
                        if key == "ChargeType":
                            tariff_data.update({"ChargeType": val})
                        if key == "ChargeTypeCode":
                            tariff_data.update({"ChargeTypeCode": val})

                    if len(tariff_data) == 24 + 6:  # 24 hours + 6 additional fields
                        self._tariffs.update(tariff_data)

            return self.tariffs
        except KeyError:
            _LOGGER.error(
                "Error finding '%s' in the list of charge owners - "
                "please reconfigure your integration.",
                self._chargeowner,
            )
        except RetryError:
            _LOGGER.error("Retry attempts exceeded for tariffs request.")

    async def async_get_system_tariffs(self, date: datetime) -> dict:
        """Get additional system tariffs defined by the Danish government."""
        if date is None:
            _LOGGER.debug("No date provided, using current date for tariff check.")
            check_date = (datetime.utcnow()).strftime("%Y-%m-%d")
        else:
            _LOGGER.debug("Using provided date for tariff check: %s", date)
            check_date = date.strftime("%Y-%m-%d")
        

        search_filter = '{"Note":["Elafgift","Systemtarif","Transmissions nettarif"],"GLN_Number":["5790000432752"]}'
        limit = 500

        query = f"filter={search_filter}&limit={limit}"

        try:
            dataset = await self.async_call_api(query)

            if len(dataset) == 0:
                _LOGGER.warning(
                    "Could not fetch tariff data from Energi Data Service DataHub!"
                )
                return
            else:
                self._all_additional_tariffs = dataset

            tariff_data = {}
            tariffs = []
            for entry in self._all_additional_tariffs:
                if self.__entry_in_range(entry, check_date):
                    if entry["Note"] not in tariff_data:
                        tariff = {
                            "Note": entry["Note"],
                            "ValidFrom": entry["ValidFrom"],
                            "ValidTo": entry["ValidTo"],
                            "ChargeType": entry["ChargeType"],
                            "ChargeTypeCode": entry["ChargeTypeCode"],
                            "Description": entry["Description"],
                            "Price": float(entry["Price1"]),
                        }

                        tariffs.append(tariff)

                        tariff_data.update(
                            {entry["Note"]: float(entry["Price1"])}
                        )

            self._additional_tariff = tariff_data
            return tariffs
        except RetryError:
            _LOGGER.error("Retry attempts exceeded for retrieving system tariffs.")

    @retry(attempts=10, delay=10, max_delay=3600, backoff=1.5)
    async def async_call_api(self, query: str) -> dict:
        """Make the API calls."""
        try:
            headers = self._header()
            url = f"{BASE_URL}?{query}"
            resp = await self.client.get(url, headers=headers)
            self.status = resp.status
            resp.raise_for_status()

            if resp.status == 400:
                _LOGGER.error("API returned error 400, Bad Request!")
                return {}
            elif resp.status == 411:
                _LOGGER.error("API returned error 411, Invalid Request!")
                return {}
            elif resp.status == 200:
                res = await resp.json()
                return res["records"]
            else:
                _LOGGER.error("API returned error %s", str(resp.status))
                return {}
        except Exception as exc:
            _LOGGER.error("Error during API request: %s", exc)
            raise
    
    def __entry_in_range(self, entry, check_date) -> bool:
        """Check if an entry is witin the date range."""
        return (entry["ValidFrom"].split("T"))[0] <= check_date and (
            entry["ValidTo"] is None or (entry["ValidTo"].split("T"))[0] > check_date
        )
    

