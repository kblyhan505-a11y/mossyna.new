/* =====================================================================
   MOSSYNA ADMIN — Kategori Önbelleği
   Not: Bu dosya Aşama 4'te demo ürün/mesaj/kur verisi üreten bir mock veri
   kaynağıydı. Aşama 5 backend'ine bağlandıktan sonra tüm veriler gerçek API
   uçlarından çekildiği için (bkz. products-admin.js, exchange-rate.html,
   messages.html, index.html) burada yalnızca sayfalar arasında paylaşılan
   kategori önbelleği kalmıştır — GET /api/categories public bir uçtur.
   ===================================================================== */

let MOSSYNA_ADMIN_CATEGORIES_CACHE = null;

async function mossynaAdminFetchCategories() {
  if (MOSSYNA_ADMIN_CATEGORIES_CACHE) return MOSSYNA_ADMIN_CATEGORIES_CACHE;
  try {
    MOSSYNA_ADMIN_CATEGORIES_CACHE = await mossynaAdminApi.getPublic("/api/categories");
  } catch (err) {
    MOSSYNA_ADMIN_CATEGORIES_CACHE = [];
  }
  return MOSSYNA_ADMIN_CATEGORIES_CACHE;
}

function mossynaAdminCategoryNameBySlug(slug) {
  const cat = (MOSSYNA_ADMIN_CATEGORIES_CACHE || []).find(c => c.slug === slug);
  return cat ? cat.name_tr : (slug || "—");
}

function mossynaAdminCategoryNameById(id) {
  const cat = (MOSSYNA_ADMIN_CATEGORIES_CACHE || []).find(c => c.id === Number(id));
  return cat ? cat.name_tr : "—";
}
