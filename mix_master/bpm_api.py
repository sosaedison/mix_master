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
        "Authorization": "Basic dFl5bUM0TndUeS1ycGxNNVhqanlMdz09OlRtVF9YTmJSVUJsV1ZYdmIxWTVDZ181S3M1clI4cmpmWGVBX1lYc2NuRjQ9"
    }

    response = requests.post(url, data=payload, headers=headers)
    response.raise_for_status()

    print(response.json())

    return response.json()["access_token"]

input_path = f"{MUSIC_DIR}/Sete - Nitefreak Remix BLOND_ISH, Francis Mercier, Amadou & Mariam, Nitefreak Sete (Nitefreak Remix) 2022.wav"
DLB_RAW_MUSIC_FILE = f"{DLB_RAW_FILES}/Sete_Nitefreak_Remix.wav"
DLB_ANALYZED_MUSIC_FILE = f"{DLB_ANALYZED_FILES}/Sete_Nitefreak_Remix.wav"

# Add your API token as an environmental variable or hard coded value.
api_token = "eyJ0eXAiOiJKV1QiLCJraWQiOiI1ODExQjE0RS1DQzVCLTQ4QkQtQTNEOC1DREQxQzUzQ0ZDNUMiLCJhbGciOiJSUzUxMiJ9.eyJpc3MiOiJkb2xieS5pbyIsImlhdCI6MTczNzMzNTE2Niwic3ViIjoidFl5bUM0TndUeS1ycGxNNVhqanlMdz09IiwiYXV0aG9yaXRpZXMiOlsiUk9MRV9DVVNUT01FUiJdLCJ0YXJnZXQiOiJhcGkiLCJvaWQiOiI5N2Y5Y2IyNS01ODM4LTQ2MTYtYjIyMi0zMjg4OTlhNjk1MzUiLCJhaWQiOiI2N2NlZDcwMC1mZWY1LTQ0ZDEtYjgwOS0zMzAyNDkwNjJhY2YiLCJiaWQiOiI4YTM2ODg1NDk0NmQyMmE5MDE5NDgwZWVkMjc5MDVmYyIsImV4cCI6MTczNzMzNjk2Nn0.rnz218SI0Ucxg1V8qra3zEB0sH8smGuINOTf9lytV86p9LVDFhS3VTimLec4Vmo-Xso-14-DTFgGJ4nv9y48AEORjeQZt1-pYQLZgVVkD2jhhS4iaAuEQGxiJOFX2VVpKLyTO1VK7P-FZ_wXwSZqO0JCWwycz7eNxrH9MsO-5V3jG8Uw-dpsmFM3GjxkLSORAMs_MniiKwcHpiR3Hk1JQGGZ34e2SCsKa57YyzJPgbyJ-FegNXY_91NJhtyn0bde7vdwyt244ZkdsTKa5GyIbvGYMVcAQrg1qgvm1uI3PFES8uPCKy46hPMmVPCPWExyEQq-NDW8EzvSetRTSu2f9rGEmkUoav_f80QD_uTpKzUWIqHr-uD0XjoEB0h_2AJ5L9TSXvy5DxxzBGy61b2-41KwaY0z2XcCPMlpRVTGiyWlq8x5Vml8L0bulAVSDO5EAzR4wazOV4DPPqIzn9-UcFcWzxVMYKKUh6th8vmQk2VmukGULfj5jCSkzqkYGBCsJbCLM-8UlzyEIlv58yq-IsXntopI5mNkeX_HlTuYr6TvxEzgW6QQzmV3AYTjo1fKjCF3f8ZMXswkiHPDd_7DmcXIgxttnALJ_JHLSEFszHs_RSUdeNvCtVITTaKeUmLwt_TfHvLHV9Ed3zH2XdZieeUmsBrMN4CPzCWL18kAgQs"

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
