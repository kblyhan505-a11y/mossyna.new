"""
MOSSYNA BACKEND — Görsel Depolama Soyutlaması

İki modu destekler:
  - "local"  : Geliştirme ortamı. Dosyalar backend/media/ altına yazılır ve
               main.py'deki StaticFiles mount'u ile /media altında servis edilir.
               UYARI: Bu mod, birden fazla backend kopyasının (autoscaling)
               çalıştığı bir production kurulumunda ÇALIŞMAZ — her instance'ın
               diski ayrıdır, bir instance'a yüklenen görsel diğerinde görünmez.
  - "s3"     : Production için önerilen mod. Cloudflare R2 (S3 uyumlu API) ya
               da herhangi bir S3 uyumlu nesne depolamaya yükler; tüm instance'lar
               aynı bucket'ı paylaştığı için autoscaling ile sorunsuz çalışır.

Hangi modun aktif olduğu `STORAGE_BACKEND` ortam değişkeniyle belirlenir
(bkz. app/config.py, .env.example, render.yaml).
"""
import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


def _local_save(product_id: int, filename_hint: str, contents: bytes) -> str:
    media_dir = Path(settings.media_root) / "products" / str(product_id)
    media_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(filename_hint or "image.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{extension}"
    (media_dir / filename).write_bytes(contents)
    return f"/media/products/{product_id}/{filename}"


def _local_delete(image_url: str) -> None:
    # image_url biçimi: /media/products/{id}/{dosya}
    relative = image_url.removeprefix("/media/")
    path = Path(settings.media_root) / relative
    path.unlink(missing_ok=True)


def _s3_client():
    import boto3  # yalnızca s3 modu aktifken import edilir (local modda boto3 zorunlu değildir)

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name="auto",
    )


def _s3_save(product_id: int, filename_hint: str, contents: bytes) -> str:
    extension = Path(filename_hint or "image.jpg").suffix or ".jpg"
    key = f"products/{product_id}/{uuid.uuid4().hex}{extension}"
    client = _s3_client()
    content_type = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
    }.get(extension.lower(), "application/octet-stream")
    client.put_object(Bucket=settings.s3_bucket_name, Key=key, Body=contents, ContentType=content_type)
    base = settings.s3_public_base_url.rstrip("/")
    return f"{base}/{key}"


def _s3_delete(image_url: str) -> None:
    base = settings.s3_public_base_url.rstrip("/")
    if not image_url.startswith(base):
        return  # local moddan kalma eski bir kayıt olabilir — sessizce yoksay
    key = image_url[len(base):].lstrip("/")
    client = _s3_client()
    client.delete_object(Bucket=settings.s3_bucket_name, Key=key)


def save_image(product_id: int, filename_hint: str, contents: bytes) -> str:
    """Görseli aktif depolama arka ucuna kaydeder, herkese açık (public) URL döner."""
    if settings.storage_backend == "s3":
        return _s3_save(product_id, filename_hint, contents)
    return _local_save(product_id, filename_hint, contents)


def delete_image(image_url: str) -> None:
    """Verilen public URL'e karşılık gelen görseli aktif depolama arka ucundan siler."""
    if settings.storage_backend == "s3":
        _s3_delete(image_url)
    else:
        _local_delete(image_url)
