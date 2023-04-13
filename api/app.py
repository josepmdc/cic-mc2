import os
import cv2
import time
import urllib
import tempfile
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

key = os.environ.get("API_KEY")
if key is None:
    raise Exception("API Key not defined")

credentials = CognitiveServicesCredentials(key)

client = ComputerVisionClient(
        endpoint="https://cic-fhnw.cognitiveservices.azure.com/",
        credentials=credentials
)

app = Flask(__name__)
app.secret_key = 'secret'
CORS(app)

@app.route("/translate/image", methods = ['POST'])
def hello_world():
    print(request.files)
    if 'image' not in request.files:
        return jsonify({ "status": "FILE_NOT_SET", "message": "No image was sent" }), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({ "status": "FILE_NOT_SET", "message": "No image was sent" }), 400

    with tempfile.NamedTemporaryFile() as tmp_file:
        file.save(tmp_file.name)
        tmp_file.seek(0)

        img = cv2.imread(tmp_file.name)

        # SDK call
        rawHttpResponse = client.read_in_stream(tmp_file, language="en", raw=True)

        # Get ID from returned headers
        operation_id = rawHttpResponse.headers["Operation-Location"].split('/')[-1]

        # Get data
        print("Waiting for response...")

        result = client.get_read_result(operation_id)

        while result.status in [OperationStatusCodes.running, OperationStatusCodes.not_started]:
            time.sleep(1)
            result = client.get_read_result(operation_id)

        print(result.__dict__)
        if result.status != OperationStatusCodes.succeeded:
            raise Exception("Could't complete the operation")

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        font_thickness = 2

        background_color = (255, 255, 255)
        foreground_color = (0, 0, 0)

        for page in result.analyze_result.read_results:
            for line in page.lines:
                print(line.text)

                bbox = [int(x) for x in line.bounding_box]
                width = bbox[4] - bbox[0]
                height = bbox[5] - bbox[1]
                # draw a white rectangle on top of the original text
                cv2.rectangle(img, (bbox[0], bbox[1]), (bbox[4],bbox[5]), background_color, -1)

                # add the translated text inside the rectangle
                text_size, _ = cv2.getTextSize(line.text, font, font_scale, font_thickness)
                text_x = bbox[0] + int((width - text_size[0]) / 2)
                text_y = bbox[1] + int((height + text_size[1]) / 2)
                cv2.putText(img, line.text, (text_x, text_y), font, font_scale, foreground_color, 2)

        cv2.imshow("asdf", img)
        cv2.waitKey(0)

    return jsonify({"hello": "world"})
