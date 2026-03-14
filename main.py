import argparse
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.instagram.aws_s3_manager import (
    delete_file_from_aws_s3,
    download_file_from_aws_s3,
    generate_presigned_get_url,
    upload_file_to_aws_s3,
)
from utils.instagram.upload_instagram import ig_publish_video
from utils.youtube.upload_youtube import upload_youtube

# contact me at AzimUsmanov2027@u.northwestern.edu for more info or documentation


DEFAULT_YOUTUBE_CATEGORY = "22"
DEFAULT_YOUTUBE_PRIVACY = "unlisted"
DEFAULT_S3_BUCKET = "parallel-uploads-assets-rohan1"


def normalize_job(job):
    asset = job.get("asset") or {}
    metadata = job.get("platform_specific_metadata") or {}
    connected_account = job.get("connected_account") or {}

    platform = (
        job.get("platform")
        or connected_account.get("platform")
        or metadata.get("platform")
    )
    if not platform:
        raise ValueError("Job is missing a platform.")

    normalized = {
        "id": job.get("id"),
        "asset": asset,
        "connected_account": connected_account,
        "platform": platform.strip().lower(),
        "platform_specific_metadata": metadata,
        "status": job.get("status", "pending"),
    }
    return normalized


def _download_asset_for_job(asset):
    local_path = asset.get("local_path")
    if local_path:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local asset file not found: {local_path}")
        return local_path, False

    s3_key = asset.get("s3_key")
    if not s3_key:
        raise ValueError("Asset is missing both local_path and s3_key.")

    bucket = asset.get("s3_bucket", DEFAULT_S3_BUCKET)
    suffix = os.path.splitext(asset.get("original_filename") or s3_key)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        temp_path = tmp_file.name

    download_file_from_aws_s3(s3_key, temp_path, bucket=bucket)
    return temp_path, True


def _resolve_instagram_video_url(asset):
    local_path = asset.get("local_path")
    if local_path:
        aws_url, object_key = upload_file_to_aws_s3(local_path)
        if not aws_url or not object_key:
            raise RuntimeError("Failed to upload the local asset to S3 for Instagram.")
        return aws_url, object_key

    s3_key = asset.get("s3_key")
    if not s3_key:
        raise ValueError("Instagram job asset is missing s3_key.")

    bucket = asset.get("s3_bucket", DEFAULT_S3_BUCKET)
    return generate_presigned_get_url(s3_key, bucket=bucket), None


def process_job(job):
    normalized = normalize_job(job)
    asset = normalized["asset"]
    metadata = normalized["platform_specific_metadata"]
    platform = normalized["platform"]
    title = metadata.get("title") or asset.get("title") or asset.get("original_filename") or "Untitled Upload"
    description = metadata.get("description") or asset.get("caption") or ""

    result = {
        "job_id": normalized["id"],
        "platform": platform,
        "status": "processing",
    }

    if platform == "youtube":
        filepath = None
        should_cleanup = False
        try:
            filepath, should_cleanup = _download_asset_for_job(asset)
            result_url = upload_youtube(
                filepath,
                title,
                description,
                metadata.get("category", DEFAULT_YOUTUBE_CATEGORY),
                metadata.get("keywords", ""),
                metadata.get("privacy_status", DEFAULT_YOUTUBE_PRIVACY),
            )
            result.update(
                status="completed",
                result_url=result_url,
                platform_post_id=result_url.rsplit("=", 1)[-1],
            )
        except Exception as exc:
            result.update(status="failed", error_message=str(exc))
        finally:
            if filepath and should_cleanup and os.path.exists(filepath):
                os.remove(filepath)
        return result

    if platform == "instagram":
        temp_object_key = None
        try:
            video_url, temp_object_key = _resolve_instagram_video_url(asset)
            publish_id = ig_publish_video(video_url, description)
            result.update(
                status="completed",
                platform_post_id=publish_id,
                result_url=f"https://www.instagram.com/p/{publish_id}/",
            )
        except Exception as exc:
            result.update(status="failed", error_message=str(exc))
        finally:
            if temp_object_key:
                delete_file_from_aws_s3(temp_object_key)
        return result

    raise ValueError(f"Unsupported platform: {platform}")


def process_jobs(jobs):
    if not jobs:
        raise ValueError("No jobs provided.")

    results = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
        future_map = {executor.submit(process_job, job): job for job in jobs}
        for future in as_completed(future_map):
            results.append(future.result())
    return results


def build_jobs_from_upload_request(
    filepath,
    title,
    description,
    platforms,
    keywords="",
    privacy_status=DEFAULT_YOUTUBE_PRIVACY,
    category=DEFAULT_YOUTUBE_CATEGORY,
):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Video file not found: {filepath}")
    if not platforms:
        raise ValueError("Select at least one platform.")

    asset = {
        "local_path": filepath,
        "original_filename": os.path.basename(filepath),
        "title": title,
        "caption": description,
    }
    jobs = []

    for platform in {value.strip().lower() for value in platforms if value}:
        metadata = {
            "title": title,
            "description": description,
        }
        if platform == "youtube":
            metadata.update(
                keywords=keywords,
                privacy_status=privacy_status,
                category=category,
            )
        jobs.append(
            {
                "platform": platform,
                "asset": asset,
                "platform_specific_metadata": metadata,
                "status": "pending",
            }
        )

    return jobs


def run_uploads(
    filepath,
    title,
    description,
    platforms,
    keywords="",
    privacy_status=DEFAULT_YOUTUBE_PRIVACY,
    category=DEFAULT_YOUTUBE_CATEGORY,
):
    jobs = build_jobs_from_upload_request(
        filepath=filepath,
        title=title,
        description=description,
        platforms=platforms,
        keywords=keywords,
        privacy_status=privacy_status,
        category=category,
    )
    processed = process_jobs(jobs)
    results = {}

    for item in processed:
        platform = item["platform"]
        if item["status"] == "completed":
            results[platform] = {"success": True, "value": item.get("result_url") or item.get("platform_post_id")}
        else:
            results[platform] = {"success": False, "error": item.get("error_message", "Unknown error")}

    return results


def load_jobs_from_file(job_file):
    with open(job_file, "r", encoding="utf-8") as infile:
        payload = json.load(infile)

    if isinstance(payload, dict) and "jobs" in payload:
        jobs = payload["jobs"]
    elif isinstance(payload, list):
        jobs = payload
    else:
        jobs = [payload]

    return jobs


def main():
    parser = argparse.ArgumentParser(description="Process one or more upload jobs.")
    parser.add_argument("--job-file", help="Path to a JSON job payload or a JSON object with a jobs array.")
    args = parser.parse_args()

    if args.job_file:
        results = process_jobs(load_jobs_from_file(args.job_file))
    else:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_files", "test_file_1.mp4")
        jobs = build_jobs_from_upload_request(
            filepath=filepath,
            title="AK going crazy",
            description="Test Description",
            platforms=["youtube", "instagram"],
            keywords="test,upload",
        )
        results = process_jobs(jobs)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
