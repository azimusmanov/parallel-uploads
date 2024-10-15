import subprocess
import sys
from upload_helper import upload_file


def main():
    # Define your video details here
    filepath = "C:/Users/buchk/Documents/#Career/IMG_4786.mov"
    file_name = "IMG_4786.mov"
    title = "AK going crazy"
    description = "Test Description"
    category = "22"  # Example category for 'People & Blogs'
    keywords = "test,upload"
    privacy_status = "unlisted"  # Can be 'public', 'private', or 'unlisted'

    #temporarily uploading file to AWS instagramfileholder bucket
    upload_file(filepath)
    aws_url = "https://instagramfileholder.s3.us-east-2.amazonaws.com/" + file_name
    print("successfully uploaded to AWS bucket")

    # Build the command to run upload_youtube.py with the required arguments
    command = [
        sys.executable, "upload_youtube.py",  # Use sys.executable to ensure the current Python interpreter is used
        "--file", filepath,
        "--title", title,
        "--description", description,
        "--category", category,
        "--keywords", keywords,
        "--privacyStatus", privacy_status
    ]

    # Call the upload_youtube script with subprocess
    result = subprocess.run(command, capture_output=True, text=True)

    # Print the output and error if any
    print(result.stdout)
    if result.stderr:
        print("Error:", result.stderr)

if __name__ == "__main__":
    main()
