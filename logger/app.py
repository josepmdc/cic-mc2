import os
import time
import uuid
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from azure.cosmos import CosmosClient, PartitionKey

ENDPOINTS = [
    "http://monitor:5001/ping",
    "http://api:5000/ping",
]

COSMOS_ENDPOINT = "https://cic.documents.azure.com:443/"
COSMOS_KEY = os.environ["COSMOS_KEY"]

DATABASE_NAME = "monitor"
CONTAINER_NAME = "logs"


class LoggerService:
    def __init__(self) -> None:
        self.client = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
        self.database = self.client.create_database_if_not_exists(id=DATABASE_NAME)
        self.container = self.database.create_container_if_not_exists(
            id=CONTAINER_NAME,
            partition_key=PartitionKey(path="/timestamp"),
            offer_throughput=400,
        )

    def log_request(self, endpoint, status_code, response_time):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.container.create_item(
            {
                "id": str(uuid.uuid4()),
                "timestamp": timestamp,
                "endpoint": endpoint,
                "status_code": status_code,
                "response_time": response_time,
            }
        )

    def ping_endpoints(self):
        for endpoint in ENDPOINTS:
            try:
                start_time = time.time()
                response = requests.get(endpoint)
                response_time = round((time.time() - start_time) * 1000, 2)
                self.log_request(endpoint, response.status_code, response_time)
            except requests.exceptions.RequestException as e:
                response_time = -1
                self.log_request(endpoint, "ERROR: " + str(e), response_time)


service = LoggerService()

scheduler = BlockingScheduler()
scheduler.add_job(service.ping_endpoints, "interval", seconds=5)
scheduler.start()
