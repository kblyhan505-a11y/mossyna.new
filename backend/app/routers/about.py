"""
MOSSYNA BACKEND — Hakkımızda (Üretim Tesisi Fotoğrafları)

Ana sayfadaki '#about' bölümünde gösterilen fotoğraflar. Admin panelinde
(hakkimizda.html) yüklenir; sunucu tarafında Pillow ile 4:3 oranında (640x480)
merkezden otomatik kırpılır — bu, admin panelindeki tarayıcı-içi (canvas)
önizlemeyle AYNI orandır, böylece admin'in gördüğü önizleme gerçek sonuçla eşleşir
(bkz. admin/js/hakkimizda-admin.js, mossynaCropImageCenter).
"""
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.security import get_current_admin
from app.services import storage

router = APIRouter(tags=["Hakkımızda"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB (yükleme sonrası kırpılıp küçültülür)
CROP_RATIO = 4 / 3
CROP_WIDTH = 640
CROP_HEIGHT = 480


def _crop_center_4_3(contents: bytes) -> bytes:
    """admin/js/hakkimizda-admin.js'teki tarayıcı-içi canvas kırpmasının birebir
    sunucu taraflı karşılığı: aynı 4:3 oran, aynı 640x480 hedef boyut."""
    from PIL import Image  # yalnızca bu uç çağrıldığında import edilir

    image = Image.open(io.BytesIO(contents))
    image = image.convert("RGB")  # PNG/WEBP şeffaflığı JPEG'e taşınamaz — beyaza düşer
    width, height = image.size
    src_ratio = width / height

    if src_ratio > CROP_RATIO:
        new_width = round(height * CROP_RATIO)
        left = (width - new_width) // 2
        box = (left, 0, left + new_width, height)
    else:
        new_height = round(width / CROP_RATIO)
        top = (height - new_height) // 2
        box = (0, top, width, top + new_height)

    cropped = image.crop(box).resize((CROP_WIDTH, CROP_HEIGHT), Image.LANCZOS)
    buffer = io.BytesIO()
    cropped.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


# ---------------------------------------------------------------------
# PUBLIC — frontend anasayfa '#about' bölümü bu ucu kullanır
# ---------------------------------------------------------------------

@router.get("/api/about-photos", response_model=list[schemas.AboutUsPhotoResponse])
def list_about_photos(db: Session = Depends(get_db)):
    return db.scalars(
        select(models.AboutUsPhoto).order_by(models.AboutUsPhoto.sort_order, models.AboutUsPhoto.id)
    ).all()


# ---------------------------------------------------------------------
# ADMIN — admin/hakkimizda.html bu uçları kullanır (JWT audience=admin gerekir)
# ---------------------------------------------------------------------

@router.get("/api/admin/about-photos", response_model=list[schemas.AboutUsPhotoResponse])
def admin_list_about_photos(db: Session = Depends(get_db), _admin: models.AdminUser = Depends(get_current_admin)):
    return db.scalars(
        select(models.AboutUsPhoto).order_by(models.AboutUsPhoto.sort_order, models.AboutUsPhoto.id)
    ).all()


@router.post("/api/admin/about-photos", response_model=schemas.AboutUsPhotoResponse, status_code=status.HTTP_201_CREATED)
async def admin_upload_about_photo(
    file: UploadFile = File(...),
    caption_tr: str | None = Form(default=None),
    caption_en: str | None = Form(default=None),
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Sadece JPG, PNG veya WEBP yüklenebilir.")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Görsel 8MB'dan büyük olamaz.")

    try:
        cropped_bytes = _crop_center_4_3(contents)
    except Exception as exc:  # noqa: BLE001 — bozuk/okunamayan görsel dosyası
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Görsel işlenemedi: {exc}")

    # storage.save_image ürün görselleri için tasarlanmıştı (bkz. services/storage.py)
    # ama aynı arayüz burada da sorunsuz çalışır — product_id yerine sabit 0
    # ("genel/kurumsal görsel" klasörü) kullanılır.
    image_url = storage.save_image(0, "about.jpg", cropped_bytes)

    next_sort_order = (db.scalar(select(func.max(models.AboutUsPhoto.sort_order))) or 0) + 1
    photo = models.AboutUsPhoto(
        image_url=image_url,
        caption_tr=(caption_tr or None),
        caption_en=(caption_en or None),
        sort_order=next_sort_order,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


@router.put("/api/admin/about-photos/{photo_id}", response_model=schemas.AboutUsPhotoResponse)
def admin_update_about_photo(
    photo_id: int,
    payload: schemas.AboutUsPhotoUpdateRequest,
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    photo = db.get(models.AboutUsPhoto, photo_id)
    if not photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fotoğraf bulunamadı.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(photo, field, value)
    db.commit()
    db.refresh(photo)
    return photo


@router.delete("/api/admin/about-photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_about_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    photo = db.get(models.AboutUsPhoto, photo_id)
    if not photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fotoğraf bulunamadı.")
    storage.delete_image(photo.image_url)
    db.delete(photo)
    db.commit()
