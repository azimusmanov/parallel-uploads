import logging
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()  # Loads the .env file into the environment

def upload_file_to_aws_s3(file_name, bucket="parallel-uploads-videos", object_name=None):
    """Upload a file to an S3 bucket and return the public URL

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: URL of the uploaded file if successful, else None
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Path to where files go. Default to uploads folder for now
    key = "uploads/" + object_name

    # Extra args for s3 upload file
    extra = {"ContentType": "video/mp4"}
    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, key, ExtraArgs=extra)
    except ClientError as e:
        print("Error uploading file to S3")
        logging.error(e)
        return None

    # Construct the URL for the uploaded file
    return f"https://{bucket}.s3.amazonaws.com/{object_name}"

if __name__ == '__main__':
    url = upload_file_to_aws("C:/Users/buchk/parallel-uploads/test_files/test_file_1.mp4")
    print(url)