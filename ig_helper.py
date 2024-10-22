import requests
from dotenv import load_dotenv
from accesstoken import gen_page_access_token, get_page_id, get_ig_id
import os
import time

def ig_create_container(ig__id, url, caption):
    ig_id = get_ig_id()

    # access token from the accesstoken.py
    access_token = gen_page_access_token()

    # API endpoint
    endpoint = f"https://graph.facebook.com/v21.0/{ig_id}/media?media_type=REELS&video_url={url}&caption={caption}&share_to_feed=TRUE"

    # Payload for the request
    payload = {
        "access_token": access_token
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
        
        #Allow container to process
        wait_10_sec()

        return ig_upload_container(container_id, ig_id, access_token)
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

def wait_10_sec():
    print("processing media, uploading in: \n")
    i = 0
    while i <= 10:
        time.sleep(1)
        print(f"{10-i} seconds left... \n")
        i = i + 1
    return None