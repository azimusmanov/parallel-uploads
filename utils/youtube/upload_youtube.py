#TO DO: Upload Message Says channel name that it was uploaded to

# from
# https://developers.google.com/youtube/v3/guides/uploading_a_video

#  Usage (standalone):
# python upload_youtube.py --file="C:\Users\buchk\Documents\#Career\IMG_4786.mov" --title="AK going crazy" --description="Test Description" --category="22" --keywords="test,upload" --privacyStatus="unlisted"

import http.client as httplib
import httplib2
import os
import random
import sys
import time

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


httplib2.RETRIES = 1

MAX_RETRIES = 10

RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_secrets.json")
OAUTH_STORAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_youtube.py-oauth2.json")

YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/
""" % CLIENT_SECRETS_FILE

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def get_authenticated_service(args):
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
                                   scope=YOUTUBE_UPLOAD_SCOPE,
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)

    storage = Storage(OAUTH_STORAGE_FILE)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                 http=credentials.authorize(httplib2.Http()))


def initialize_upload(youtube, file, title, description, category, keywords, privacy_status):
    tags = keywords.split(",") if keywords else None

    body = dict(
        snippet=dict(
            title=title,
            description=description,
            tags=tags,
            categoryId=category
        ),
        status=dict(
            privacyStatus=privacy_status
        )
    )

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(file, chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request)


def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    url = f"https://www.youtube.com/watch?v={response['id']}"
                    print(f"Video successfully uploaded: {url}")
                    return url
                else:
                    raise RuntimeError(f"Upload failed with unexpected response: {response}")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"A retriable error occurred: {e}"

        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                raise RuntimeError("Max retries exceeded. Upload failed.")
            sleep_seconds = random.random() * (2 ** retry)
            print(f"Sleeping {sleep_seconds:.1f}s then retrying...")
            time.sleep(sleep_seconds)
            error = None


def upload_youtube(file, title, description, category="22", keywords="", privacy_status="unlisted"):
    """
    Upload a video to YouTube.
    Returns the video URL on success, or raises an exception on failure.
    """
    if not os.path.exists(file):
        raise FileNotFoundError(f"Video file not found: {file}")

    import argparse
    args = argparse.Namespace(
        file=file, title=title, description=description,
        category=category, keywords=keywords, privacyStatus=privacy_status,
        auth_host_name='localhost', auth_host_port=[8080, 8090],
        logging_level='ERROR', noauth_local_webserver=False
    )

    youtube = get_authenticated_service(args)
    return initialize_upload(youtube, file, title, description, category, keywords, privacy_status)


if __name__ == '__main__':
    argparser.add_argument("--file", required=True, help="Video file to upload")
    argparser.add_argument("--title", help="Video title", default="Test Title")
    argparser.add_argument("--description", help="Video description", default="Test Description")
    argparser.add_argument("--category", default="22",
                           help="Numeric video category. See https://developers.google.com/youtube/v3/docs/videoCategories/list")
    argparser.add_argument("--keywords", help="Video keywords, comma separated", default="")
    argparser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
                           default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
    args = argparser.parse_args()

    try:
        url = upload_youtube(args.file, args.title, args.description,
                             args.category, args.keywords, args.privacyStatus)
        print(f"YouTube URL: {url}")
    except Exception as e:
        print(f"Error: {e}")
