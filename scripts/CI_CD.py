# run-lre-test.py
import os, sys, json, time, requests, xml.etree.ElementTree as ET, tempfile, shutil, zipfile

# Load environment variables
TEST_ID = int(os.environ["lre_test"])
TEST_INSTANCE_ID = os.environ["lre_test_instance"]
TIMESLOT_HOURS = int(os.environ["lre_timeslot_duration_hours"])
TIMESLOT_MINUTES = int(os.environ["lre_timeslot_duration_minutes"])
TOKEN = os.environ["LRE_API_TOKEN"]
LRE_URL = os.environ["lRE_URL"]
DOMAIN = os.environ["DOMAIN "]
PROJECT_NAME = os.environ["PROJECT_NAME "]


# Validate Test Instance ID
if TEST_INSTANCE_ID.upper() == "AUTO":
    print("Error: Test instance is set to AUTO. Please set a valid number.")
    sys.exit(1)
TEST_INSTANCE_ID = int(TEST_INSTANCE_ID)

# API endpoints
AUTH_URL = f"{LRE_URL}/rest/authentication-point/authenticate?tenant=fa128c06-5436-413d-9cfa-9f04bb738df3"
RUN_URL = f"{LRE_URL}/rest/domains/{DOMAIN}/projects/{PROJECT_NAME}/runs"
GET_RUN_EXTENDED_STATUS = (
    f"{LRE_URL}/rest/domains/{DOMAIN}/projects/{PROJECT_NAME}/Runs"
)

# Create session and authenticate
session = requests.Session()
session.post(
    AUTH_URL, headers={"Content-Type": "application/json"}, json={"Token": TOKEN}
)

# Start test run
run_body = {
    "PostRunAction": "Collate Results",
    "TestID": TEST_ID,
    "TestInstanceID": TEST_INSTANCE_ID,
    "TimeslotDuration": {"Hours": TIMESLOT_HOURS, "Minutes": TIMESLOT_MINUTES},
    "VudsMode": False,
}
RUN_ID = session.post(
    RUN_URL, headers={"Content-Type": "application/json"}, json=run_body
).json()["ID"]
print(f"Test run started: {RUN_ID}")

# Poll status and evaluate failure rate
STATUS = "INITIALIZING"
while STATUS not in ["FINISHED", "FAILED", "STOPPED"]:
    time.sleep(30)
    STATUS = (
        session.get(f"{RUN_URL}/{RUN_ID}", headers={"Content-Type": "application/json"})
        .json()
        .get("RunState", "UNKNOWN")
    )
    if STATUS == "RUNNING":
        resp = session.get(f"{GET_RUN_EXTENDED_STATUS}/{RUN_ID}/Extended")
        xml_root = ET.fromstring(resp.content)
        total_passed = int(xml_root.findtext(".//TotalPassedTransactions", default="0"))
        total_failed = int(xml_root.findtext(".//TotalFailedTransactions", default="0"))
        failure_percent = (
            round((total_failed / (total_passed + total_failed)) * 100, 2)
            if total_passed + total_failed > 0
            else 0
        )
        print(f"Failure %: {failure_percent}")
        if failure_percent >= 5:
            print("Too many failures, stopping test...")
            session.post(
                f"{RUN_URL}/{RUN_ID}/stopNow",
                headers={"Content-Type": "application/json"},
            )
            break

# Download RawResults ZIP and save artifacts
results = session.get(f"{RUN_URL}/{RUN_ID}/results").json()
raw_zip = next(r for r in results if r["Name"].startswith("RawResults_"))
zip_path = os.path.join(tempfile.gettempdir(), raw_zip["Name"])
with session.get(f"{RUN_URL}/{RUN_ID}/results/{raw_zip['ID']}/data", stream=True) as r:
    with open(zip_path, "wb") as f:
        shutil.copyfileobj(r.raw, f)
extract_path = os.path.join(tempfile.gettempdir(), "RawResultsExtracted")
shutil.rmtree(extract_path, ignore_errors=True)
with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall(extract_path)
artifact_dir = os.path.join(os.environ.get("CI_PROJECT_DIR", os.getcwd()), "Artifacts")
shutil.copytree(
    extract_path, os.path.join(artifact_dir, "RawResults"), dirs_exist_ok=True
)
print(f"Artifacts saved at {artifact_dir}")
