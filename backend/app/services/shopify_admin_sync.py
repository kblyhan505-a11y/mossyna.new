"""
MOSSYNA BACKEND — Shopify Admin API Ürün Senkronizasyonu

Admin panelinden bir ürün eklendiğinde/güncellendiğinde, Shopify tarafındaki
karşılığını otomatik oluşturur (ilk kayıt) ya da günceller (zaten bağlıysa) ve
dönen "variant" Global ID'sini products.shopify_variant_id alanına yazar.
Böylece admin, Shopify panelinden bir ID kopyalayıp buraya elle yapıştırmak
zorunda kalmaz — bkz. routers/products.py (admin_create_product / admin_update_product).

ÖNEMLİ — bu, ödeme sırasında kullanılan Storefront API'den (bkz.
services/payment_providers/shopify_provider.py) FARKLI bir API'dir:
  - Storefront API  → sadece sepet/checkout oluşturur (SHOPIFY_STOREFRONT_ACCESS_TOKEN)
  - Admin API (bu dosya) → ürün OLUŞTURMA/GÜNCELLEME yetkisi ister

KİMLİK DOĞRULAMA (Ocak 2026'da değişti) — Shopify, tek seferlik sabit bir
"Admin API access token" gösteren eski "Uygulama geliştir" ekranını tamamen
kaldırdı. Yeni uygulamalar artık "Dev Dashboard" üzerinden oluşturuluyor ve
orada sabit bir anahtar GÖSTERİLMİYOR — bunun yerine bir İstemci kimliği
(Client ID) ve Gizli anahtar (Client secret) veriliyor. Bu ikisinden gerçek
bir erişim anahtarını KENDİMİZ, her senkronizasyonda "Client Credentials
Grant" denen küçük bir ek istekle üretiyoruz (bkz. _get_admin_access_token).
Üretilen anahtar yalnızca 24 saat geçerli olduğu için hiçbir yerde
SAKLAMIYORUZ — her ürün kaydında taze bir tane isteniyor. Bu, ürün kaydetme
gibi seyrek olan bir işlem için performans açısından önemsiz bir maliyettir.

NOT: "Client Credentials Grant" SADECE uygulama ile mağaza aynı Shopify
hesabına/organizasyonuna aitse çalışır (bir tüccarın kendi mağazası için
kendi oluşturduğu uygulama gibi — Mossyna'nın durumu tam olarak bu). Ayrıca
uygulamanın mağazaya GERÇEKTEN YÜKLENMİŞ olması gerekir (Dev Dashboard'da
uygulamanın "Ana Sayfa" sekmesinden "Uygulamayı Yükle" ile yapılır) — sadece
oluşturmak yetmez.

Bu senkronizasyon İSTEĞE BAĞLIDIR: yapılandırma eksikse ya da Shopify
tarafında herhangi bir sorun olursa (yanlış anahtar, geçici bağlantı sorunu,
beklenmeyen bir hata vb.) fonksiyon sessizce None döner ve ürünün Mossyna'ya
kaydedilmesini HİÇBİR ZAMAN engellemez — "Shopify Variant ID" alanı o durumda
eskisi gibi admin panelinden elle doldurulabilir.

Senkronize edilen alanlar bilinçli olarak sınırlı tutulmuştur: ürün adı (TR),
kısa açıklama (varsa) ve TL satış fiyatı. Stok adedi Shopify'a GÖNDERİLMEZ —
stok takibi hâlâ yalnızca Mossyna admin panelinde yapılır, Shopify sadece
ödeme sayfası olarak kullanılır (bkz. shopify_provider.py mimari notu).

VARSAYIM: Shopify mağazasının para birimi TL (TRY) olarak ayarlanmıştır —
öyle değilse, gönderilen sayısal fiyat yanlış para biriminde yorumlanır.
"""
import logging

import httpx

from app.config import get_settings
from app import models

logger = logging.getLogger("mossyna.shopify_admin_sync")
settings = get_settings()


def _shop_base_url() -> str:
    return f"https://{settings.shopify_store_domain}"


def _get_admin_access_token() -> str | None:
    """
    Dev Dashboard uygulamaları artık sabit bir "Admin API access token"
    göstermiyor — bunun yerine "Uygulama ayarları" sayfasındaki İstemci
    kimliği + Gizli anahtar çiftini "Client Credentials Grant" denen küçük
    bir istekle gerçek bir erişim anahtarına çeviriyoruz. Bu anahtar yalnızca
    24 saat geçerlidir, bu yüzden saklamak yerine her senkronizasyonda taze
    bir tane isteriz.
    """
    try:
        response = httpx.post(
            f"{_shop_base_url()}/admin/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.shopify_admin_client_id,
                "client_secret": settings.shopify_admin_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # Shopify'ın 400/401 gibi durumlarda döndürdüğü asıl hata metnini (ör.
        # "application_cannot_be_found" ya da "shop_not_permitted") log'a yazıyoruz —
        # bu olmadan sadece "400 Bad Request" görünür, asıl neden anlaşılamaz.
        logger.warning(
            "Shopify'dan erişim anahtarı alınamadı (HTTP %s): %s",
            exc.response.status_code, exc.response.text,
        )
        return None
    except httpx.HTTPError as exc:
        logger.warning("Shopify'a bağlanılamadı: %s", exc)
        return None

    token = response.json().get("access_token")
    if not token:
        logger.warning("Shopify erişim anahtarı yanıtında 'access_token' bulunamadı: %s", response.text)
        return None
    return token


def _admin_graphql(query: str, variables: dict) -> dict | None:
    access_token = _get_admin_access_token()
    if not access_token:
        return None

    try:
        response = httpx.post(
            f"{_shop_base_url()}/admin/api/{settings.shopify_api_version}/graphql.json",
            json={"query": query, "variables": variables},
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": access_token,
            },
            timeout=20.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Shopify Admin API'ye bağlanılamadı (HTTP %s): %s",
            exc.response.status_code, exc.response.text,
        )
        return None
    except httpx.HTTPError as exc:
        logger.warning("Shopify Admin API'ye bağlanılamadı: %s", exc)
        return None

    payload = response.json()
    if payload.get("errors"):
        logger.warning("Shopify Admin API GraphQL hatası: %s", payload["errors"])
        return None
    return payload.get("data")


# productSet: mevcut Shopify Admin API'nin, bir ürünü ID'siyle eşleştirip
# GÜNCELLEYEN ya da (identifier verilmezse) YENİ oluşturan "upsert" mutation'ı.
# NOT: Bu şema, Shopify'ın 2024 sonrası Admin API sürümlerinde geçerlidir; fiyat
# doğrudan `variants` dizisi içinde tanımlanır (eski `productCreate` mutation'ında
# bu artık desteklenmiyor, ayrı bir productVariantsBulkCreate çağrısı gerektiriyordu).
_PRODUCT_SET_MUTATION = """
mutation MossynaProductSet($input: ProductSetInput!, $identifier: ProductSetIdentifiers) {
  productSet(input: $input, identifier: $identifier, synchronous: true) {
    product {
      id
      variants(first: 1) {
        edges { node { id } }
      }
    }
    userErrors { field message }
  }
}
"""

_VARIANT_PARENT_QUERY = """
query MossynaVariantParent($id: ID!) {
  productVariant(id: $id) {
    product { id }
  }
}
"""


def sync_product_to_shopify(product: models.Product) -> str | None:
    """
    Verilen Mossyna ürününü Shopify'da oluşturur (ilk kayıt) ya da günceller
    (zaten product.shopify_variant_id doluysa). Başarılı olursa Shopify
    ProductVariant Global ID'sini ("gid://shopify/ProductVariant/...") döndürür
    — çağıran taraf bunu products.shopify_variant_id alanına yazar. Yapılandırma
    eksikse ya da Shopify tarafında bir sorun olursa None döner; çağıran taraf bu
    durumda mevcut (varsa) değeri OLDUĞU GİBİ bırakmalıdır.
    """
    if (
        not settings.shopify_store_domain
        or not settings.shopify_admin_client_id
        or not settings.shopify_admin_client_secret
    ):
        return None

    # Shopify'ın güncel ürün modelinde her varyantın hangi "seçenek" değerine karşılık
    # geldiğini belirtmesi ZORUNLU (optionValues alanı boş/null olamaz). Mossyna'da
    # gerçek bir varyant seçimi (renk/beden gibi) olmadığı için Shopify'ın tek-varyantlı
    # ürünler için kullandığı standart "Title" seçeneği + "Default Title" değeriyle
    # tanımlıyoruz (bkz. shopify.dev OptionSetInput / VariantOptionValueInput).
    product_input = {
        "title": product.name_tr,
        "status": "ACTIVE" if product.is_active else "DRAFT",
        "productOptions": [{"name": "Title", "values": [{"name": "Default Title"}]}],
        "variants": [{
            "price": f"{float(product.price_try):.2f}",
            "sku": product.sku,
            "optionValues": [{"optionName": "Title", "name": "Default Title"}],
        }],
    }
    if product.short_desc_tr:
        product_input["descriptionHtml"] = product.short_desc_tr

    identifier = None
    if product.shopify_variant_id:
        parent_data = _admin_graphql(_VARIANT_PARENT_QUERY, {"id": product.shopify_variant_id})
        parent_variant = (parent_data or {}).get("productVariant")
        if parent_variant and parent_variant.get("product"):
            identifier = {"id": parent_variant["product"]["id"]}

    data = _admin_graphql(_PRODUCT_SET_MUTATION, {"input": product_input, "identifier": identifier})
    if not data:
        return None

    result = data.get("productSet") or {}
    if result.get("userErrors"):
        logger.warning("Shopify productSet hatası (SKU=%s): %s", product.sku, result["userErrors"])
        return None

    edges = ((result.get("product") or {}).get("variants") or {}).get("edges") or []
    if not edges:
        logger.warning("Shopify productSet başarılı göründü ama varyant ID'si alınamadı (SKU=%s).", product.sku)
        return None
    return edges[0]["node"]["id"]
