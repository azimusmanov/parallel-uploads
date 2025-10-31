import requests
from dotenv import load_dotenv
from aws_s3_manager import delete_file_from_aws_s3, upload_file_to_aws_s3
import os
import time

load_dotenv()

def ig_create_container(ig_id, access_token, url, caption):
    # Todo: clean up ts, get env stuff from .env,
    # Make a call o s3 upload function. this should make the new url
    # Getting environment variables
    # ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    # access_token = os.getenv("FB_GRAPH_TOKEN_LONG")

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
    response = requests.post(endpoint, payload)
    
    # Check if the request was successful
    if response.status_code == 200:
        print("Container created successfully!")
        response_json = response.json()
        print(response_json)  # Debugging information

        # Extract container ID from the response
        container_id = response_json.get("id")  # Correct field is 'video_id'
        
        # Allow container to process
        success = wait_until_complete(container_id, access_token)

        # Error uploading (stuck on IN_PROGRESS)
        if not success:
            print("Error Uploading Container")
            return False

        return (container_id)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def ig_upload_container(container_number, ig_id, access_token):
    endpoint = f"https://graph.facebook.com/v21.0/{ig_id}/media_publish?creation_id={container_number}&access_token={access_token}"

    print("before response")
    response = requests.post(endpoint)
    if response.status_code == 200:
        print("Post created successfully!")
        response_json = response.json()
        print(response_json)  # Debugging information
    # Check if the status code is 400 (bad request)
    if response.status_code == 400:
        print("Error: Bad request (status code 400)")
        print(response.text)  # Print the detailed error message from the response
    print(response)
    return response

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
            print(f"Error checking status: {response.status_code} — {response.text}")
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
    url, obj = upload_file_to_aws_s3("C:/Users/buchk/parallel-uploads/test_files/test_file_1.mp4")
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