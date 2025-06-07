import azure.functions as func
import logging
from app_main import data_get_load

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="HEADS")
async def HEADS(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    await data_get_load()


    return func.HttpResponse(f"This HTTP triggered function executed successfully.")
