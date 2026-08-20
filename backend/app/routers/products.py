"""
MOSSYNA BACKEND — Ürünler, Kategoriler ve Ürün Görselleri
(Public listeleme + Admin CRUD)
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.security import get_current_admin
from app.services.currency_service import get_latest_rate
from app.services import storage

router = APIRouter(tags=["Ürünler"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _slugify(text: str) -> str:
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    text = text.translate(tr_map).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "urun"


def _generate_unique_slug(db: Session, base_text: str) -> str:
    base = _slugify(base_text)
    slug = base
    suffix = 1
    while db.scalar(select(models.Product).where(models.Product.slug == slug)):
        suffix += 1
        slug = f"{base}-{suffix}"
    return slug


SUPPORTED_TRANSLATION_LANGS = {"de", "fr", "ru", "ar"}


def _upsert_product_translations(
    db: Session,
    product: models.Product,
    translations: dict[str, schemas.ProductTranslationInput] | None,
) -> None:
    """Admin panelindeki DE/FR/RU/AR sekmelerinden gelen çevirileri kaydeder —
    her dil için tek bir satır olacak şekilde var olanı günceller, yoksa oluşturur."""
    if not translations:
        return
    existing = {t.language_code: t for t in product.translations}
    for lang_code, item in translations.items():
        if lang_code not in SUPPORTED_TRANSLATION_LANGS:
            continue  # bilinmeyen/desteklenmeyen dil kodu — sessizce yoksay
        row = existing.get(lang_code)
        if row:
            row.name = item.name
            row.short_desc = item.short_desc
            row.description = item.description
        else:
            db.add(models.ProductTranslation(
                product_id=product.id,
                language_code=lang_code,
                name=item.name,
                short_desc=item.short_desc,
                description=item.description,
            ))


# ---------------------------------------------------------------------
# KATEGORİLER (Public — admin ürün formu ve müşteri filtreleri bunu kullanır)
# ---------------------------------------------------------------------

@router.get("/api/categories", response_model=list[schemas.CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.scalars(select(models.Category).where(models.Category.is_active.is_(True)).order_by(models.Category.sort_order)).all()


# ---------------------------------------------------------------------
# PUBLIC (müşteri arayüzü — frontend/products.html bu uçları tüketir)
# ---------------------------------------------------------------------

@router.get("/api/products", response_model=list[schemas.ProductListItem])
def list_products(
    category: str | None = Query(default=None, description="Kategori slug'ı (ör. 'yatak')"),
    search: str | None = Query(default=None, min_length=1),
    is_featured: bool | None = None,
    sort: str | None = Query(default=None, description="'priceAsc' | 'priceDesc'"),
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(models.Product).where(models.Product.is_active.is_(True))
    if category:
        stmt = stmt.join(models.Category).where(models.Category.slug == category)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(models.Product.name_tr.ilike(like) | models.Product.sku.ilike(like))
    if is_featured is not None:
        stmt = stmt.where(models.Product.is_featured.is_(is_featured))
    if min_price is not None:
        stmt = stmt.where(models.Product.price_try >= min_price)
    if max_price is not None:
        stmt = stmt.where(models.Product.price_try <= max_price)

    if sort == "priceAsc":
        stmt = stmt.order_by(models.Product.price_try.asc())
    elif sort == "priceDesc":
        stmt = stmt.order_by(models.Product.price_try.desc())
    else:
        stmt = stmt.order_by(models.Product.is_featured.desc(), models.Product.created_at.desc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all()


@router.get("/api/products/{slug}", response_model=schemas.ProductListItem)
def get_product_detail(slug: str, db: Session = Depends(get_db)):
    product = db.scalar(select(models.Product).where(models.Product.slug == slug, models.Product.is_active.is_(True)))
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün bulunamadı.")
    return product


# ---------------------------------------------------------------------
# ADMIN (admin/products.html bu uçları tüketir — JWT audience=admin gerekir)
# ---------------------------------------------------------------------

@router.get("/api/admin/products", response_model=schemas.AdminProductListResponse)
def admin_list_products(
    search: str | None = None,
    category: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    stmt = select(models.Product)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(models.Product.name_tr.ilike(like) | models.Product.sku.ilike(like))
    if category:
        stmt = stmt.join(models.Category).where(models.Category.slug == category)
    if status_filter == "active":
        stmt = stmt.where(models.Product.is_active.is_(True))
    elif status_filter == "inactive":
        stmt = stmt.where(models.Product.is_active.is_(False))
    elif status_filter == "low":
        stmt = stmt.where(models.Product.stock_quantity <= models.Product.low_stock_threshold, models.Product.stock_quantity > 0)
    elif status_filter == "out":
        stmt = stmt.where(models.Product.stock_quantity == 0)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(models.Product.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()

    return schemas.AdminProductListResponse(items=items, total=total or 0)


@router.post("/api/admin/products", response_model=schemas.ProductListItem, status_code=status.HTTP_201_CREATED)
def admin_create_product(
    payload: schemas.ProductCreateRequest,
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    if db.scalar(select(models.Product).where(models.Product.sku == payload.sku)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu SKU zaten kullanılıyor.")

    latest_usd = get_latest_rate(db, "USD")
    usd_rate = float(latest_usd.rate_to_try) if latest_usd else 34.20
    price_try = round(payload.base_price_usd * usd_rate * (1 + payload.margin_percentage / 100), 2)

    product = models.Product(
        sku=payload.sku,
        category_id=payload.category_id,
        name_tr=payload.name_tr,
        name_en=payload.name_en,
        slug=_generate_unique_slug(db, payload.name_tr or payload.sku),
        short_desc_tr=payload.short_desc_tr,
        short_desc_en=payload.short_desc_en,
        description_tr=payload.description_tr,
        description_en=payload.description_en,
        shopify_variant_id=payload.shopify_variant_id,
        base_price_usd=payload.base_price_usd,
        margin_percentage=payload.margin_percentage,
        price_try=price_try,
        stock_quantity=payload.stock_quantity,
        low_stock_threshold=payload.low_stock_threshold,
        is_active=payload.is_active,
        is_featured=payload.is_featured,
        is_b2b_available=payload.is_b2b_available,
    )
    db.add(product)
    db.flush()  # translations satırları için product.id gerekli
    _upsert_product_translations(db, product, payload.translations)
    db.commit()
    db.refresh(product)
    return product


@router.put("/api/admin/products/{product_id}", response_model=schemas.ProductListItem)
def admin_update_product(
    product_id: int,
    payload: schemas.ProductUpdateRequest,
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün bulunamadı.")

    update_data = payload.model_dump(exclude_unset=True)
    manual_price = update_data.pop("price_try", None)
    translations_set = update_data.pop("translations", None)  # ilişki alanı — setattr ile yazılamaz

    for field, value in update_data.items():
        setattr(product, field, value)

    if translations_set:
        _upsert_product_translations(db, product, payload.translations)

    if product.price_override and manual_price is not None:
        product.price_try = manual_price
    elif not product.price_override:
        latest_usd = get_latest_rate(db, "USD")
        usd_rate = float(latest_usd.rate_to_try) if latest_usd else 34.20
        product.price_try = round(float(product.base_price_usd) * usd_rate * (1 + float(product.margin_percentage) / 100), 2)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/api/admin/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün bulunamadı.")
    db.delete(product)
    db.commit()


# ---------------------------------------------------------------------
# ADMIN — ÜRÜN GÖRSELİ YÜKLEME
# Not: Dosyalar bu ortamda yerel diske (`backend/media/`) kaydedilir ve
# main.py'de `/media` altında statik olarak servis edilir. Production'da
# bunun yerine S3/Cloudflare R2 gibi bir nesne depolama servisi ve CDN
# kullanılması önerilir (bkz. docs/architecture.md §2).
# ---------------------------------------------------------------------

@router.post("/api/admin/products/{product_id}/image", response_model=schemas.ProductListItem)
async def admin_upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün bulunamadı.")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Sadece JPG, PNG veya WEBP yüklenebilir.")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Görsel 5MB'dan büyük olamaz.")

    image_url = storage.save_image(product_id, file.filename, contents)

    is_first_image = len(product.images) == 0
    image = models.ProductImage(
        product_id=product.id,
        image_url=image_url,
        is_primary=is_first_image,
        sort_order=len(product.images),
    )
    db.add(image)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/api/admin/products/{product_id}/image/{image_id}", response_model=schemas.ProductListItem)
def admin_delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ürün bulunamadı.")

    image = db.get(models.ProductImage, image_id)
    if not image or image.product_id != product_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Görsel bulunamadı.")

    was_primary = image.is_primary
    storage.delete_image(image.image_url)
    db.delete(image)
    db.flush()

    if was_primary:
        next_image = db.scalar(
            select(models.ProductImage).where(models.ProductImage.product_id == product_id).order_by(models.ProductImage.sort_order)
        )
        if next_image:
            next_image.is_primary = True

    db.commit()
    db.refresh(product)
    return product
