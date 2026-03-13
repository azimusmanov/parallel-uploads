import subprocess
import sys
from utils.instagram.aws_s3_manager import upload_file_to_aws_s3
from utils.instagram.upload_instagram import ig_create_container
#contact me at AzimUsmanov2027@u.northwestern.edu for more info or documentation

def get_name_from_path(filename):
    i = len(filename)
    if filename[i-4:i:1] != ".mp4":
        return "ERROR"
    i = i - 1
    while i != 0:
        if filename[i] == "/":
            return filename[i+1:len(filename):1]
        else:
            i = i - 1
    return "ERROR"


def main():
    #defining video fields
    #SHARED FIELDS
    filepath = "C:/Users/buchk/parallel-uploads/test_files/test_file_1.mp4"
    title = "AK going crazy"
    description = "Test Description"

    #YOUTUBE FIELDS
    category = "22"  # Example category for 'People & Blogs'
    keywords = "test,upload"
    privacy_status = "unlisted"  # Can be 'public', 'private', or 'unlisted'


    #INSTAGRAM FIELDS

    #temporarily uploading file to AWS instagramfileholder bucket
    aws_url, _ = upload_file_to_aws_s3(filepath)
    print("successfully uploaded to AWS bucket")
    print("AWS link: " + aws_url)

    # Build the command to run upload_youtube.py with the required arguments
    command = [
        sys.executable, "utils/youtube/upload_youtube.py",  # Use sys.executable to ensure the current Python interpreter is used
        "--file", filepath,
        "--title", title,
        "--description", description,
        "--category", category,
        "--keywords", keywords,
        "--privacyStatus", privacy_status
    ]

    # Call the upload_youtube script with subprocess. Currently commented out so I could test with Instagram
    print("YouTube: ")
    result = subprocess.run(command, capture_output=True, text=True)

    # Print the output and error if any
    print("YouTube: ")
    print(result.stdout)
    if result.stderr:
        print("YOUTUBE Error:", result.stderr)

    youtube_url = None
    for line in result.stdout.splitlines():
        if line.startswith("YOUTUBE_URL:"):
            youtube_url = line.split("YOUTUBE_URL:")[1]
            print("YouTube URL:", youtube_url)
            break

    # print("Instagram Process: ")
    # ig_create_container("y", "x" , aws_url, description)

if __name__ == "__main__":
    main()
