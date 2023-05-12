import json
import os
import uuid
import time
import tempfile
from flask import Flask, jsonify, request
from flask_cors import CORS
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
import requests

MONITOR_URL = "http://monitor:5001/check-balance"

vision_key = os.environ.get("VISION_KEY")
if vision_key is None:
    raise Exception("Translate API Key not defined")

translate_key = os.environ.get("TRANSLATE_KEY")
if translate_key is None:
    raise Exception("Translate API Key not defined")

credentials = CognitiveServicesCredentials(vision_key)

endpoint = "https://cic-fhnw.cognitiveservices.azure.com/"

translate_endpoint = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=en&to=ca"

client = ComputerVisionClient(endpoint=endpoint, credentials=credentials)

app = Flask(__name__)
app.secret_key = "secret"
CORS(app)


@app.before_request
def check_balance():
    response = requests.get(MONITOR_URL)
    within_balance_limit = response.json()["within_balance_limit"]
    if not within_balance_limit:
        return jsonify({"error": "Balance exceeded. Too many requests"}), 429


@app.route("/translate/image", methods=["POST"])
def hello_world():
    if request.args.get("mock") is not None:
        return jsonify({"status": "SUCCESS", "message": "This is a mock response"}), 200

    if "image" not in request.files:
        return jsonify({"status": "FILE_NOT_SET", "message": "No image was sent"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"status": "FILE_NOT_SET", "message": "No image was sent"}), 400

    with tempfile.NamedTemporaryFile() as tmp_file:
        file.save(tmp_file.name)
        tmp_file.seek(0)
        read_response = client.read_in_stream(tmp_file, language="en", raw=True)

    # Get ID from returned headers
    operation_id = read_response.headers["Operation-Location"].split("/")[-1]

    result = client.get_read_result(operation_id)

    while result.status in [
        OperationStatusCodes.running,
        OperationStatusCodes.not_started,
    ]:
        time.sleep(1)
        result = client.get_read_result(operation_id)

    if result.status != OperationStatusCodes.succeeded:
        raise Exception("Could't complete the operation")

    full_text = ""
    for page in result.analyze_result.read_results:
        for line in page.lines:
            full_text += line.text + "\n"

    full_text = "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness ..."

    headers = {
        "Ocp-Apim-Subscription-Key": translate_key,
        "Ocp-Apim-Subscription-Region": "westeurope",
        "Content-type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }

    res = requests.post(translate_endpoint, headers=headers, json=[{"text": full_text}])
    translated_text = res.json()[0]["translations"][0]["text"]

    return jsonify({"status": "SUCCESS", "message": translated_text})
