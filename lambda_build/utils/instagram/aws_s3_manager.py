import logging
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import os
from dotenv import load_dotenv
import time

load_dotenv()  # Loads the .env file into the environment


def _get_s3_client():
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION")
    return boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
    )

def upload_file_to_aws_s3(file_name, bucket="parallel-uploads-videos", object_name=None):
    """Upload a file to an S3 bucket and return the temporary pre-signed URL

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: Tuple of URL of the uploaded file and object name/key if successful, else None
    """

    # Getting environment variables
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Path to where files go. Default to uploads folder for now
    object_key = f"uploads/{object_name}"
    
    # Create client
    s3_client = _get_s3_client()
    # Upload the file
    try:
        s3_client.upload_file(file_name, bucket, object_key)
    except ClientError as e:
        print("Error uploading file to S3")
        logging.error(e)
        return None

    # Generate a pre-signed url, so that objects could be accesssed. This url expires in 15 minutes
    url = s3_client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": object_key}, ExpiresIn=900)

    return (url, object_key)


def generate_presigned_get_url(object_name, bucket="parallel-uploads-videos", expires_in=900):
    s3_client = _get_s3_client()
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": object_name},
        ExpiresIn=expires_in,
    )


def download_file_from_aws_s3(object_name, file_name, bucket="parallel-uploads-videos"):
    s3_client = _get_s3_client()
    try:
        s3_client.download_file(bucket, object_name, file_name)
        return file_name
    except ClientError as e:
        print("Error downloading file from S3")
        logging.error(e)
        raise

def delete_file_from_aws_s3(object_name, bucket="parallel-uploads-videos") -> bool:
    """Delete a file from an S3 bucket

    :param object_name: S3 object key (e.g., "uploads/test_file_1.mp4")
    :param bucket: Bucket name (defaults to your main bucket)
    :return: True if deleted successfully, False otherwise
    """
    # Getting environment variables
    s3_client = _get_s3_client()
    # Delete the file
    try:
        s3_client.delete_object(Bucket=bucket, Key=object_name)
        return True
    except ClientError as e:
        print("Error deleting file from S3")
        logging.error(e)
        return False

# Testing functionality by uploading and deleting a simple bucket
if __name__ == '__main__':
    print("Uploading file...")
    url, obj = upload_file_to_aws_s3("C:/Users/buchk/parallel-uploads/test_files/test_file_1.mp4")
    print("File successfully uploaded! Find it at: ")
    print(url)
    print("\nWaiting 4 seconds then deleting...")
    for i in range(4):
        time.sleep(1)
        print(i)
    print("Deleting file...")
    delete_file_from_aws_s3(obj)
    print("Done!")
