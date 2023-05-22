import time
import requests
from apscheduler.schedulers.blocking import BlockingScheduler

ENDPOINTS = [
    "http://monitor:5001/ping",
    "http://api:5000/ping",
]

LOG_FILE = "logs.txt"


def log_request(endpoint, status_code, response_time):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    log_entry = f"{timestamp} - Endpoint: {endpoint}, Status Code: {status_code}, Response Time: {response_time} ms\n"

    with open(LOG_FILE, "a") as file:
        file.write(log_entry)


def ping_endpoints():
    for endpoint in ENDPOINTS:
        try:
            start_time = time.time()
            response = requests.get(endpoint)
            response_time = round((time.time() - start_time) * 1000, 2)
            log_request(endpoint, response.status_code, response_time)
        except requests.exceptions.RequestException as e:
            response_time = -1
            log_request(endpoint, "ERROR: " + str(e), response_time)


scheduler = BlockingScheduler()
scheduler.add_job(ping_endpoints, "interval", minutes=30)
scheduler.start()
