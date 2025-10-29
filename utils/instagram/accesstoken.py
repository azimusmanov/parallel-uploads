import requests
import os
import json
from dotenv import load_dotenv

# This is a simple helper file that gets a long access token for the facebook graph api,
# which is used for posting to instagram and facebook. There is also a simple tester function
# that makes an api call with this token. simply run the file, and observe outputs

# should return a long term access token thats valid for around 60 days
def get_long_token():
    # Loading Environment Variables
    load_dotenv()
    ig_user_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    app_id = os.getenv("APP_ID")
    app_secret = os.getenv("APP_SECRET")
    user_access_token = os.getenv("USER_ACCESS_TOKEN")

    # URL
    url = f"https://graph.facebook.com/v17.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={user_access_token}"

    response = requests.get(url)
    long_access_token = response.json()["access_token"]

    return long_access_token

def test_token(token: str):
    ig_user_id = os.getenv("INSTAGRAM_ACCOUNT_ID")
    username = os.getenv("IG_TEST_USERNAME")
    print(f"username: {username}")
    required_param = "{followers_count, media_count}"
    url = f"https://graph.facebook.com/v17.0/{ig_user_id}?fields=business_discovery.username({username}){required_param}&access_token={token}"
    
    response = requests.get(url)

    # Check if request was successful
    if response.status_code == 200:
        metadata = response.json()
        followers_count = metadata["business_discovery"]["followers_count"]
        media_count = metadata["business_discovery"]["media_count"]
        print(json.dumps(metadata, indent=4))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
    
# Ensure the functions run when the script is executed directly
if __name__ == "__main__":
    token = get_long_token()
    print(f"Long-Life Page Access Token: {token}")

    print("Testing Token...")
    test_token(token)