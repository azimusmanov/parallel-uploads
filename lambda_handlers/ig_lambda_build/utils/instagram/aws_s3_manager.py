import logging
import os
import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import load_dotenv


load_dotenv()


def upload_file_to_aws_s3(file_name, bucket="parallel-uploads-assets-rohan-1", object_name=None):
    region = os.getenv("AWS_REGION")

    if object_name is None:
        object_name = os.path.basename(file_name)

    object_key = f"uploads/{object_name}"

    s3_client = boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4"),
    )
    try:
        s3_client.upload_file(file_name, bucket, object_key)
    except ClientError as e:
        print("Error uploading file to S3")
        logging.error(e)
        return None

    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=900,
    )

    return (url, object_key)


def generate_presigned_get_url(object_name, bucket="parallel-uploads-assets-rohan-1", expires_in=900):
    region = os.getenv("AWS_REGION")
    s3_client = boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4"),
    )
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": object_name},
        ExpiresIn=expires_in,
    )


def download_file_from_aws_s3(object_name, file_name, bucket="parallel-uploads-assets-rohan-1"):
    region = os.getenv("AWS_REGION")
    s3_client = boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4"),
    )
    try:
        s3_client.download_file(bucket, object_name, file_name)
        return file_name
    except ClientError as e:
        print("Error downloading file from S3")
        logging.error(e)
        raise


def delete_file_from_aws_s3(object_name, bucket="parallel-uploads-assets-rohan-1") -> bool:
    region = os.getenv("AWS_REGION")

    s3_client = boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4"),
    )
    try:
        s3_client.delete_object(Bucket=bucket, Key=object_name)
        return True
    except ClientError as e:
        print("Error deleting file from S3")
        logging.error(e)
        return False


if __name__ == "__main__":
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
