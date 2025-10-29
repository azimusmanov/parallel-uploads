import logging
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import os
from dotenv import load_dotenv

load_dotenv()  # Loads the .env file into the environment

def upload_file_to_aws_s3(file_name, bucket="parallel-uploads-videos", object_name=None):
    """Upload a file to an S3 bucket and return the temporary pre-signed URL

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: URL of the uploaded file if successful, else None
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Path to where files go. Default to uploads folder for now
    key = f"uploads/{object_name}"

    # Extra args for s3 upload file
    extra = {"ContentType": "video/mp4"}

    # Create client
    s3_client = boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION"),             # must match bucket region
        config=Config(signature_version="s3v4")          # force SigV4
        )
    # Upload the file
    try:
        s3_client.upload_file(file_name, bucket, key, ExtraArgs=extra)
    except ClientError as e:
        print("Error uploading file to S3")
        logging.error(e)
        return None

    # Generate a pre-signed url, so that objects could be accesssed. This url expires in 15 minutes
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=900
    )

    return url

if __name__ == '__main__':
    url = upload_file_to_aws_s3("C:/Users/buchk/parallel-uploads/test_files/test_file_1.mp4")
    print(url)