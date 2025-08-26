from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse


def _parse_credentials(api_key: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse credentials from api_key which can be:
      - JSON: {"access_key": "...", "secret_key": "...", "region": "us-east-1"}
      - Colon separated: ACCESS_KEY:SECRET_KEY[:REGION]
    Returns (access_key, secret_key, region)
    """
    access_key = None
    secret_key = None
    region = None
    if not api_key:
        return access_key, secret_key, region
    api_key = api_key.strip()
    if api_key.startswith("{"):
        try:
            data = json.loads(api_key)
            access_key = data.get("access_key") or data.get("aws_access_key_id")
            secret_key = data.get("secret_key") or data.get("aws_secret_access_key")
            region = data.get("region")
        except Exception:
            pass
    elif ":" in api_key:
        parts = api_key.split(":")
        if len(parts) >= 2:
            access_key, secret_key = parts[0], parts[1]
        if len(parts) >= 3:
            region = parts[2]
    return access_key, secret_key, region


def _parse_bucket_and_key(bucket_link: str, cloud_folder_path: str, filename: str) -> Tuple[str, str]:
    """
    Accepts bucket_link like:
      - s3://bucket
      - s3://bucket/prefix
    Returns (bucket, key)
    """
    parsed = urlparse(bucket_link)
    if parsed.scheme != "s3":
        # Allow raw bucket name
        bucket = bucket_link.strip().split("/")[0]
        base_prefix = "/".join(bucket_link.strip().split("/")[1:])
    else:
        bucket = parsed.netloc
        base_prefix = parsed.path.lstrip("/")

    parts = [p for p in [base_prefix, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in parts if p.strip("/")])
    key = f"{prefix + '/' if prefix else ''}{filename}"
    return bucket, key


class Uploader:
    @staticmethod
    def _create_client(api_key: str):
        import boto3
        access_key, secret_key, region = _parse_credentials(api_key)
        client_kwargs: Dict[str, Any] = {}
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key
        if region:
            client_kwargs["region_name"] = region
        return boto3.client("s3", **client_kwargs)
    
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        import boto3

        bucket, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, filename)
        s3 = Uploader._create_client(api_key)
        s3.put_object(Bucket=bucket, Key=key, Body=image_bytes, ContentType="image/png")

        url = f"https://{bucket}.s3.amazonaws.com/{key}"
        return {
            "provider": "AWS S3",
            "bucket": bucket,
            "path": key,
            "url": url,
        }

    @staticmethod
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        import boto3

        s3 = Uploader._create_client(api_key)

        results: list[Dict[str, Any]] = []
        for item in items:
            filename = item["filename"]
            body = item["content"]
            bucket, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, filename)
            s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType="image/png")
            url = f"https://{bucket}.s3.amazonaws.com/{key}"
            results.append({"provider": "AWS S3", "bucket": bucket, "path": key, "url": url})
        return results

    @staticmethod
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        import boto3

        bucket, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, key_or_filename)
        s3 = Uploader._create_client(api_key)
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()

    @staticmethod
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        import boto3

        s3 = Uploader._create_client(api_key)

        results: list[Dict[str, Any]] = []
        for name in keys:
            bucket, key = _parse_bucket_and_key(bucket_link, cloud_folder_path, name)
            obj = s3.get_object(Bucket=bucket, Key=key)
            results.append({"filename": name, "content": obj["Body"].read()})
        return results


