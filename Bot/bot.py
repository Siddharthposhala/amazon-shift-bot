import os
import time
import uuid
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

# ----------------- TELEGRAM & LOGIC SETUP -----------------
latest_status_message = "Initializing bot..."
TELEGRAM_BOT_TOKEN = "8876339427:AAFcMwDl86tFhSwSsoIGBZHMPRg_zQzerd0"
CHAT_IDS = ["995130827", "8914774840"]

seen_job_ids = set()

LONDON_AREAS = [
    "london", "enfield", "dartford", "bromley", "croydon", "barking",
    "dagenham", "tilbury", "en3", "da17", "br5", "rm9", "ig11", "ha0",
    "heathrow", "tw6", "ub3", "ub7", "e16", "se28"
]

session = requests.Session()

BEARER_TOKEN = (
    "Status|UNAUTHENTICATED|Session|eyJhbGciOiJLTVMiLCJ0eXAiOiJKV1QifQ.eyJpYXQiOjE3OTEyNDc5ODcsImV4cCI6MTc5MTI1MTU4N30.AQICAHgRVX6yB5HaOXG/6jWEErD4AnJUVlc3se+5PoiAFFV3IgF6hNqVpk2XuNkKBBTd9KP2AAAAtDCBsQYJKoZIhvcNAQcGoIGjMIGgAgEAMIGaBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDBB8JfJ5MC6m/UN7mgIBEIBt54CBZP7RXfYZKVx8YU57vxC31LkGQjg0MeozCz1RAd+wa9MbGSgj2vdFuI5+upLE2jn+ZCBtqhbg7bpXsdh5Zmt/MPuZ5EPu1elfpZ6RqivT1EjP6jpcRQTZPxGA33FTBO+gg/wH7gIlGKgWLA=="
    )

COOKIE_STR = (
    'hvh-locale=en-GB; hvh-default-locale=en-GB; hvh-country-code=UK; hvh-stage=prod; adobe-session-id=7ac72e8c-ef4c-4763-b514-707b86a39296; hvh_cs_wlbsid=""; hvh-analytics-cookies-enable=true; hvh-advertising-cookies-enable=true; cookieConsent=true; at_check=true; AMCVS_CCBC879D5572070E7F000101%40AdobeOrg=1; s_cc=true; AMCV_CCBC879D5572070E7F000101%40AdobeOrg=179643557%7CMCIDTS%7C20733%7CMCMID%7C53491464723443621675762394496461225840%7CMCAAMLH-1791852228%7C6%7CMCAAMB-1791852228%7C6G1ynYcLPuiQxYZrsz_pkqfLG9yMXBpb2zX5dvJdYQJzPXImdj0y%7CMCOPTOUT-1791254628s%7CNONE%7CMCAID%7CNONE%7CMCSYNCSOP%7C411-20740%7CvVersion%7C5.5.0; JSESSIONID=0331AFBA1773F69E12A268AB01AC2448; QSI_HistorySession=https%3A%2F%2Fwww.jobsatamazon.co.uk%2F~1791247426430%7Chttps%3A%2F%2Fwww.jobsatamazon.co.uk%2Fapp%23%2FjobSearch~1791247452415; hvhcid=5ffb55d0-c11f-11f1-b362-c1a88b1cc19d; s_ips=632; mbox=session#af1e83a920f74822b52a35ebd0ad68d0#1791249848|PC#af1e83a920f74822b52a35ebd0ad68d0.37_0#1854492788; s_tp=1262; s_ppv=https%253A%252F%252Fwww.jobsatamazon.co.uk%252Fapp%2523%252FjobSearch%2C50%2C50%2C632%2C1%2C1; s_sq=%5B%5BB%5D%5D; aws-waf-token=d8447138-ff1d-4660-beff-26895cc3423e:CwoAqqNpzgtSJAAA:bRzfTKfZDu7ogjMIn0Z+TGU5HqnRSWvnda2U/TtdRX3YIIc2FAbFvAMqQz22tUgmAdmsjr9XAtajt/rUCPbwVO7pCLg3s4a4IxCWzyyURyedFrGCb9mMKDUvYBxojHSDkC7UEoLERnaYfEeYdoop2XUhct6UFz6Cm9inn0T0ErjhmgIcoMatCC7tDp9uzrKAkr1+kYJHQHoS8JEseUQfWx7Akfs3osgPaEg0lwL7UsgAZJLm4vlDD3mS6MLRsgcK1UfD2SHBwxFY+WY0vJlFaRFqBSu4vuZXL0iRXE27TAYfFkrC7Yh5pP0d31zgQOcxdUf5IzyaBGr+svH4as00fQh4qS0AkNyYoEiA7zSLtJMvUVSyJnbWlt2cr3Z5ew=='
)

GRAPHQL_QUERY = """query searchJobCardsByLocation($searchJobRequest: SearchJobRequest!) {
  searchJobCardsByLocation(searchJobRequest: $searchJobRequest) {
    nextToken
    jobCards {
      jobId
      jobTitle
      jobType
      employmentType
      city
      postalCode
      totalPayRateMinL10N
      jobTypeL10N
      employmentTypeL10N
      __typename
    }
    __typename
  }
}"""

def send_alert(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for cid in CHAT_IDS:
        payload = {"chat_id": cid, "text": text, "disable_web_page_preview": False}
        try:
            requests.post(url, json=payload, timeout=8)
        except Exception as e:
            print(f"Failed to alert {cid}: {e}")

def check_shifts():
    global latest_status_message 
    url = "https://www.jobsatamazon.co.uk/graphql"
    current_time_ms = str(int(time.time() * 1000))
    headers = {
        "accept": "*/*",
        "authorization": BEARER_TOKEN,
        "content-type": "application/json",
        "cookie": COOKIE_STR,
        "country": "United Kingdom",
        "origin": "https://www.jobsatamazon.co.uk",
        "referer": "https://www.jobsatamazon.co.uk/app",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
        "x-amzn-requestid": str(uuid.uuid4()),
        "x-hvh-time": current_time_ms
    }

    payload = {
        "operationName": "searchJobCardsByLocation",
        "variables": {
            "searchJobRequest": {
                "locale": "en-GB",
                "country": "United Kingdom",
                "pageSize": 100,
                "geoQueryClause": {"lat": 51.50740836, "lng": -0.127698693, "unit": "mi", "distance": 50},
                "consolidateSchedule": True
            }
        },
        "query": GRAPHQL_QUERY
    }

    try:
        response = session.post(url, json=payload, headers=headers, timeout=10)
        # Update the web server message with the live status
        status_text = f"[{time.strftime('%H:%M:%S')}] HTTP Status: {response.status_code}"
        print(status_text)
        latest_status_message = status_text
        
        if response.status_code != 200:
            send_alert("The bot has stopped Due to 403 Error")
            return

        data = response.json()
        job_cards = data.get("data", {}).get("searchJobCardsByLocation", {}).get("jobCards", []) or []
        print(f"[{time.strftime('%H:%M:%S')}] Polled Amazon. Open shifts: {len(job_cards)}")

        for job in job_cards:
            job_id = job.get("jobId")
            address = job.get("address","")
            city = job.get("city", "London")
            postal_code = job.get("postalCode", "")
            full_loc = f"{city} {postal_code}".strip()

            if not any(k in full_loc.lower() for k in LONDON_AREAS):
                continue

            if job_id and job_id not in seen_job_ids:
                seen_job_ids.add(job_id)
                title = job.get("jobTitle", "Warehouse Associate")
                job_type = job.get("jobTypeL10N") or "Seasonal"
                emp_type = job.get("employmentTypeL10N") or "Part-time"
                pay_min = job.get("totalPayRateMinL10N") or "Competitive"
                apply_url = f"https://www.jobsatamazon.co.uk/application/uk/?CS=true&jobId={job_id}&locale=en-GB&ssoEnabled=1#/consent?CS=true&jobId={job_id}&locale=en-GB&ssoEnabled=1"

                alert_text = (
                    f"📍 ({address},{city}) {postal_code}\n"
                    f"🏷️ {title} | 1\n"
                    f"💼 {job_type} | {emp_type}\n"
                    f"💰 {pay_min}\n\n"
                    f"🔗 {apply_url}"
                )
                print(f"🚨 MATCH FOUND: {title} in {full_loc}")
                send_alert(alert_text)

    except Exception as err:
        print(f"Error checking shifts: {err}")

# ----------------- DUMMY SERVER FOR RENDER -----------------
class RenderHealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        global latest_status_message 
        self.send_response(200)
        self.end_headers()
        self.wfile.write(latest_status_message.encode("utf-8"))

def run_render_server():
    # Render binds automatically to the PORT environment variable (default 10000)
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), RenderHealthServer)
    print(f"Health server running on port {port}")
    server.serve_forever()

if __name__ == "__main__":
    # Start web server on a background thread for Render
    threading.Thread(target=run_render_server, daemon=True).start()

    send_alert("🟢 Bot successfully deployed to Render! Monitoring active.")
    print("Bot loop started...")
    x = 1800
    while True:
        check_shifts()
        time.sleep(2)
        x+=2
        if (x % 1800 == 0):
            x=1800
            send_alert("Bot is Active && Login into your AMAZON ACCOUNT")
            
            
