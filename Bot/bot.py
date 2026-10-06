import os
import time
import uuid
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

# ----------------- TELEGRAM & LOGIC SETUP -----------------
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
    "Bearer Status|logged-in|Session|eyJhbGciOiJLTVMiLCJ0eXAiOiJKV1QifQ.eyJpYXQiOjE3OTEyNDAxODksImV4cCI6MTc5MTI0Mzc4OX0.AQICAHgRVX6yB5HaOXG/6jWEErD4AnJUVlc3se+5PoiAFFV3IgHscuSqoKqxEWZgfQDHGJzXAAAAtDCBsQYJKoZIhvcNAQcGoIGjMIGgAgEAMIGaBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDD/7L/ixLd+ykrkU5wIBEIBtPtAku91VpKz6C2JYQwHvwvUUvnMXM/NiLzqh2fZcTQVcThe3BNDOFkkXj56gWLKy9HxxJUS2PLjC4ZvPsRa0Fk0g1t7EzFG88JRya15DB/bxKVSvpofEaX0XbvdrmheyoIMCagjbWEohHV4puQ=="
)

COOKIE_STR = (
    'adobe-session-id=2e82556e-3c54-4e1c-a983-f87d9265390b; hvh-analytics-cookies-enable=true; '
    'hvh-advertising-cookies-enable=true; cookieConsent=true; hvh_cs_wlbsid=""; hvh-locale=en-GB; '
    'hvh-default-locale=en-GB; hvh-country-code=UK; hvh-stage=prod; at_check=true; '
    'AMCVS_CCBC879D5572070E7F000101%40AdobeOrg=1; AMCV_CCBC879D5572070E7F000101%40AdobeOrg=179643557%7CMCIDTS%7C20732%7CMCMID%7C48590944176880913753806590635719872685%7CMCAAMLH-1791844028%7C6%7CMCAAMB-1791844028%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1791246428s%7CNONE%7CMCAID%7CNONE%7CvVersion%7C5.5.0; '
    's_cc=true; hvhcid=ecbee310-c10b-11f1-b462-6d762f4f7d76; s_ips=730; JSESSIONID=D982E5EB26793CB0A2E44902E133E666; '
    'aws-waf-token=d8447138-ff1d-4660-beff-26895cc3423e:CwoAdB9p0BzmNwAA:GJy2G4pvFzFyRdNndhOcGC4Lrq04KM6obm5y+4B2DdbmG6nSDutCcCcfrF37KQLJsW0CqSkCdccvBkbnSWxKhpXAAQK43s2bqGcR+tqRIpkRiBFMBL8tCpoXwEUjeGw7efPCgjKtdnquDqusQ6rWBGPjCCd1yjMO+I9q51qBsYCBl1pB67nA2fAnF5ub/Qds6Wa5C9sQXQIyFjdl9WBB/kXkAdv4zIaNqxlR/D/TV8oAvDirg9O++FTfwQ7s8yCXTBewr8LrtVB0wcHadB64eRt6Av/NcikfcZJJ/eimqnDYHO2ojhbmdq/YvtC0vMJkzXGwCf5eW3vPxEEg7JPS4UtCC2lUbMYDw/0Aekl6sKBLa0t0b+53b2zcwA/xBg=='
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
        if response.status_code != 200:
            print(f"[{time.strftime('%H:%M:%S')}] HTTP Status: {response.status_code}")
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
                    f"📍 {address},{city}) {postal_code}\n"
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
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Amazon Shift Bot is Online!")

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

    while True:
        check_shifts()
        time.sleep(5)