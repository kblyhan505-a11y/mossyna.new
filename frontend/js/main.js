/* =====================================================================
   MOSSYNA — Genel UI Etkileşimleri
   ===================================================================== */

/* ---------- Mobil Menü ---------- */
document.addEventListener("DOMContentLoaded", () => {
  const hamburger = document.querySelector(".hamburger");
  const nav = document.querySelector(".main-nav");
  if (hamburger && nav) {
    hamburger.addEventListener("click", () => nav.classList.toggle("open"));
  }
});

/* ---------- Sepet Çekmecesi Aç/Kapat ---------- */
document.addEventListener("DOMContentLoaded", () => {
  const overlay = document.querySelector(".cart-drawer-overlay");
  const drawer = document.querySelector(".cart-drawer");
  const openBtns = document.querySelectorAll("[data-open-cart]");
  const closeBtns = document.querySelectorAll("[data-close-cart]");

  function openCart() {
    overlay?.classList.add("open");
    drawer?.classList.add("open");
  }
  function closeCart() {
    overlay?.classList.remove("open");
    drawer?.classList.remove("open");
  }

  openBtns.forEach(btn => btn.addEventListener("click", (e) => { e.preventDefault(); openCart(); }));
  closeBtns.forEach(btn => btn.addEventListener("click", closeCart));
  overlay?.addEventListener("click", closeCart);
});

/* ---------- Hoş Geldin İndirimi Modalı ----------
   Gerçek sistemde bu modal, kullanıcı yeni kayıt olduğunda backend'in
   döndürdüğü "unused welcome discount" bilgisine göre tetiklenir.
   Demo için: daha önce kapatılmamışsa 1.5 sn sonra gösterilir. */
document.addEventListener("DOMContentLoaded", () => {
  const overlay = document.querySelector(".welcome-modal-overlay");
  if (!overlay) return;

  const alreadySeen = sessionStorage.getItem("mossyna_welcome_seen");
  if (!alreadySeen) {
    setTimeout(() => overlay.classList.add("open"), 1200);
    sessionStorage.setItem("mossyna_welcome_seen", "true");
  }

  overlay.querySelectorAll("[data-close-welcome]").forEach(btn => {
    btn.addEventListener("click", () => overlay.classList.remove("open"));
  });
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.classList.remove("open");
  });
});

/* ---------- Ürün Kartı Render (ortak fonksiyon) ---------- */
function mossynaProductCardHTML(product) {
  const lang = mossynaGetLang();
  const name = mossynaProductName(product, lang);
  const shortDesc = mossynaProductShortDesc(product, lang);

  const hasDiscount = product.compare_at_price && Number(product.compare_at_price) > Number(product.price_try);
  const badgesHTML = hasDiscount ? `<span class="badge discount">${lang === "tr" ? "İndirim" : "Sale"}</span>` : "";
  const oldPriceHTML = hasDiscount ? `<span class="price-old">${mossynaFormatPrice(product.compare_at_price)}</span>` : "";
  const stockHTML = product.stock_quantity === 0
    ? `<div class="form-hint" style="color:var(--danger);">${lang === "tr" ? "Stokta yok" : "Out of stock"}</div>` : "";

  return `
    <div class="product-card" data-id="${product.id}">
      <div class="product-thumb">
        <div class="product-badges">${badgesHTML}</div>
        <img src="${mossynaProductImageSrc(product)}" alt="${name}" onerror="this.src='https://placehold.co/400x400/e4ede7/1a5c40?text=Mossyna'">
        <button class="quick-add" data-add-cart="${product.id}" title="${mossynaT('product.addtocart')}" ${product.stock_quantity === 0 ? "disabled" : ""}>+</button>
      </div>
      <div class="product-info">
        <span class="cat-label">${product.category_slug || ""}</span>
        <h3>${name}</h3>
        ${shortDesc ? `<p style="font-size:.82rem; color:var(--text-muted); margin:0;">${shortDesc}</p>` : ""}
        <div class="price-row">
          <span class="price-current">${mossynaFormatPrice(product.price_try)}</span>
          ${oldPriceHTML}
        </div>
        <div class="price-b2b-note">${mossynaT('product.b2bnote')}</div>
        ${stockHTML}
        <button class="add-to-cart-btn" data-add-cart="${product.id}" ${product.stock_quantity === 0 ? "disabled" : ""}>${mossynaT('product.addtocart')}</button>
      </div>
    </div>
  `;
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-add-cart]");
  if (!btn || btn.disabled) return;
  const id = Number(btn.getAttribute("data-add-cart"));
  mossynaAddToCart(id, 1);
});

/* ---------- Anasayfa: Öne Çıkan Ürünler + Kategoriler ----------
   Not: Backend'e ulaşılamazsa ya da veritabanı henüz boşsa (ürünler admin
   panelden eklenmeden önce), vitrin boş görünmesin diye js/mock-data.js
   içindeki örnek verilere otomatik geçilir. Gerçek ürünler eklendiği an
   bu mock veri devreye hiç girmez. */
async function mossynaRenderFeatured() {
  const grid = document.querySelector("[data-featured-grid]");
  if (!grid) return;
  grid.innerHTML = `<p class="text-center text-muted" style="grid-column:1/-1;">Ürünler yükleniyor…</p>`;
  let featured = [];
  try {
    featured = await mossynaFetchProducts({ isFeatured: true, pageSize: 4 });
  } catch (err) {
    featured = [];
  }
  if (!featured.length && typeof mossynaGetMockProducts === "function") {
    featured = mossynaGetMockProducts({ isFeatured: true, pageSize: 4 });
  }
  grid.innerHTML = featured.length
    ? featured.map(mossynaProductCardHTML).join("")
    : `<p class="text-center text-muted" style="grid-column:1/-1;">Henüz öne çıkan ürün eklenmemiş.</p>`;
}

async function mossynaRenderCategories() {
  const grid = document.querySelector("[data-category-grid]");
  if (!grid) return;
  const lang = mossynaGetLang();
  let categories = [];
  try {
    categories = await mossynaFetchCategories();
  } catch (err) {
    categories = [];
  }
  if (!categories.length && typeof mossynaGetMockCategories === "function") {
    categories = mossynaGetMockCategories();
  }
  grid.innerHTML = categories.map(cat => `
    <a class="category-card" href="products.html?category=${cat.slug}">
      <img src="${cat.image_url ? MOSSYNA_API_BASE_URL + cat.image_url : 'https://placehold.co/400x500/1a5c40/f5f5f0?text=' + encodeURIComponent(cat.slug)}"
           alt="${lang === 'en' ? cat.name_en : cat.name_tr}" onerror="this.src='https://placehold.co/400x500/1a5c40/f5f5f0?text=Mossyna'">
      <div class="label">${lang === "en" ? cat.name_en : cat.name_tr}</div>
    </a>
  `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  mossynaRenderFeatured();
  mossynaRenderCategories();
});
document.addEventListener("mossyna:languagechange", () => {
  mossynaRenderFeatured();
  mossynaRenderCategories();
  if (typeof mossynaRenderProductGrid === "function") mossynaRenderProductGrid();
});
