import os
import uuid
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from azure.cosmos import CosmosClient, PartitionKey

COSMOS_ENDPOINT = "https://cic.documents.azure.com:443/"
COSMOS_KEY = os.environ["COSMOS_KEY"]

DATABASE_NAME = "monitor"
CONTAINER_NAME = "requests"
USAGE_LIMIT = 300


class MonitorService:
    def __init__(self):
        self.client = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
        self.database = self.client.create_database_if_not_exists(id=DATABASE_NAME)
        self.container = self.database.create_container_if_not_exists(
            id=CONTAINER_NAME,
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400,
        )

    def is_within_balance_limit(self):
        count = self.container.query_items(
            query="SELECT VALUE COUNT(1) FROM requests c",
            enable_cross_partition_query=True,
        ).next()

        if count >= USAGE_LIMIT:
            return False

        self.container.create_item(
            {
                "id": str(uuid.uuid4()),
                "timestamp": str(datetime.now()),
            }
        )

        return True


service = MonitorService()

app = Flask(__name__)
app.secret_key = "secret"
CORS(app)


@app.route("/check-balance", methods=["GET"])
def check_balance():
    return jsonify({"within_balance_limit": service.is_within_balance_limit()})


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "SUCCESS", "message": "Pong"})
