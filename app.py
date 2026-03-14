import json
import os

import requests
from flask import Flask, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge

from utils.instagram.aws_s3_manager import generate_presigned_get_url


API_BASE_URL = "https://v48jp37m05.execute-api.us-east-2.amazonaws.com/prod"
DEFAULT_USER_ID = 1
YOUTUBE_CONNECTED_ACCOUNT_ID = 1
INSTAGRAM_CONNECTED_ACCOUNT_ID = 2
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".webm"}


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def render_form(form_data=None, results=None, error=None, status_code=200):
    return render_template(
        "index.html",
        form_data=form_data or {},
        results=results,
        error=error,
    ), status_code


def parse_lambda_response(response):
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and "body" in payload:
        body = payload["body"]
        if isinstance(body, str):
            return json.loads(body)
        if isinstance(body, dict):
            return body
    return payload


def create_presigned_upload(filename, content_type):
    response = requests.post(
        f"{API_BASE_URL}/assets/presign",
        json={
            "user_id": DEFAULT_USER_ID,
            "filename": filename,
            "content_type": content_type,
        },
        timeout=30,
    )
    return parse_lambda_response(response)


def upload_file_to_presigned_url(upload_url, file_storage):
    file_storage.stream.seek(0)
    response = requests.put(
        upload_url,
        data=file_storage.stream,
        headers={"Content-Type": "binary/octet-stream"},
        timeout=300,
    )
    response.raise_for_status()


def create_asset_record(s3_key, original_filename, caption, hashtags):
    response = requests.post(
        f"{API_BASE_URL}/assets",
        json={
            "user_id": DEFAULT_USER_ID,
            "s3_key": s3_key,
            "original_filename": original_filename,
            "caption": caption,
            "hashtags": hashtags,
        },
        timeout=30,
    )
    return parse_lambda_response(response)


def create_upload_jobs(asset_id, title, description, keywords, privacy_status, platforms):
    jobs = []
    for platform in platforms:
        if platform == "instagram":
            connected_account_id = INSTAGRAM_CONNECTED_ACCOUNT_ID
        else:
            connected_account_id = YOUTUBE_CONNECTED_ACCOUNT_ID

        jobs.append(
            {
                "connected_account_id": connected_account_id,
                "platform_specific_metadata": {
                    "platform": platform,
                    "title": title,
                    "caption": description,
                    "description": description,
                    "keywords": keywords,
                    "privacy_status": privacy_status,
                },
                "scheduled_at": None,
                "is_live": 1,
            }
        )

    response = requests.post(
        f"{API_BASE_URL}/upload_jobs",
        json={
            "asset_id": asset_id,
            "jobs": jobs,
        },
        timeout=30,
    )
    return parse_lambda_response(response)


def build_results(platforms, asset_response, upload_jobs_response, s3_key):
    asset_id = asset_response.get("asset_id")
    jobs = upload_jobs_response.get("upload_jobs", []) if upload_jobs_response else []
    invoke_debug = upload_jobs_response.get("invoke_debug", []) if upload_jobs_response else []
    env_debug = upload_jobs_response.get("env_debug", {}) if upload_jobs_response else {}
    presigned_asset_url = generate_presigned_get_url(
        s3_key,
        bucket=os.environ.get("ASSET_BUCKET", "parallel-uploads-assets-rohan-1"),
    )
    results = {
        "asset": {
            "success": True,
            "value": f"Created asset {asset_id} for S3 key {s3_key}",
        }
    }

    returned_jobs = len(jobs) if isinstance(jobs, list) else 0

    for platform in platforms:
        results[platform] = {
            "success": True,
            "value": f"Created upload job for {platform} on asset {asset_id}. Returned jobs: {returned_jobs}",
        }

    if invoke_debug:
        results["invoke_debug"] = {
            "success": True,
            "value": json.dumps(invoke_debug, indent=2),
        }

    if env_debug:
        results["env_debug"] = {
            "success": True,
            "value": json.dumps(env_debug, indent=2),
        }

    results["asset_url_debug"] = {
        "success": True,
        "value": presigned_asset_url,
    }

    return results


@app.route("/", methods=["GET"])
def index():
    return render_form()


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(_error):
    return render_form(
        error="The selected file is too large for this local server.",
        status_code=413,
    )


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    return render_form(
        error=f"Server error: {error}",
        status_code=500,
    )


@app.route("/upload", methods=["POST"])
def upload():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    keywords = request.form.get("keywords", "").strip()
    privacy_status = request.form.get("privacy_status", "unlisted").strip() or "unlisted"
    platforms = [value.strip().lower() for value in request.form.getlist("platforms") if value]
    hashtags = request.form.get("hashtags", "").strip()
    file = request.files.get("video")

    form_data = {
        "title": title,
        "description": description,
        "keywords": keywords,
        "privacy_status": privacy_status,
        "platforms": platforms,
        "hashtags": hashtags,
    }

    if not title:
        return render_form(form_data=form_data, error="Title is required.", status_code=400)
    if not description:
        return render_form(form_data=form_data, error="Caption/description is required.", status_code=400)
    if not platforms:
        return render_form(form_data=form_data, error="Select at least one platform.", status_code=400)
    if not file or not file.filename:
        return render_form(form_data=form_data, error="Select a video file to upload.", status_code=400)
    if not allowed_file(file.filename):
        return render_form(form_data=form_data, error="Unsupported file type.", status_code=400)

    try:
        presign_response = create_presigned_upload(file.filename, file.mimetype or "application/octet-stream")
        upload_url = presign_response["upload_url"]
        s3_key = presign_response["key"]

        upload_file_to_presigned_url(upload_url, file)
        asset_response = create_asset_record(s3_key, file.filename, description, hashtags)
        upload_jobs_response = create_upload_jobs(
            asset_id=asset_response["asset_id"],
            title=title,
            description=description,
            keywords=keywords,
            privacy_status=privacy_status,
            platforms=platforms,
        )
        results = build_results(platforms, asset_response, upload_jobs_response, s3_key)
        return render_form(form_data=form_data, results=results)
    except requests.HTTPError as exc:
        error_text = exc.response.text if exc.response is not None else str(exc)
        return render_form(form_data=form_data, error=f"API request failed: {error_text}", status_code=502)
    except Exception as exc:
        return render_form(form_data=form_data, error=str(exc), status_code=500)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, threaded=True)
