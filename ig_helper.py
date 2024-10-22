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
    # endpoint = f"https://graph.facebook.com/v21.0/{ig_business_account_user_id}/media?video_url={url}&caption=#{caption}"
    endpoint = f"https://graph.facebook.com/v21.0/{ig_id}/media?image_url={url}&caption=#{caption}"
    # Payload for the request
    payload = {
        "access_token": access_token
    }
    # Make the POST request
    response = requests.post(endpoint, payload)
    print("after response request")
    # Check if the request was successful
    if response.status_code == 200:
        print("Container created successfully!")
        response_json = response.json()
        print(response_json)  # Debugging information

        # Extract container ID from the response
        container_id = response_json.get("video_id")  # Correct field is 'video_id'
        print(f"Container ID: {container_id}")
        return ig_upload_container(container_id)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None



def ig_upload_container(container_number):
    response = requests.post(f"https://graph.facebook.com/v21.0/17841469637578345/media_publish?creation_id={container_number}")
    #response = requests.post(f"https://graph.facebook.com/v21.0/17841469637578345/media_publish?creation_id=896791421977760")

    # Check if the status code is 400 (bad request)
    if response.status_code == 400:
        print("Error: Bad request (status code 400)")
        print(response.text)  # Print the detailed error message from the response
    print(response)
    return response