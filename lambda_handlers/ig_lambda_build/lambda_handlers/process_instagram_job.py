import json
import os
import tempfile

import pymysql

from utils.instagram.aws_s3_manager import (
    delete_file_from_aws_s3,
    download_file_from_aws_s3,
    generate_presigned_get_url,
    upload_file_to_aws_s3,
)
from utils.instagram.upload_instagram import ig_publish_video


DEFAULT_S3_BUCKET = "parallel-uploads-videos"


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _get_db_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        port=int(os.environ.get("DB_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def _extract_job_id(event):
    if isinstance(event, dict):
        if "job_id" in event:
            return int(event["job_id"])
        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)
        if isinstance(body, dict) and "job_id" in body:
            return int(body["job_id"])
    raise ValueError("Missing job_id in event.")


def _load_job(cursor, job_id):
    sql = """
        SELECT
            uj.id,
            uj.asset_id,
            uj.connected_account_id,
            uj.status,
            uj.platform_specific_metadata,
            uj.is_live,
            a.s3_key,
            a.original_filename,
            a.caption,
            ca.platform
        FROM upload_jobs uj
        JOIN assets a ON a.id = uj.asset_id
        JOIN connected_accounts ca ON ca.id = uj.connected_account_id
        WHERE uj.id = %s
    """
    cursor.execute(sql, (job_id,))
    return cursor.fetchone()


def _mark_processing(cursor, job_id):
    cursor.execute(
        """
        UPDATE upload_jobs
        SET status = 'processing', error_message = NULL
        WHERE id = %s
        """,
        (job_id,),
    )


def _mark_completed(cursor, job_id, platform_post_id):
    cursor.execute(
        """
        UPDATE upload_jobs
        SET
            status = 'completed',
            platform_post_id = %s,
            posted_at = NOW(),
            error_message = NULL,
            is_live = 1
        WHERE id = %s
        """,
        (platform_post_id, job_id),
    )


def _mark_failed(cursor, job_id, error_message):
    cursor.execute(
        """
        UPDATE upload_jobs
        SET
            status = 'failed',
            error_message = %s,
            is_live = 0
        WHERE id = %s
        """,
        (error_message[:1000], job_id),
    )


def _prepare_reuploaded_video_url(job, bucket):
    suffix = os.path.splitext(job.get("original_filename") or job["s3_key"])[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        temp_path = tmp_file.name

    print(f"[worker-debug] Using S3 bucket: {bucket}")
    print(f"[worker-debug] Downloading source asset key {job['s3_key']} to {temp_path}")
    download_file_from_aws_s3(job["s3_key"], temp_path, bucket=bucket)

    print("[worker-debug] Re-uploading asset through local-success S3 helper path")
    uploaded = upload_file_to_aws_s3(temp_path, bucket=bucket)
    if not uploaded:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise RuntimeError("Failed to re-upload asset through helper path.")

    video_url, temp_object_key = uploaded
    print(f"[worker-debug] Re-uploaded object key: {temp_object_key}")
    print(f"[worker-debug] Re-uploaded video URL: {video_url}")
    return video_url, temp_path, temp_object_key


def lambda_handler(event, context):
    conn = None
    cursor = None

    try:
        job_id = _extract_job_id(event)
    except Exception as exc:
        return _response(400, {"message": "invalid request", "error": str(exc)})

    try:
        conn = _get_db_connection()
        cursor = conn.cursor()

        job = _load_job(cursor, job_id)
        if not job:
            conn.rollback()
            return _response(404, {"message": "job not found", "job_id": job_id})

        if job["platform"].lower() != "instagram":
            conn.rollback()
            return _response(400, {"message": "job is not an Instagram job", "job_id": job_id})

        _mark_processing(cursor, job_id)
        conn.commit()

        metadata = job.get("platform_specific_metadata") or {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        caption = metadata.get("caption") or metadata.get("description") or job.get("caption") or ""
        s3_bucket = metadata.get("s3_bucket") or os.environ.get("ASSET_BUCKET", DEFAULT_S3_BUCKET)
        original_asset_url = generate_presigned_get_url(job["s3_key"], bucket=s3_bucket)
        print(f"[worker-debug] Original asset presigned URL: {original_asset_url}")

        temp_path = None
        temp_object_key = None
        try:
            video_url, temp_path, temp_object_key = _prepare_reuploaded_video_url(job, s3_bucket)
            platform_post_id = ig_publish_video(video_url, caption)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            if temp_object_key:
                delete_file_from_aws_s3(temp_object_key, bucket=s3_bucket)

        cursor = conn.cursor()
        _mark_completed(cursor, job_id, platform_post_id)
        conn.commit()

        return _response(
            200,
            {
                "message": "instagram job completed",
                "job_id": job_id,
                "platform_post_id": platform_post_id,
            },
        )

    except Exception as exc:
        if conn:
            try:
                cursor = conn.cursor()
                _mark_failed(cursor, job_id, str(exc))
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        return _response(
            500,
            {
                "message": "instagram job failed",
                "job_id": job_id,
                "error": str(exc),
            },
        )

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass
