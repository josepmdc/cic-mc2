import os
import uuid
import time
import tempfile
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

MONITOR_ENDPOINT = "http://monitor:5001/check-balance"
CV_ENDPOINT = "https://cic-fhnw.cognitiveservices.azure.com/"
TRANSLATE_ENDPOINT = (
    "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0"
)

vision_key = os.environ.get("VISION_KEY")
if vision_key is None:
    raise Exception("Translate API Key not defined")

translate_key = os.environ.get("TRANSLATE_KEY")
if translate_key is None:
    raise Exception("Translate API Key not defined")

client = ComputerVisionClient(
    endpoint=CV_ENDPOINT, credentials=CognitiveServicesCredentials(vision_key)
)

app = Flask(__name__)
app.secret_key = "secret"
CORS(app)


@app.before_request
def check_balance():
    if request.args.get("mock") is not None:
        return jsonify({"status": "SUCCESS", "message": "This is a mock response"}), 200

    response = requests.get(MONITOR_ENDPOINT)
    within_balance_limit = response.json()["within_balance_limit"]
    if not within_balance_limit:
        return jsonify({"error": "Balance exceeded. Too many requests"}), 429


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "SUCCESS", "message": "Pong"})


@app.route("/translate/image", methods=["POST"])
def translate_image():
    if "image" not in request.files:
        return jsonify({"status": "FILE_NOT_SET", "message": "No image was sent"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"status": "FILE_NOT_SET", "message": "No image was sent"}), 400

    input_lang = (
        request.form.get("input_lang")
        if request.form.get("input_lang") is not None
        else "en"
    )
    output_lang = (
        request.form.get("output_lang")
        if request.form.get("output_lang") is not None
        else "en"
    )

    with tempfile.NamedTemporaryFile() as tmp_file:
        file.save(tmp_file.name)
        tmp_file.seek(0)
        read_response = client.read_in_stream(tmp_file, language=input_lang, raw=True)

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
            full_text += line.text

    headers = {
        "Ocp-Apim-Subscription-Key": translate_key,
        "Ocp-Apim-Subscription-Region": "westeurope",
        "Content-type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }

    endpoint = TRANSLATE_ENDPOINT + "&from=" + input_lang + "&to=" + output_lang
    res = requests.post(endpoint, headers=headers, json=[{"text": full_text}])
    translated_text = res.json()[0]["translations"][0]["text"]

    return jsonify({"status": "SUCCESS", "message": translated_text})


@app.route("/translate/text", methods=["POST"])
def translate_text():
    if request.args.get("mock") is not None:
        return jsonify({"status": "SUCCESS", "message": "This is a mock response"}), 200

    input_lang = (
        request.form.get("input_lang")
        if request.form.get("input_lang") is not None
        else "en"
    )
    output_lang = (
        request.form.get("output_lang")
        if request.form.get("output_lang") is not None
        else "en"
    )

    if request.form.get("text") is None:
        return (
            jsonify({"status": "INVALID_REQUEST", "message": "No message was sent"}),
            400,
        )

    text = request.form.get("text")

    headers = {
        "Ocp-Apim-Subscription-Key": translate_key,
        "Ocp-Apim-Subscription-Region": "westeurope",
        "Content-type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4()),
    }

    endpoint = TRANSLATE_ENDPOINT + "&from=" + input_lang + "&to=" + output_lang
    res = requests.post(endpoint, headers=headers, json=[{"text": text}])
    translated_text = res.json()[0]["translations"][0]["text"]

    return jsonify({"status": "SUCCESS", "message": translated_text})
