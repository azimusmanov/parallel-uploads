import requests

def exchange_for_long_lived_token(short_lived_token, client_secret):
    url = "https://graph.instagram.com/access_token"
    params = {
        "grant_type": "ig_exchange_token",
        "client_secret": "529f4c2105846aa385595db8ba43ff8b",
        "access_token": "EAAOZBCU1nD8kBOx3PrTTyrsC4LFDZA4rf3HXQXe4gNHGiACtZAmHHi4PeqRkoZC9lRTsAmi9tZC1uqMLLehqfZC0hYPTaW4Ao2ZAW2ZAKKZBjD2QRP5fzk0V8NH7H0VIrHsrjnmraRpz3Srj4Q0TttsrOaPN7DLIiwAdxhamwVyQYf8gs4PZBKZCAVPO36KoDgjeaZAQu5XKnlNiR3ChvxitXR5ZAZCDRzv3O1ZCSWWts8ZD"
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Replace these with your actual short-lived token and client secret
short_lived_token = "your_short_lived_token"
client_secret = "your_instagram_app_secret"

long_lived_token = exchange_for_long_lived_token(short_lived_token, client_secret)

if long_lived_token:
    print("Long-lived token:", long_lived_token)
