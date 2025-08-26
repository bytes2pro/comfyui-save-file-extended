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


def _parse_endpoint_bucket_key(bucket_link: str, cloud_folder_path: str, filename: str) -> Tuple[str, str, str]:
    """
    Accepts bucket_link like:
      - https://endpoint.example.com/bucket[/prefix]
    Returns (endpoint_url, bucket, key)
    """
    parsed = urlparse(bucket_link)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("S3-Compatible requires an http(s) endpoint URL, e.g. https://endpoint/bucket")
    path_parts = parsed.path.lstrip("/").split("/", 1)
    bucket = path_parts[0]
    base_prefix = path_parts[1] if len(path_parts) > 1 else ""

    parts = [p for p in [base_prefix, cloud_folder_path] if p]
    prefix = "/".join([p.strip("/") for p in parts if p.strip("/")])
    key = f"{prefix + '/' if prefix else ''}{filename}"

    endpoint_url = f"{parsed.scheme}://{parsed.netloc}"
    return endpoint_url, bucket, key


class Uploader:
    @staticmethod
    def _create_client(api_key: str, endpoint_url: str):
        import boto3
        access_key, secret_key, region = _parse_credentials(api_key)
        client_kwargs: Dict[str, Any] = {"endpoint_url": endpoint_url}
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key
        if region:
            client_kwargs["region_name"] = region
        return boto3.client("s3", **client_kwargs)
    
    @staticmethod
    def upload(image_bytes: bytes, filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> Dict[str, Any]:
        import boto3

        endpoint_url, bucket, key = _parse_endpoint_bucket_key(bucket_link, cloud_folder_path, filename)
        s3 = Uploader._create_client(api_key, endpoint_url)
        s3.put_object(Bucket=bucket, Key=key, Body=image_bytes, ContentType="image/png")

        url = f"{endpoint_url}/{bucket}/{key}"
        return {
            "provider": "S3-Compatible",
            "bucket": bucket,
            "path": key,
            "url": url,
        }

    @staticmethod
    def upload_many(items: list[Dict[str, Any]], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        import boto3

        endpoint_url, bucket, _ = _parse_endpoint_bucket_key(bucket_link, cloud_folder_path, "dummy")
        s3 = Uploader._create_client(api_key, endpoint_url)
        results: list[Dict[str, Any]] = []
        for item in items:
            filename = item["filename"]
            body = item["content"]
            _, bucket_name, key = _parse_endpoint_bucket_key(bucket_link, cloud_folder_path, filename)
            s3.put_object(Bucket=bucket_name, Key=key, Body=body, ContentType="image/png")
            url = f"{endpoint_url}/{bucket_name}/{key}"
            results.append({"provider": "S3-Compatible", "bucket": bucket_name, "path": key, "url": url})
        return results

    @staticmethod
    def download(key_or_filename: str, bucket_link: str, cloud_folder_path: str, api_key: str) -> bytes:
        import boto3

        endpoint_url, bucket, key = _parse_endpoint_bucket_key(bucket_link, cloud_folder_path, key_or_filename)
        s3 = Uploader._create_client(api_key, endpoint_url)
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()

    @staticmethod
    def download_many(keys: list[str], bucket_link: str, cloud_folder_path: str, api_key: str) -> list[Dict[str, Any]]:
        import boto3

        endpoint_url, _, _ = _parse_endpoint_bucket_key(bucket_link, cloud_folder_path, "dummy")
        s3 = Uploader._create_client(api_key, endpoint_url)

        results: list[Dict[str, Any]] = []
        for name in keys:
            _, bucket, key = _parse_endpoint_bucket_key(bucket_link, cloud_folder_path, name)
            obj = s3.get_object(Bucket=bucket, Key=key)
            results.append({"filename": name, "content": obj["Body"].read()})
        return results


