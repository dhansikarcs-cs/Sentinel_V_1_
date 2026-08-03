import logging
import os

logger = logging.getLogger("sentinel.storage")


class ObjectStorage:
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    def get(self, key: str) -> bytes | None:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError

    def get_url(self, key: str, expires: int = 3600) -> str:
        raise NotImplementedError


class LocalObjectStorage(ObjectStorage):
    def __init__(self, base_dir: str = "./data/uploads"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = os.path.join(self.base_dir, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def get(self, key: str) -> bytes | None:
        path = os.path.join(self.base_dir, key)
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    def delete(self, key: str) -> bool:
        path = os.path.join(self.base_dir, key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def get_url(self, key: str, expires: int = 3600) -> str:
        return f"/uploads/{key}"


class S3ObjectStorage(ObjectStorage):
    def __init__(self, bucket: str = "", region: str = "us-east-1"):
        self.bucket = bucket
        self.region = region

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        try:
            import boto3

            s3 = boto3.client("s3", region_name=self.region)
            s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
            return f"s3://{self.bucket}/{key}"
        except Exception as e:
            logger.error("S3 put failed: %s", e)
            raise

    def get(self, key: str) -> bytes | None:
        try:
            import boto3

            s3 = boto3.client("s3", region_name=self.region)
            resp = s3.get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()
        except Exception as e:
            logger.error("S3 get failed: %s", e)
            return None

    def delete(self, key: str) -> bool:
        try:
            import boto3

            s3 = boto3.client("s3", region_name=self.region)
            s3.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def get_url(self, key: str, expires: int = 3600) -> str:
        try:
            import boto3

            s3 = boto3.client("s3", region_name=self.region)
            return s3.generate_presigned_url(
                "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires
            )
        except Exception:
            return ""


storage: ObjectStorage = LocalObjectStorage()
