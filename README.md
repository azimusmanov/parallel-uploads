# Parallel Uploads

**Project Status:** Early Development 

## Overview
Parallel Uploads is a personal project by **Azim Usmanov**, created to streamline the process of distributing short-form content across multiple platforms such as **TikTok**, **YouTube Shorts**, and **Instagram**. The goal is to enable creators to upload a single video and automatically publish it to all selected platforms, eliminating repetitive manual uploads.

## Objective
The long-term goal is to deploy a full backend and turn this into a functioning web application where users can:
- Upload short-form videos directly through a web interface  
- Choose which platforms to publish to  
- Automate uploading and publishing through secure API integrations  
- And any other features that might prove useful

## Technical Focus
This project serves as a learning platform for me to develop my skills in:
- **Backend development** and **REST API design**
- **AWS S3** file management and cloud storage
- **API integration** with the Meta Graph API, YouTube Data API, and TikTok API
- **Authentication**, **token management**, and secure environment variable handling
- Preparing for **cloud deployment** and scaling backend services

## Contact
For questions or collaboration inquiries, contact:  
**Email:** AzimUsmanov2027@u.northwestern.edu

## Local Web UI
This project now includes a small Flask frontend for testing uploads from a browser.

### What it does
- Accepts a video file upload from the browser
- Lets you choose YouTube and/or Instagram
- Lets you enter a title, caption/description, YouTube keywords, and YouTube privacy
- Runs the existing Python upload logic on form submit

### Run it
1. Create and activate a virtual environment
2. Install dependencies with `pip install -r requirements.txt`
3. Add your `.env` file for AWS and Instagram credentials
4. Place `client_secrets.json` in `utils/youtube/`
5. Start the web app with `python app.py`
6. Open `http://127.0.0.1:5000`

### Required environment variables
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `INSTAGRAM_ACCOUNT_ID`
- `FB_GRAPH_TOKEN_LONG`
- `APP_ID`
- `APP_SECRET`
- `USER_ACCESS_TOKEN`
- `IG_TEST_USERNAME`

### Important notes
- The request stays open while uploads run. This is a simple local UI, not a background job system.
- The first YouTube upload may trigger the OAuth browser flow if `upload_youtube.py-oauth2.json` does not already exist.
- Instagram publishing depends on the Meta Graph API credentials being valid and configured for Reels uploads.

## Job-Driven Worker
The uploader can now process job payloads instead of relying on a hardcoded local test file.

### Supported job shape
```json
{
  "id": 101,
  "platform": "youtube",
  "asset": {
    "s3_bucket": "parallel-uploads-videos",
    "s3_key": "uploads/my-video.mp4",
    "original_filename": "my-video.mp4",
    "caption": "Example caption",
    "title": "Example title"
  },
  "platform_specific_metadata": {
    "title": "Example title",
    "description": "Example caption",
    "keywords": "demo,shorts",
    "privacy_status": "unlisted",
    "category": "22"
  }
}
```

### Run the worker on a job payload
```powershell
python main.py --job-file job.json
```

Example payload: [examples/sample_job.json](/c:/Users/RGSek/parallel/parallel-uploads/examples/sample_job.json)

### Notes
- `asset.local_path` is supported for local testing.
- `asset.s3_key` is the intended production path and matches your presign + asset record flow.
- YouTube jobs download the asset from S3 to a temporary local file before upload.
- Instagram jobs generate a presigned `GET` URL for the existing S3 object and publish from that URL.

### Test the Instagram API directly
You can call the test Instagram API with a fresh presigned URL using:

```powershell
python test_instagram_api.py --s3-key "1/your-video.mp4" --caption "test caption"
```

## Instagram Lambda Handler
There is now a Lambda-oriented handler at [process_instagram_job.py](/c:/Users/RGSek/parallel/parallel-uploads/lambda_handlers/process_instagram_job.py).

Expected event shape:
```json
{
  "job_id": 5
}
```

What it does:
- loads the job, asset, and connected account from MySQL
- verifies the job is for Instagram
- marks the job as `processing`
- generates a presigned `GET` URL for the S3 asset
- publishes the Reel through the existing Instagram helper
- updates `upload_jobs` to `completed` or `failed`

Required Lambda environment variables:
- `DB_HOST`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `DB_PORT` (optional)
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `INSTAGRAM_ACCOUNT_ID`
- `FB_GRAPH_TOKEN_LONG`
- `ASSET_BUCKET` (optional, defaults to `parallel-uploads-videos`)

