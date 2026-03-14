import argparse
import json

import requests

from utils.instagram.aws_s3_manager import generate_presigned_get_url


API_URL = "https://v48jp37m05.execute-api.us-east-2.amazonaws.com/prod/test/instagram"
DEFAULT_BUCKET = "parallel-uploads-videos"


def main():
    parser = argparse.ArgumentParser(description="Test the Instagram publish API with a fresh presigned S3 URL.")
    parser.add_argument("--s3-key", required=True, help="S3 object key for the uploaded video.")
    parser.add_argument("--caption", required=True, help="Caption to send to Instagram.")
    parser.add_argument("--bucket", default=DEFAULT_BUCKET, help="S3 bucket name.")
    args = parser.parse_args()

    presigned_url = generate_presigned_get_url(args.s3_key, bucket=args.bucket)
    payload = {
        "s3_url": presigned_url,
        "caption": args.caption,
    }

    print("Calling Instagram test API...")
    print(f"S3 key: {args.s3_key}")
    print(f"Bucket: {args.bucket}")

    response = requests.post(API_URL, json=payload, timeout=300)
    print(f"HTTP {response.status_code}")

    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)


if __name__ == "__main__":
    main()
