from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.instagram.aws_s3_manager import upload_file_to_aws_s3
from utils.instagram.upload_instagram import ig_create_container
from utils.youtube.upload_youtube import upload_youtube
#contact me at AzimUsmanov2027@u.northwestern.edu for more info or documentation


def main():
    #SHARED FIELDS
    filepath = "C:/Users/buchk/parallel-uploads/test_files/test_file_1.mp4"
    title = "AK going crazy"
    description = "Test Description"

    #YOUTUBE FIELDS
    category = "22"  # Example category for 'People & Blogs'
    keywords = "test,upload"
    privacy_status = "unlisted"  # Can be 'public', 'private', or 'unlisted'

    # Upload file to AWS so Instagram can access it via URL
    aws_url, _ = upload_file_to_aws_s3(filepath)
    print(f"Successfully uploaded to AWS bucket: {aws_url}")

    # Upload to YouTube and Instagram concurrently
    with ThreadPoolExecutor() as executor:
        yt_future = executor.submit(upload_youtube, filepath, title, description, category, keywords, privacy_status)
        ig_future = executor.submit(ig_create_container, None, None, aws_url, description)

        for future in as_completed([yt_future, ig_future]):
            if future == yt_future:
                try:
                    youtube_url = future.result()
                    print(f"YouTube URL: {youtube_url}")
                except Exception as e:
                    print(f"YouTube upload failed: {e}")
            else:
                try:
                    ig_result = future.result()
                    print(f"Instagram container: {ig_result}")
                except Exception as e:
                    print(f"Instagram upload failed: {e}")


if __name__ == "__main__":
    main()
