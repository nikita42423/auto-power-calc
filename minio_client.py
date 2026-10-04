import uuid
from io import BytesIO
from minio import Minio

client = Minio("localhost:9000", access_key="admin", secret_key="passadmin", secure=False)
BUCKET = "auto-power-calc"

def upload_file(file_bytes: bytes, original_name: str) -> str:
    ext = original_name.rsplit(".", 1)[-1] if "." in original_name else "bin"
    filename = f"{uuid.uuid4().hex}.{ext}"
    client.put_object(BUCKET, filename, BytesIO(file_bytes), len(file_bytes))
    return f"http://localhost:9000/{BUCKET}/{filename}"