import requests
from dotenv import load_dotenv
try:
    from .aws_s3_manager import delete_file_from_aws_s3, upload_file_to_aws_s3
except ImportError:
    from aws_s3_manager import delete_file_from_aws_s3, upload_file_to_aws_s3
import os
import time

load_dotenv()

def ig_create_container(ig_id, access_token, url, caption):
    # Todo: clean up ts, get env stuff from .env,
    # Make a call o s3 upload function. this should make the new url
    # Getting environment variables
    ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    access_token = os.getenv("FB_GRAPH_TOKEN_LONG")

    # API endpoint

    # Note to self: send data in payload
    endpoint = f"https://graph.facebook.com/v21.0/{ig_id}/media"
    payload = {
        "access_token": access_token,
        "media_type": "REELS",
        "video_url": url,          # raw, not encoded
        "caption": caption,
        "share_to_feed": "TRUE",
    }

    # Make the POST request
    try:
        response = requests.post(endpoint, payload)
        response.raise_for_status()
    except Exception as e:
        print(f"[ig_create_container] Request failed: {e}")
        return None

    print(f"[ig_create_container] Container created successfully! Response: {response.json()}")

    # Extract container ID from the response
    container_id = response.json().get("id")

    # Allow container to process
    success = wait_until_complete(container_id, access_token)

    # Error uploading (stuck on IN_PROGRESS)
    if not success:
        print(f"[ig_create_container] Error: container {container_id} failed to process")
        return None

    return container_id

def ig_upload_container(container_number, ig_id, access_token):
    endpoint = f"https://graph.facebook.com/v21.0/{ig_id}/media_publish?creation_id={container_number}&access_token={access_token}"

    try:
        response = requests.post(endpoint)
        response.raise_for_status()
    except Exception as e:
        print(f"[ig_upload_container] Publish request failed: {e}")
        return None

    print(f"[ig_upload_container] Post published successfully! Response: {response.json()}")

    media_id = response.json()["id"]

    # fetch permalink
    try:
        permalink_resp = requests.get(
            f"https://graph.facebook.com/v21.0/{media_id}",
            params={"fields": "permalink", "access_token": access_token}
        )
        permalink_resp.raise_for_status()
    except Exception as e:
        print(f"[ig_upload_container] Permalink request failed: {e}")
        return None

    print(f"[ig_upload_container] Permalink response: {permalink_resp.json()}")

    return permalink_resp.json()["permalink"]

def wait_until_complete(container_id, access_token, interval=5, max_attempts=40):
    """
    Polls the Instagram Graph API until the media container is ready for publishing.

    :param container_id: The ID of the created media container
    :param access_token: Your long-lived access token
    :param interval: Time (seconds) between checks
    :param max_attempts: Max number of attempts before giving up
    :return: True if processing is complete, False if it failed or timed out
    """
    print("Waiting for container to finish processing...")

    for attempt in range(max_attempts):
        status_endpoint = f"https://graph.facebook.com/v21.0/{container_id}?fields=status_code&access_token={access_token}"
        response = requests.get(status_endpoint)

        if response.status_code != 200:
            print(f"[wait_until_complete] Error checking status: {response.status_code} — {response.text}")
            time.sleep(interval)
            continue

        status_json = response.json()
        status = status_json.get("status_code", "UNKNOWN")
        print(f"Attempt {attempt+1}/{max_attempts}: Current status → {status}")

        if status == "FINISHED":
            print("✅ Container processing complete!")
            return True
        elif status in ["ERROR", "FAILED"]:
            print(f"❌ Processing failed with status: {status}")
            return False

        time.sleep(interval)

    print("⚠️ Timeout waiting for container to finish processing.")
    return False

# Simple test script. Uploads to AWS, gets url and creates a container, uploads container, deletes file from aws
if __name__ == '__main__':
    print("Uploading file to aws...")
    url, obj = upload_file_to_aws_s3(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "test_files", "test_file_1.mp4"))
    print("File successfully uploaded! Find it at: ")
    print(url)
    ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    access_token = os.getenv("FB_GRAPH_TOKEN_LONG")

    container = ig_create_container(ig_id, access_token, url, 'This is a test')

    if container is not None:
        print(f"Successfuly created container at {container} and uploaded media. Now publishing media")
        ig_upload_container(container, ig_id, access_token)
        print("Deleting file from aws...")
        delete_file_from_aws_s3(obj)
        print("Done!")
    else:
        print("Error uploading container")