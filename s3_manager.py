"""
Boto3 logic for S3 file discovery and pre-signed URLs.

Bucket: intelli-extract-tech-challenge-891377258245
Used for URL-path tests: list objects, generate pre-signed GET URLs.
"""

import os
from pathlib import Path
from typing import List

import boto3
from botocore.exceptions import ClientError
from tqdm import tqdm

DEFAULT_BUCKET = "intelli-extract-tech-challenge-891377258245"
DEFAULT_EXPIRY = 3600  # seconds


def get_s3_client(region: str | None = None):
    """Return boto3 S3 client using default credential chain."""
    return boto3.client("s3", region_name=region or os.environ.get("AWS_REGION", "us-east-1"))


# Default extensions for spreadsheet/Excel/CSV (configurable via --formats)
DEFAULT_ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv", ".ods"]


def _key_matches_extensions(key: str, allowed_extensions: List[str] | None) -> bool:
    """True if allowed_extensions is None or key ends with one of them (case-insensitive)."""
    if not allowed_extensions:
        return True
    key_lower = key.lower()
    for ext in allowed_extensions:
        e = ext.lower().strip()
        if e and not e.startswith("."):
            e = "." + e
        if e and key_lower.endswith(e):
            return True
    return False


def list_object_keys(
    bucket: str = DEFAULT_BUCKET,
    prefix: str = "",
    max_keys: int = 1000,
    region: str | None = None,
    allowed_extensions: List[str] | None = None,
) -> List[str]:
    """
    List object keys in the bucket under the given prefix.
    MaxKeys controls the PAGE size if we use paginator? 
    Actually, we want to stop after collecting max_keys items.
    """
    client = get_s3_client(region=region)
    keys: List[str] = []
    
    # Use PaginationConfig to enforce strict limit on total items
    paginator = client.get_paginator("list_objects_v2")
    
    # MaxItems limit global results. PageSize controls per-request.
    page_iterator = paginator.paginate(
        Bucket=bucket, 
        Prefix=prefix, 
        PaginationConfig={'MaxItems': max_keys, 'PageSize': min(1000, max_keys)}
    )

    for page in page_iterator:
        for obj in page.get("Contents") or []:
            key = obj.get("Key")
            if key and _key_matches_extensions(key, allowed_extensions):
                keys.append(key)
                if len(keys) >= max_keys:
                    return keys
    return keys


def generate_presigned_url(
    bucket: str,
    key: str,
    expiry: int = DEFAULT_EXPIRY,
    region: str | None = None,
) -> str:
    """
    Generate a pre-signed GET URL for the object.

    Returns:
        Pre-signed URL string.
    """
    client = get_s3_client(region=region)
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry,
        )
        return url
    except ClientError as e:
        raise RuntimeError(f"Failed to generate pre-signed URL for s3://{bucket}/{key}: {e}") from e


def get_presigned_urls_for_prefix(
    bucket: str = DEFAULT_BUCKET,
    prefix: str = "",
    expiry: int = DEFAULT_EXPIRY,
    region: str | None = None,
    allowed_extensions: List[str] | None = None,
    limit: int | None = None,
) -> List[tuple[str, str]]:
    """
    List keys under prefix and return (key, presigned_url) pairs.
    Only keys whose extension is in allowed_extensions are included (if provided).
    Key can be used as file_name for reporting (e.g. basename).
    """
    keys = list_object_keys(
        bucket=bucket,
        prefix=prefix,
        region=region,
        allowed_extensions=allowed_extensions,
        max_keys=limit if limit else 1000,
    )
    return [
        (key, generate_presigned_url(bucket, key, expiry=expiry, region=region))
        for key in keys
    ]


def download_file(bucket: str, key: str, local_path: Path, region: str | None = None) -> None:
    """Download an S3 object to a local path."""
    client = get_s3_client(region=region)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, key, str(local_path))


def sync_prefix_to_local(
    bucket: str = DEFAULT_BUCKET,
    prefix: str = "",
    local_dir: str | Path = "./staging",
    region: str | None = None,
    allowed_extensions: List[str] | None = None,
    limit: int | None = None,
) -> List[Path]:
    """
    Sync files from S3 prefix to local_dir.
    Skips if file exists and size matches.
    Returns list of local file paths.
    """
    local_dir_path = Path(local_dir)
    local_dir_path.mkdir(parents=True, exist_ok=True)
    
    keys = list_object_keys(
        bucket=bucket,
        prefix=prefix,
        region=region,
        allowed_extensions=allowed_extensions,
        max_keys=limit if limit else 1000,
    )
    
    if limit:
        keys = keys[:limit]

    synced_files: List[Path] = []
    
    # print(f"Syncing {len(keys)} files from s3://{bucket}/{prefix} to {local_dir} ...")
    
    # Calculate total size for better progress? For now just file count.
    with tqdm(total=len(keys), desc=f"Syncing from s3://{bucket}/{prefix}", unit="file") as pbar:
        # Re-create client inside loop/function to avoid thread issues if any, though here it is single threaded sync
        client = get_s3_client(region=region)

        for key in keys:
            # Flatten structure or keep? "folder/file.ext" -> "folder_file.ext" to avoid deep nesting issues?
            # Or just keep base name if unique?
            # Let's keep original structure relative to prefix, or just flat if simple.
            # For simplicity in this specific project context (often flat buckets), let's use the basename
            # but warn if duplicates? 
            # Actually safer to keep relative path structure if possible, but strict requirements say "dataset is in production under brand-specific buckets".
            # So "BrandA/file1.xlsx".
            # Let's construct local path preserving hierarchy.
            
            # If prefix is "data/", and key is "data/brand/file.xlsx", we want "brand/file.xlsx" inside local_dir?
            # Or just full key? Let's use full key to be safe against collisions.
            safe_key_path = Path(key)
            # Remove drive letter if any (unlikely in S3 key) 
            
            target_path = local_dir_path / safe_key_path
            
            # Check if exists and size matches
            should_download = True
            if target_path.exists():
                # efficient check: size
                try:
                    resp = client.head_object(Bucket=bucket, Key=key)
                    remote_size = resp["ContentLength"]
                    if target_path.stat().st_size == remote_size:
                        should_download = False
                except Exception:
                    # If head fails, re-download to be safe
                    pass
            
            if should_download:
                # print(f"Downloading {key} -> {target_path}")
                download_file(bucket, key, target_path, region=region)
                
            synced_files.append(target_path)
            pbar.update(1)
            
    return synced_files
