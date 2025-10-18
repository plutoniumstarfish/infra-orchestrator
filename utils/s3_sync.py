import hashlib
import subprocess
import json
import os

def calculate_sha256(file_path):
    """Calculate SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_s3_object_etag(bucket, key):
    """Get checksum metadata (or ETag) from S3 object."""
    try:
        result = subprocess.run(
            ["aws", "s3api", "head-object", "--bucket", bucket, "--key", key],
            check=True, capture_output=True, text=True
        )
        info = json.loads(result.stdout)
        if "Metadata" in info and "sha256" in info["Metadata"]:
            return info["Metadata"]["sha256"]
        return info.get("ETag", "").replace('"', "")
    except subprocess.CalledProcessError:
        return None

def upload_to_s3_if_changed(local_file, s3_uri):
    """Upload file to S3 if checksum differs."""
    assert s3_uri.startswith("s3://"), "Invalid S3 URI"
    _, _, bucket_and_key = s3_uri.partition("s3://")
    bucket, _, key = bucket_and_key.partition("/")

    print(f"🧩 Checking {local_file} against s3://{bucket}/{key}")

    local_sha = calculate_sha256(local_file)
    remote_sha = get_s3_object_etag(bucket, key)

    if local_sha == remote_sha:
        print(f"✅ No change detected (SHA256: {local_sha}). Skipping upload.")
        return False

    print(f"⬆️ Uploading new version (SHA256: {local_sha})...")
    subprocess.run([
        "aws", "s3api", "put-object",
        "--bucket", bucket,
        "--key", key,
        "--body", local_file,
        "--metadata", f"sha256={local_sha}"
    ], check=True)
    print(f"✅ Uploaded {local_file} to s3://{bucket}/{key}")
    return True
