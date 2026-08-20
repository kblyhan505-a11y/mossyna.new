/* =====================================================================
   MOSSYNA — Ürün Verisi Katmanı (Backend'e Bağlı)

   Not: Bu dosya, önceki demo aşamasındaki statik `products-data.js`
   dosyasının yerini alır. Ürünler artık FastAPI backend'inden
   (GET /api/products, GET /api/categories) gerçek zamanlı çekilir.
   ===================================================================== */

// Sayfa içinde render edilen ürünlerin önbelleği — sepete eklerken
// (mossynaAddToCart) tekrar API çağrısı yapmamak için id'ye göre saklanır.
const MOSSYNA_PRODUCT_CACHE = {};

/** DE/FR/RU/AR için product.translations dizisinden ilgili dilin çevirisini bulur (yoksa null döner). */
function mossynaProductTranslation(product, lang) {
  if (!product.translations || !product.translations.length) return null;
  return product.translations.find(t => t.language_code === lang) || null;
}

function mossynaProductName(product, lang) {
  if (lang === "en") return product.name_en;
  if (lang === "tr") return product.name_tr;
  const t = mossynaProductTranslation(product, lang);
  // Çevirisi girilmemiş diller için Türkçe adı gösterilir (site genelindeki tr-fallback kuralı).
  return (t && t.name) || product.name_tr;
}

function mossynaProductShortDesc(product, lang) {
  if (lang === "en") return product.short_desc_en || "";
  if (lang === "tr") return product.short_desc_tr || "";
  const t = mossynaProductTranslation(product, lang);
  return (t && t.short_desc) || product.short_desc_tr || "";
}

function mossynaProductDescription(product, lang) {
  if (lang === "en") return product.description_en || "";
  if (lang === "tr") return product.description_tr || "";
  const t = mossynaProductTranslation(product, lang);
  return (t && t.description) || product.description_tr || "";
}

function mossynaProductImageSrc(product) {
  if (!product.primary_image_url) {
    return "https://placehold.co/400x400/e4ede7/1a5c40?text=Mossyna";
  }
  // S3/R2 depolamada (bkz. backend/app/services/storage.py) görsel URL'i zaten
  // tam (absolute) bir adres olarak döner — bu durumda API base URL ile
  // BİRLEŞTİRİLMEMELİ, doğrudan kullanılmalı. Yerel depolamada ise göreli bir
  // yol döner (örn. /media/products/1/x.jpg) ve API base URL'in önüne eklenmesi
  // gerekir.
  if (/^https?:\/\//i.test(product.primary_image_url)) {
    return product.primary_image_url;
  }
  return `${MOSSYNA_API_BASE_URL}${product.primary_image_url}`;
}

async function mossynaFetchCategories() {
  try {
    return await mossynaApi.get("/api/categories");
  } catch (err) {
    console.warn("Kategoriler çekilemedi:", err.message);
    return [];
  }
}

/**
 * @param {object} filters - { category, search, isFeatured, sort, minPrice, maxPrice, pageSize }
 */
async function mossynaFetchProducts(filters = {}) {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.search) params.set("search", filters.search);
  if (filters.isFeatured !== undefined) params.set("is_featured", filters.isFeatured);
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.minPrice !== undefined) params.set("min_price", filters.minPrice);
  if (filters.maxPrice !== undefined) params.set("max_price", filters.maxPrice);
  params.set("page_size", filters.pageSize || 100);

  const products = await mossynaApi.get(`/api/products?${params.toString()}`);
  products.forEach(p => { MOSSYNA_PRODUCT_CACHE[p.id] = p; });
  return products;
}
