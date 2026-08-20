"""
MOSSYNA BACKEND — Başlangıç Verisi (Seed) Script'i

Yeni kurulan bir ortamda bu script'i BİR KEZ çalıştırın:
    python -m app.scripts.seed

Oluşturduğu kayıtlar:
  - İlk süper yönetici hesabı (admin@mossyna.com / admin123 — İLK GİRİŞTEN
    SONRA MUTLAKA DEĞİŞTİRİN)
  - "WELCOME10" hoş geldin indirimi (%10, yeni üyelere otomatik atanır)
  - Başlangıç USD/EUR kuru (currency_service ilk çalışmadan önce bir
    referans değere sahip olsun diye)
  - Temel kategoriler (frontend/js/products-data.js ile birebir aynı slug'lar)
"""
import logging

from app.database import Base, engine, SessionLocal
from app import models
from app.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mossyna.seed")


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(models.AdminUser).filter_by(username="admin@mossyna.com").first():
            db.add(models.AdminUser(
                username="admin@mossyna.com",
                email="admin@mossyna.com",
                password_hash=hash_password("admin123"),
                role="superadmin",
            ))
            logger.info("Süper yönetici oluşturuldu: admin@mossyna.com / admin123 (ilk girişten sonra değiştirin!)")

        if not db.query(models.Discount).filter_by(code="WELCOME10").first():
            db.add(models.Discount(
                code="WELCOME10",
                description_tr="Yeni üyelere özel %10 hoş geldin indirimi",
                description_en="10% welcome discount for new members",
                type="percentage",
                value=10,
                min_order_amount=0,
                is_auto_welcome=True,
                usage_limit_per_user=1,
            ))
            logger.info("WELCOME10 indirim kuponu oluşturuldu.")

        if not db.query(models.ExchangeRate).first():
            db.add(models.ExchangeRate(currency_code="USD", rate_to_try=34.20, source="Seed"))
            db.add(models.ExchangeRate(currency_code="EUR", rate_to_try=37.10, source="Seed"))
            logger.info("Başlangıç döviz kuru eklendi (USD=34.20, EUR=37.10).")

        categories = [
            ("yatak", "Yatak Odası", "Bedroom"),
            ("banyo", "Banyo", "Bathroom"),
            ("sofra", "Sofra & Mutfak", "Table & Kitchen"),
            ("dekor", "Dekoratif", "Decorative"),
        ]
        for slug, name_tr, name_en in categories:
            if not db.query(models.Category).filter_by(slug=slug).first():
                db.add(models.Category(slug=slug, name_tr=name_tr, name_en=name_en))
        logger.info("Kategoriler kontrol edildi/oluşturuldu.")
        db.commit()

        # --- Örnek ürünler (frontend/js/products-data.js ile aynı katalog) ---
        category_map = {c.slug: c.id for c in db.query(models.Category).all()}
        usd_rate = 34.20
        sample_products = [
            ("MSY-YAT-0001", "yatak", "Organik Pamuk Nevresim Takımı", "Organic Cotton Duvet Cover Set", 62, 40),
            ("MSY-BAN-0001", "banyo", "Yosun Yeşili Banyo Havlusu Seti (4'lü)", "Moss Green Bath Towel Set (Set of 4)", 32, 40),
            ("MSY-SOF-0001", "sofra", "Keten Karışımlı Masa Örtüsü", "Linen Blend Tablecloth", 22, 40),
            ("MSY-BAN-0002", "banyo", "Krem Bornoz (Unisex)", "Cream Bathrobe (Unisex)", 29, 40),
            ("MSY-YAT-0002", "yatak", "Doğal Pamuklu Alez", "Natural Cotton Mattress Protector", 16, 40),
            ("MSY-DEK-0001", "dekor", "Bej Dekoratif Yastık Kılıfı", "Beige Decorative Cushion Cover", 8, 40),
            ("MSY-YAT-0003", "yatak", "Yün Karışımlı Battaniye", "Wool Blend Throw Blanket", 45, 40),
            ("MSY-SOF-0002", "sofra", "Pamuklu Mutfak Havlusu Seti (6'lı)", "Cotton Kitchen Towel Set (Set of 6)", 12, 40),
        ]
        for sku, cat_slug, name_tr, name_en, usd, margin in sample_products:
            if db.query(models.Product).filter_by(sku=sku).first():
                continue
            price_try = round(usd * usd_rate * (1 + margin / 100), 2)
            slug = name_tr.lower().translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"))
            slug = "".join(c if c.isalnum() else "-" for c in slug).strip("-")
            db.add(models.Product(
                sku=sku, category_id=category_map.get(cat_slug), name_tr=name_tr, name_en=name_en,
                slug=slug, base_price_usd=usd, margin_percentage=margin, price_try=price_try,
                stock_quantity=25, low_stock_threshold=5, is_active=True,
                is_featured=(sku in ("MSY-YAT-0001", "MSY-BAN-0001", "MSY-SOF-0001", "MSY-BAN-0002")),
            ))
        logger.info("Örnek ürünler kontrol edildi/oluşturuldu.")

        db.commit()
        logger.info("Seed işlemi tamamlandı.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
