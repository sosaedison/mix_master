import os
import requests
import time

from common import MUSIC_DIR, DLB_RAW_FILES, DLB_ANALYZED_FILES

from dotenv import load_dotenv

load_dotenv()

def refresh_access_token() -> str:
    url = "https://api.dolby.io/v1/auth/token"

    payload = { "grant_type": "client_credentials" }
    headers = {
        "accept": "application/json",
        "Cache-Control": "no-cache",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic"
    }

    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()

    print(response.json())

    return response.json()["access_token"]

input_path = f"{MUSIC_DIR}/Sete - Nitefreak Remix BLOND_ISH, Francis Mercier, Amadou & Mariam, Nitefreak Sete (Nitefreak Remix) 2022.wav"
DLB_RAW_MUSIC_FILE = f"{DLB_RAW_FILES}/Sete_Nitefreak_Remix.wav"
DLB_ANALYZED_MUSIC_FILE = f"{DLB_ANALYZED_FILES}/Sete_Nitefreak_Remix.wav"

# Add your API token as an environmental variable or hard coded value.
api_token = ""

headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
media_storage_url = "https://api.dolby.com/media/input"
# Replace the url value with your Dolby.io temporary storage location that you want to create.
body = {
    "url": DLB_RAW_MUSIC_FILE,
}

# Create a pre-signed URL.
response = requests.post(url=media_storage_url, json=body, headers=headers)
response.raise_for_status()
data = response.json()
presigned_url = data["url"]
print(f"Uploading {input_path} to presigned_url")
with open(input_path, "rb") as input_file:
    # Upload your media.
    response = requests.put(presigned_url, data=input_file)
    response.raise_for_status()
    print(f"Upload complete -> {response.status_code}")


analyze_url = "https://api.dolby.com/media/analyze/music"

payload = {
    "input": DLB_RAW_MUSIC_FILE,
    "output": DLB_ANALYZED_MUSIC_FILE
}

headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "x-api-version": "v1.0",
}

response = requests.post(analyze_url, json=payload, headers=headers)

print(response.text)

job_id = response.json()["job_id"]

job_status = None

time_elapsed = 0

headers = {"accept": "application/json", "authorization": f"Bearer {api_token}"}
while job_status != "Success":
    time.sleep(5)
    time_elapsed += 5
    response = requests.get(f"{analyze_url}?job_id={job_id}", headers=headers)
    response.raise_for_status()
    data = response.json()
    job_status = data["status"]
    print(f"Job status: {job_status} -> after {time_elapsed} seconds")

    if job_status == "Failed":
        print("Job failed")
        print(response.json())
        break

print(response.json())
num_sections = response.json()["result"]["processed_region"]["audio"]["music"][
    "num_sections"
]

print(f"Number of sections: {num_sections}")
if num_sections >= 1:
    print(
        f"BPM is -> {response.json()['result']['processed_region']['audio']['music']['sections'][0]['bpm']}"
    )
