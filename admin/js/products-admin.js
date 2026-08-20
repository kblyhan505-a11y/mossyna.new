/* =====================================================================
   MOSSYNA ADMIN — Ürün Yönetimi — Backend'e Bağlı

   Aşama 5 backend'inin GET/POST/PUT/DELETE /api/admin/products ve
   POST/DELETE /api/admin/products/{id}/image uçlarını kullanır. Arama,
   filtreleme ve sayfalama artık sunucu tarafında yapılır (bkz. backend
   app/routers/products.py). Görsel yükleme gerçek multipart/form-data
   isteğiyle backend'e (ve oradan `backend/media/` dizinine) yapılır.
   ===================================================================== */

const PRODUCTS_PAGE_SIZE = 10;
let adminProductsState = { page: 1, search: "", category: "all", status: "all" };
let currentEditingImages = []; // mevcut ürün: { id, image_url, is_primary } — yeni ürün: { file, previewUrl }
let currentEditingProductId = null;
let mossynaLastProductsFetch = [];
let mossynaCachedUsdRate = 34.2;
let mossynaSearchDebounceTimer = null;

/* ---------- Yardımcılar ---------- */
async function mossynaFetchLatestUsdRate() {
  try {
    const rates = await mossynaAdminApi.getPublic("/api/exchange-rate/current");
    const usd = rates.find(r => r.currency_code === "USD");
    if (usd) mossynaCachedUsdRate = usd.rate_to_try;
  } catch (err) {
    // Kur servisine ulaşılamazsa son bilinen/varsayılan değerle devam edilir.
  }
  return mossynaCachedUsdRate;
}

function mossynaStatusPillHTML(product) {
  if (product.stock_quantity === 0) return '<span class="status-pill out">Stok Yok</span>';
  if (!product.is_active) return '<span class="status-pill inactive">Pasif</span>';
  if (product.stock_quantity <= product.low_stock_threshold) return '<span class="status-pill low">Düşük Stok</span>';
  return '<span class="status-pill active">Aktif</span>';
}

function mossynaBuildAdminProductsQuery() {
  const { search, category, status, page } = adminProductsState;
  const params = new URLSearchParams();
  if (search.trim()) params.set("search", search.trim());
  if (category !== "all") params.set("category", category);
  if (status !== "all") params.set("status", status);
  params.set("page", page);
  params.set("page_size", PRODUCTS_PAGE_SIZE);
  return params.toString();
}

/* ---------- Tablo Render ---------- */
async function mossynaRenderProductsTable() {
  const tbody = document.getElementById("productsTableBody");
  tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding:40px;">Yükleniyor…</td></tr>`;

  let result;
  try {
    result = await mossynaAdminApi.get(`/api/admin/products?${mossynaBuildAdminProductsQuery()}`);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center" style="padding:40px; color:var(--danger);">${err.message}</td></tr>`;
    document.getElementById("resultCountLabel").textContent = "0 sonuç bulundu";
    return;
  }

  const { items, total } = result;
  mossynaLastProductsFetch = items;
  const totalPages = Math.max(1, Math.ceil(total / PRODUCTS_PAGE_SIZE));
  if (adminProductsState.page > totalPages) { adminProductsState.page = totalPages; mossynaRenderProductsTable(); return; }

  document.getElementById("productCountLabel").textContent = `Ürünler (${total})`;
  document.getElementById("resultCountLabel").textContent = `${total} sonuç bulundu`;

  tbody.innerHTML = items.map(p => `
    <tr data-row-id="${p.id}">
      <td>
        <div class="prod-cell">
          <img class="prod-thumb" src="${mossynaAdminImageUrl(p.primary_image_url)}" onerror="this.src='https://placehold.co/80x80/e4ede7/1a5c40?text=•'">
          <div>
            <div class="prod-name">${p.name_tr}</div>
            <div class="prod-sku">${p.sku}</div>
          </div>
        </div>
      </td>
      <td>${mossynaAdminCategoryNameBySlug(p.category_slug)}</td>
      <td>$${Number(p.base_price_usd).toFixed(2)}</td>
      <td><strong>${mossynaAdminFormatPrice(p.price_try)}</strong></td>
      <td>${p.stock_quantity}</td>
      <td>${mossynaStatusPillHTML(p)}</td>
      <td>
        <label class="toggle-switch">
          <input type="checkbox" data-toggle-featured="${p.id}" ${p.is_featured ? "checked" : ""}>
          <span class="toggle-slider"></span>
        </label>
      </td>
      <td>
        <div class="row-actions">
          <button class="btn btn-outline btn-sm" data-edit-product="${p.id}">Düzenle</button>
          <button class="btn btn-danger btn-sm" data-delete-product="${p.id}">Sil</button>
        </div>
      </td>
    </tr>
  `).join("") || `<tr><td colspan="8" class="text-center text-muted" style="padding:40px;">Sonuç bulunamadı.</td></tr>`;

  mossynaRenderPagination(totalPages, total);
}

function mossynaRenderPagination(totalPages, totalCount) {
  const bar = document.getElementById("paginationBar");
  const { page } = adminProductsState;
  let pageButtons = "";
  for (let i = 1; i <= totalPages; i++) {
    if (totalPages > 7 && Math.abs(i - page) > 2 && i !== 1 && i !== totalPages) {
      if (i === 2 || i === totalPages - 1) pageButtons += `<span style="padding:0 4px;">…</span>`;
      continue;
    }
    pageButtons += `<button class="${i === page ? 'active' : ''}" data-goto-page="${i}">${i}</button>`;
  }
  bar.innerHTML = `
    <span>Toplam ${totalCount} üründen ${totalCount === 0 ? 0 : (page - 1) * PRODUCTS_PAGE_SIZE + 1}–${Math.min(page * PRODUCTS_PAGE_SIZE, totalCount)} arası gösteriliyor</span>
    <div class="pages">
      <button data-goto-page="${page - 1}" ${page <= 1 ? "disabled" : ""}>‹</button>
      ${pageButtons}
      <button data-goto-page="${page + 1}" ${page >= totalPages ? "disabled" : ""}>›</button>
    </div>
  `;
}

/* ---------- Fiyat Önizleme ---------- */
function mossynaUpdatePricePreview() {
  const usd = parseFloat(document.getElementById("prodBaseUsd").value) || 0;
  const margin = parseFloat(document.getElementById("prodMargin").value) || 0;
  const priceTry = usd * mossynaCachedUsdRate * (1 + margin / 100);
  document.getElementById("prodPriceTryPreview").value = priceTry.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  document.getElementById("currentRateLabel").textContent = `1 USD = ${mossynaCachedUsdRate.toFixed(2)} TL`;
}

/* ---------- Görsel Yükleme ---------- */
function mossynaRenderImagePreviews() {
  const grid = document.getElementById("imagePreviewGrid");
  grid.innerHTML = currentEditingImages.map((img, idx) => `
    <div class="image-preview-item ${img.is_primary || idx === 0 ? 'primary' : ''}">
      <img src="${img.id ? mossynaAdminImageUrl(img.image_url) : img.previewUrl}" alt="">
      <button type="button" class="remove-img" data-remove-image="${idx}">✕</button>
    </div>
  `).join("");
}

async function mossynaHandleImageFiles(files) {
  const fileList = Array.from(files);

  if (currentEditingProductId) {
    // Mevcut ürün: görseller hemen sunucuya (multipart) yüklenir.
    for (const file of fileList) {
      const form = new FormData();
      form.append("file", file);
      try {
        const updated = await mossynaAdminApi.post(`/api/admin/products/${currentEditingProductId}/image`, form, true);
        currentEditingImages = updated.images || [];
        mossynaRenderImagePreviews();
      } catch (err) {
        mossynaAdminShowToast(err.message, true);
      }
    }
  } else {
    // Yeni ürün: ürün henüz oluşturulmadığı için görseller yerel önizlemeyle
    // bekletilir, ürün kaydedilince sırayla yüklenir (bkz. mossynaSaveProductFromForm).
    for (const file of fileList) {
      await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          currentEditingImages.push({ file, previewUrl: e.target.result });
          mossynaRenderImagePreviews();
          resolve();
        };
        reader.readAsDataURL(file);
      });
    }
  }
}

/* ---------- Dil Sekmeleri (Ürün Adı/Açıklama — Çoklu Dil) ---------- */
function mossynaResetProdLangTabs() {
  document.querySelectorAll("#prodLangTabs .lang-tab").forEach(btn =>
    btn.classList.toggle("active", btn.getAttribute("data-prod-lang-tab") === "tr")
  );
  document.querySelectorAll(".lang-tab-panel").forEach(panel =>
    panel.classList.toggle("hidden", panel.getAttribute("data-prod-lang-panel") !== "tr")
  );
}

/* ---------- Modal Aç/Kapat ---------- */
async function mossynaOpenProductModal(product = null) {
  currentEditingProductId = product ? product.id : null;

  document.getElementById("productModalTitle").textContent = product ? "Ürünü Düzenle" : "Yeni Ürün Ekle";
  document.getElementById("prodId").value = product ? product.id : "";
  document.getElementById("prodNameTr").value = product ? product.name_tr : "";
  document.getElementById("prodNameEn").value = product ? product.name_en : "";
  document.getElementById("prodShortDescTr").value = product ? (product.short_desc_tr || "") : "";
  document.getElementById("prodShortDescEn").value = product ? (product.short_desc_en || "") : "";
  document.getElementById("prodDescTr").value = product ? (product.description_tr || "") : "";
  document.getElementById("prodDescEn").value = product ? (product.description_en || "") : "";
  document.getElementById("prodShopifyVariantId").value = product ? (product.shopify_variant_id || "") : "";

  // DE/FR/RU/AR çevirileri (bkz. backend ProductTranslation / ProductListItem.translations)
  const translationsByLang = {};
  (product && product.translations ? product.translations : []).forEach(t => { translationsByLang[t.language_code] = t; });
  ["de", "fr", "ru", "ar"].forEach(lang => {
    const t = translationsByLang[lang] || {};
    const cap = lang.charAt(0).toUpperCase() + lang.slice(1);
    document.getElementById(`prodName${cap}`).value = t.name || "";
    document.getElementById(`prodShortDesc${cap}`).value = t.short_desc || "";
    document.getElementById(`prodDesc${cap}`).value = t.description || "";
  });

  mossynaResetProdLangTabs();
  document.getElementById("prodSku").value = product ? product.sku : "";
  document.getElementById("prodCategory").value = product && product.category_id ? String(product.category_id) : "";
  document.getElementById("prodBaseUsd").value = product ? product.base_price_usd : "";
  document.getElementById("prodMargin").value = product ? product.margin_percentage : 40;
  document.getElementById("prodStock").value = product ? product.stock_quantity : 0;
  document.getElementById("prodLowStock").value = product ? product.low_stock_threshold : 5;
  document.getElementById("prodActive").checked = product ? product.is_active : true;
  document.getElementById("prodFeatured").checked = product ? product.is_featured : false;
  document.getElementById("prodB2b").checked = product ? (product.is_b2b_available !== false) : true;

  currentEditingImages = product && product.images ? product.images.slice() : [];
  mossynaRenderImagePreviews();

  await mossynaFetchLatestUsdRate();
  mossynaUpdatePricePreview();

  document.getElementById("productModalOverlay").classList.add("open");
}

function mossynaCloseProductModal() {
  document.getElementById("productModalOverlay").classList.remove("open");
  document.getElementById("productForm").reset();
  document.querySelectorAll("#productForm .form-group").forEach(g => g.classList.remove("has-error"));
  mossynaResetProdLangTabs();
  currentEditingProductId = null;
  currentEditingImages = [];
}

/* ---------- Kaydet ---------- */
async function mossynaSaveProductFromForm() {
  const id = document.getElementById("prodId").value;
  const nameTr = document.getElementById("prodNameTr").value.trim();
  const nameEn = document.getElementById("prodNameEn").value.trim();
  const sku = document.getElementById("prodSku").value.trim();
  const categoryIdRaw = document.getElementById("prodCategory").value;
  const categoryId = categoryIdRaw ? Number(categoryIdRaw) : null;
  const baseUsd = parseFloat(document.getElementById("prodBaseUsd").value);
  const margin = parseFloat(document.getElementById("prodMargin").value);
  const stock = parseInt(document.getElementById("prodStock").value, 10);
  const lowStock = parseInt(document.getElementById("prodLowStock").value, 10);

  if (!nameTr || !nameEn || !sku || isNaN(baseUsd) || isNaN(stock)) {
    mossynaAdminShowToast("Lütfen zorunlu alanları doldurun.", true);
    return;
  }

  // DE/FR/RU/AR çevirilerini topla — bir dilin "Ürün Adı" alanı boş bırakılmışsa o dil
  // hiç gönderilmez (sitede otomatik olarak Türkçe adı gösterilir, bkz. lang-tab-hint).
  const translations = {};
  ["de", "fr", "ru", "ar"].forEach(lang => {
    const cap = lang.charAt(0).toUpperCase() + lang.slice(1);
    const name = document.getElementById(`prodName${cap}`).value.trim();
    if (!name) return;
    translations[lang] = {
      name,
      short_desc: document.getElementById(`prodShortDesc${cap}`).value.trim() || null,
      description: document.getElementById(`prodDesc${cap}`).value.trim() || null,
    };
  });

  const payload = {
    name_tr: nameTr,
    name_en: nameEn,
    category_id: categoryId,
    base_price_usd: baseUsd,
    margin_percentage: margin,
    stock_quantity: stock,
    low_stock_threshold: lowStock,
    is_active: document.getElementById("prodActive").checked,
    is_featured: document.getElementById("prodFeatured").checked,
    is_b2b_available: document.getElementById("prodB2b").checked,
    short_desc_tr: document.getElementById("prodShortDescTr").value.trim() || null,
    short_desc_en: document.getElementById("prodShortDescEn").value.trim() || null,
    description_tr: document.getElementById("prodDescTr").value.trim() || null,
    description_en: document.getElementById("prodDescEn").value.trim() || null,
    shopify_variant_id: document.getElementById("prodShopifyVariantId").value.trim() || null,
    translations,
  };

  const saveBtn = document.getElementById("saveProductBtn");
  saveBtn.disabled = true;

  try {
    let product;
    if (id) {
      product = await mossynaAdminApi.put(`/api/admin/products/${id}`, payload);
    } else {
      product = await mossynaAdminApi.post("/api/admin/products", { ...payload, sku });

      // Ürün oluşturulmadan önce yerelde bekletilen (henüz yüklenmemiş) görseller varsa sırayla yükle
      const pendingFiles = currentEditingImages.filter(img => img.file);
      for (const pending of pendingFiles) {
        const form = new FormData();
        form.append("file", pending.file);
        try {
          await mossynaAdminApi.post(`/api/admin/products/${product.id}/image`, form, true);
        } catch (err) {
          mossynaAdminShowToast(`Görsel yüklenemedi: ${err.message}`, true);
        }
      }
    }
    mossynaAdminShowToast(id ? "Ürün güncellendi ✓" : "Yeni ürün eklendi ✓");
    mossynaCloseProductModal();
    mossynaRenderProductsTable();
  } catch (err) {
    mossynaAdminShowToast(err.message, true);
  } finally {
    saveBtn.disabled = false;
  }
}

/* ---------- Kategori Seçenekleri ---------- */
async function mossynaPopulateCategorySelects() {
  const categories = await mossynaAdminFetchCategories();

  const filterSelect = document.getElementById("categoryFilter");
  filterSelect.innerHTML = `<option value="all">Tüm Kategoriler</option>` +
    categories.map(c => `<option value="${c.slug}">${c.name_tr}</option>`).join("");

  const formSelect = document.getElementById("prodCategory");
  formSelect.innerHTML = `<option value="">Kategori Seçin</option>` +
    categories.map(c => `<option value="${c.id}">${c.name_tr}</option>`).join("");
}

/* ---------- Olay Bağlama ---------- */
document.addEventListener("DOMContentLoaded", async () => {
  if (!document.getElementById("productsTableBody")) return;
  if (!mossynaAdminIsLoggedIn()) return;

  await mossynaPopulateCategorySelects();
  mossynaRenderProductsTable();

  document.getElementById("searchInput").addEventListener("input", (e) => {
    clearTimeout(mossynaSearchDebounceTimer);
    const value = e.target.value;
    mossynaSearchDebounceTimer = setTimeout(() => {
      adminProductsState.search = value; adminProductsState.page = 1; mossynaRenderProductsTable();
    }, 350);
  });
  document.getElementById("categoryFilter").addEventListener("change", (e) => {
    adminProductsState.category = e.target.value; adminProductsState.page = 1; mossynaRenderProductsTable();
  });
  document.getElementById("statusFilter").addEventListener("change", (e) => {
    adminProductsState.status = e.target.value; adminProductsState.page = 1; mossynaRenderProductsTable();
  });

  document.getElementById("openAddProductBtn").addEventListener("click", () => mossynaOpenProductModal());
  document.querySelectorAll("[data-close-product-modal]").forEach(el => el.addEventListener("click", mossynaCloseProductModal));
  document.getElementById("productModalOverlay").addEventListener("click", (e) => {
    if (e.target.id === "productModalOverlay") mossynaCloseProductModal();
  });

  document.getElementById("saveProductBtn").addEventListener("click", mossynaSaveProductFromForm);
  document.getElementById("prodBaseUsd").addEventListener("input", mossynaUpdatePricePreview);
  document.getElementById("prodMargin").addEventListener("input", mossynaUpdatePricePreview);

  // Dil sekmeleri (Ürün Adı/Açıklama)
  document.getElementById("prodLangTabs").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-prod-lang-tab]");
    if (!btn) return;
    const lang = btn.getAttribute("data-prod-lang-tab");
    document.querySelectorAll("#prodLangTabs .lang-tab").forEach(b => b.classList.toggle("active", b === btn));
    document.querySelectorAll(".lang-tab-panel").forEach(panel =>
      panel.classList.toggle("hidden", panel.getAttribute("data-prod-lang-panel") !== lang)
    );
  });

  // Görsel yükleme
  const uploadZone = document.getElementById("imageUploadZone");
  const imageInput = document.getElementById("imageInput");
  uploadZone.addEventListener("click", () => imageInput.click());
  imageInput.addEventListener("change", (e) => mossynaHandleImageFiles(e.target.files));
  uploadZone.addEventListener("dragover", (e) => { e.preventDefault(); uploadZone.classList.add("dragover"); });
  uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
  uploadZone.addEventListener("drop", (e) => {
    e.preventDefault(); uploadZone.classList.remove("dragover");
    mossynaHandleImageFiles(e.dataTransfer.files);
  });

  // Tablo içi olaylar (event delegation)
  document.getElementById("productsTableBody").addEventListener("click", (e) => {
    const editId = e.target.getAttribute("data-edit-product");
    const delId = e.target.getAttribute("data-delete-product");
    if (editId) {
      const product = mossynaLastProductsFetch.find(p => String(p.id) === editId);
      if (product) mossynaOpenProductModal(product);
    }
    if (delId) {
      if (confirm("Bu ürünü silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.")) {
        mossynaAdminApi.del(`/api/admin/products/${delId}`)
          .then(() => {
            mossynaAdminShowToast("Ürün silindi.");
            mossynaRenderProductsTable();
          })
          .catch(err => mossynaAdminShowToast(err.message, true));
      }
    }
  });
  document.getElementById("productsTableBody").addEventListener("change", (e) => {
    const toggleId = e.target.getAttribute("data-toggle-featured");
    if (toggleId) {
      const checked = e.target.checked;
      mossynaAdminApi.put(`/api/admin/products/${toggleId}`, { is_featured: checked })
        .then(() => mossynaAdminShowToast(checked ? "Öne çıkanlara eklendi." : "Öne çıkanlardan kaldırıldı."))
        .catch(err => { mossynaAdminShowToast(err.message, true); e.target.checked = !checked; });
    }
  });

  document.getElementById("imagePreviewGrid").addEventListener("click", (e) => {
    const removeIdx = e.target.getAttribute("data-remove-image");
    if (removeIdx === null) return;
    const idx = Number(removeIdx);
    const img = currentEditingImages[idx];
    if (img && img.id && currentEditingProductId) {
      mossynaAdminApi.del(`/api/admin/products/${currentEditingProductId}/image/${img.id}`)
        .then(updated => { currentEditingImages = updated.images || []; mossynaRenderImagePreviews(); })
        .catch(err => mossynaAdminShowToast(err.message, true));
    } else {
      currentEditingImages.splice(idx, 1);
      mossynaRenderImagePreviews();
    }
  });

  document.getElementById("paginationBar").addEventListener("click", (e) => {
    const page = e.target.getAttribute("data-goto-page");
    if (page) {
      adminProductsState.page = Number(page);
      mossynaRenderProductsTable();
    }
  });
});
