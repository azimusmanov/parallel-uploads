import os
import time

import requests
from dotenv import load_dotenv

try:
    from .aws_s3_manager import upload_file_to_aws_s3
except ImportError:
    from aws_s3_manager import upload_file_to_aws_s3


load_dotenv()


def _mask_secret(value, visible=6):
    if not value:
        return "<missing>"
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def _debug(message):
    print(f"[instagram-debug] {message}")


def ig_create_container(ig_id, access_token, url, caption):
    _debug("Starting container creation")
    _debug(
        f"Function arguments received: ig_id_provided={bool(ig_id)}, "
        f"access_token_provided={bool(access_token)}"
    )

    ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    access_token = os.getenv("FB_GRAPH_TOKEN_LONG")

    _debug(
        f"Environment values loaded: INSTAGRAM_ACCOUNT_ID={ig_id or '<missing>'}, "
        f"FB_GRAPH_TOKEN_LONG={_mask_secret(access_token)}"
    )
    _debug(f"Video URL received: {url}")
    _debug(f"Caption length: {len(caption or '')}")

    if not ig_id or not access_token:
        _debug("Cannot create container because required Instagram environment variables are missing")
        return None

    endpoint = f"https://graph.facebook.com/v21.0/{ig_id}/media"
    payload = {
        "access_token": access_token,
        "media_type": "REELS",
        "video_url": url,
        "caption": caption,
        "share_to_feed": "TRUE",
    }

    _debug(f"POST {endpoint}")
    _debug(
        f"Payload summary: media_type={payload['media_type']}, "
        f"share_to_feed={payload['share_to_feed']}"
    )

    try:
        response = requests.post(endpoint, payload)
        _debug(f"Container create response status: {response.status_code}")
        _debug(f"Container create response body: {response.text}")
        response.raise_for_status()
    except Exception as e:
        print(f"[ig_create_container] Request failed: {e}")
        return None

    print(f"[ig_create_container] Container created successfully! Response: {response.json()}")

    container_id = response.json().get("id")
    _debug(f"Container ID parsed from response: {container_id}")

    if not container_id:
        _debug("Response did not contain a container id")
        return None

    success = wait_until_complete(container_id, access_token)

    if not success:
        print(f"[ig_create_container] Error: container {container_id} failed to process")
        return None

    return container_id


def ig_upload_container(container_number, ig_id, access_token):
    _debug(f"Starting publish step for container {container_number}")
    _debug(
        f"Publish inputs before env fallback: ig_id_provided={bool(ig_id)}, "
        f"access_token_provided={bool(access_token)}"
    )

    if not ig_id:
        ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    if not access_token:
        access_token = os.getenv("FB_GRAPH_TOKEN_LONG")

    _debug(
        f"Publish environment values: INSTAGRAM_ACCOUNT_ID={ig_id or '<missing>'}, "
        f"FB_GRAPH_TOKEN_LONG={_mask_secret(access_token)}"
    )

    if not container_number or not ig_id or not access_token:
        _debug("Cannot publish because container number, Instagram account id, or access token is missing")
        return None

    endpoint = (
        f"https://graph.facebook.com/v21.0/{ig_id}/media_publish"
        f"?creation_id={container_number}&access_token={access_token}"
    )
    _debug(f"POST {endpoint}")

    try:
        response = requests.post(endpoint)
        _debug(f"Publish response status: {response.status_code}")
        _debug(f"Publish response body: {response.text}")
        response.raise_for_status()
    except Exception as e:
        print(f"[ig_upload_container] Publish request failed: {e}")
        return None

    print(f"[ig_upload_container] Post published successfully! Response: {response.json()}")

    media_id = response.json()["id"]
    _debug(f"Published media id: {media_id}")

    try:
        _debug(f"Fetching permalink for media id {media_id}")
        permalink_resp = requests.get(
            f"https://graph.facebook.com/v21.0/{media_id}",
            params={"fields": "permalink", "access_token": access_token},
        )
        _debug(f"Permalink response status: {permalink_resp.status_code}")
        _debug(f"Permalink response body: {permalink_resp.text}")
        permalink_resp.raise_for_status()
    except Exception as e:
        print(f"[ig_upload_container] Permalink request failed: {e}")
        return None

    print(f"[ig_upload_container] Permalink response: {permalink_resp.json()}")
    return permalink_resp.json()["permalink"]


def ig_publish_video(url, caption):
    ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    access_token = os.getenv("FB_GRAPH_TOKEN_LONG")
    if not ig_id or not access_token:
        raise RuntimeError("Missing Instagram credentials in environment variables.")

    container = ig_create_container(ig_id, access_token, url, caption)
    if not container:
        raise RuntimeError("Instagram container creation failed.")

    permalink = ig_upload_container(container, ig_id, access_token)
    if not permalink:
        raise RuntimeError("Instagram publish failed.")

    return permalink


def wait_until_complete(container_id, access_token, interval=5, max_attempts=40):
    print("Waiting for container to finish processing...")
    _debug(f"Polling container status every {interval}s for up to {max_attempts} attempts")

    for attempt in range(max_attempts):
        status_endpoint = (
            f"https://graph.facebook.com/v21.0/{container_id}"
            f"?fields=status_code&access_token={access_token}"
        )
        _debug(f"GET {status_endpoint}")
        response = requests.get(status_endpoint)
        _debug(f"Status poll response status: {response.status_code}")
        _debug(f"Status poll response body: {response.text}")

        if response.status_code != 200:
            print(f"[wait_until_complete] Error checking status: {response.status_code} - {response.text}")
            time.sleep(interval)
            continue

        status_json = response.json()
        status = status_json.get("status_code", "UNKNOWN")
        print(f"Attempt {attempt + 1}/{max_attempts}: Current status -> {status}")

        if status == "FINISHED":
            print("Container processing complete")
            return True
        if status in ["ERROR", "FAILED"]:
            print(f"Processing failed with status: {status}")
            return False

        time.sleep(interval)

    print("Timeout waiting for container to finish processing")
    return False


if __name__ == "__main__":
    _debug("Running Instagram upload test script entrypoint")
    print("Uploading file to aws...")
    url, obj = upload_file_to_aws_s3(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "test_files",
            "test_file_1.mp4",
        )
    )
    print("File successfully uploaded! Find it at: ")
    print(url)

    ig_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    access_token = os.getenv("FB_GRAPH_TOKEN_LONG")
    _debug(
        f"Test script env values: INSTAGRAM_ACCOUNT_ID={ig_id or '<missing>'}, "
        f"FB_GRAPH_TOKEN_LONG={_mask_secret(access_token)}"
    )

    container = ig_create_container(ig_id, access_token, url, "This is a test")

    if container is not None:
        print(f"Successfuly created container at {container} and uploaded media. Now publishing media")
        ig_upload_container(container, ig_id, access_token)
        print(f"S3 object retained for inspection: {obj}")
        print("Done!")
    else:
        print("Error uploading container")
