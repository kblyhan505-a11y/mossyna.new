/* =====================================================================
   MOSSYNA — Sepet (Cart) Modülü

   Not: Sepet, backend'de kalıcı bir "cart" tablosuna değil, kasıtlı olarak
   tarayıcının localStorage'ına yazılır (misafir alışverişi de dahil sorunsuz
   çalışsın diye — yaygın bir e-ticaret pratiğidir). Checkout adımında tüm
   sepet içeriği tek seferde `POST /api/orders` ile backend'e gönderilir ve
   fiyatlar orada sunucu tarafından yeniden doğrulanır (bkz. checkout.html).
   Ürün bilgisi, sepete eklenme anında backend'den gelen güncel veriyle
   (MOSSYNA_PRODUCT_CACHE, bkz. products.js) satır içine gömülür.
   ===================================================================== */

const MOSSYNA_CART_KEY = "mossyna_cart";
const MOSSYNA_WELCOME_DISCOUNT_RATE = 0.10; // %10 hoş geldin indirimi

function mossynaGetCart() {
  try {
    return JSON.parse(localStorage.getItem(MOSSYNA_CART_KEY)) || [];
  } catch (e) {
    return [];
  }
}

function mossynaSaveCart(cart) {
  localStorage.setItem(MOSSYNA_CART_KEY, JSON.stringify(cart));
  mossynaUpdateCartBadge();
  document.dispatchEvent(new CustomEvent("mossyna:cartchange", { detail: { cart } }));
}

function mossynaAddToCart(productId, qty = 1) {
  const product = MOSSYNA_PRODUCT_CACHE[productId];
  if (!product) {
    mossynaShowToast("Ürün bilgisi bulunamadı, sayfayı yenileyip tekrar deneyin.");
    return;
  }

  const cart = mossynaGetCart();
  const existing = cart.find(item => item.productId === productId);

  if (existing) {
    existing.qty += qty;
  } else {
    cart.push({
      productId: product.id,
      qty,
      unitPrice: product.price_try,
      nameTr: product.name_tr,
      nameEn: product.name_en,
      image: mossynaProductImageSrc(product)
    });
  }
  mossynaSaveCart(cart);
  mossynaShowToast(mossynaT("product.addtocart") + " ✓");
}

function mossynaRemoveFromCart(productId) {
  const cart = mossynaGetCart().filter(item => item.productId !== productId);
  mossynaSaveCart(cart);
}

function mossynaUpdateQty(productId, qty) {
  const cart = mossynaGetCart();
  const item = cart.find(i => i.productId === productId);
  if (!item) return;
  item.qty = Math.max(1, qty);
  mossynaSaveCart(cart);
}

function mossynaCartSubtotal() {
  return mossynaGetCart().reduce((sum, item) => sum + item.unitPrice * item.qty, 0);
}

function mossynaCartCount() {
  return mossynaGetCart().reduce((sum, item) => sum + item.qty, 0);
}

function mossynaHasUnusedWelcomeDiscount() {
  return localStorage.getItem("mossyna_welcome_discount_used") !== "true";
}

function mossynaFormatPrice(amount, currency = "TRY") {
  const symbols = { TRY: "₺", USD: "$", EUR: "€" };
  return `${symbols[currency] || ""}${amount.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function mossynaUpdateCartBadge() {
  document.querySelectorAll(".cart-badge").forEach(el => {
    el.textContent = mossynaCartCount();
  });
}

function mossynaShowToast(message) {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(window._mossynaToastTimer);
  window._mossynaToastTimer = setTimeout(() => toast.classList.remove("show"), 2200);
}

/* ---------- Sepet Çekmecesi (Drawer) Render ---------- */
function mossynaRenderCartDrawer() {
  const container = document.querySelector(".cart-drawer-items");
  const subtotalEl = document.querySelector(".cart-drawer-subtotal");
  if (!container) return;

  const cart = mossynaGetCart();
  const lang = mossynaGetLang();

  if (cart.length === 0) {
    container.innerHTML = `<p class="text-center" style="color:var(--text-muted); margin-top:40px;">${mossynaT("cart.empty")}</p>`;
  } else {
    container.innerHTML = cart.map(item => `
      <div class="cart-line" data-id="${item.productId}">
        <img src="${item.image}" alt="${lang === 'en' ? item.nameEn : item.nameTr}" onerror="this.src='https://placehold.co/120x120/e4ede7/1a5c40?text=Mossyna'">
        <div class="cart-line-info">
          <h5>${lang === 'en' ? item.nameEn : item.nameTr}</h5>
          <div>${mossynaFormatPrice(item.unitPrice)}</div>
          <div class="qty-control">
            <button data-action="dec">−</button>
            <span>${item.qty}</span>
            <button data-action="inc">+</button>
            <button data-action="remove" style="margin-left:10px; border:none; background:none; color:var(--danger); cursor:pointer;">✕</button>
          </div>
        </div>
      </div>
    `).join("");
  }

  if (subtotalEl) subtotalEl.textContent = mossynaFormatPrice(mossynaCartSubtotal());
  mossynaUpdateCartBadge();
}

document.addEventListener("click", (e) => {
  const line = e.target.closest(".cart-line");
  if (!line) return;
  const productId = Number(line.getAttribute("data-id"));
  const cart = mossynaGetCart();
  const item = cart.find(i => i.productId === productId);
  if (!item) return;

  if (e.target.matches('[data-action="inc"]')) mossynaUpdateQty(productId, item.qty + 1);
  if (e.target.matches('[data-action="dec"]')) mossynaUpdateQty(productId, item.qty - 1);
  if (e.target.matches('[data-action="remove"]')) mossynaRemoveFromCart(productId);
});

document.addEventListener("mossyna:cartchange", mossynaRenderCartDrawer);
document.addEventListener("mossyna:languagechange", mossynaRenderCartDrawer);
document.addEventListener("DOMContentLoaded", () => {
  mossynaUpdateCartBadge();
  mossynaRenderCartDrawer();
});
