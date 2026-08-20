/* =====================================================================
   MOSSYNA ADMIN — Ortak UI Etkileşimleri (sidebar, topbar, toast)
   Backend'e Bağlı: sayfa korumasını ve topbar kullanıcı bilgisini
   gerçek JWT oturumu + GET /api/admin/auth/me üzerinden kurar.
   ===================================================================== */

function mossynaAdminFormatPrice(amount) {
  return "₺" + Number(amount || 0).toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function mossynaAdminFormatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "short", year: "numeric" }) +
    " " + d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
}

function mossynaAdminShowToast(message, isError = false) {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.toggle("toast-error", isError);
  toast.classList.add("show");
  clearTimeout(window._adminToastTimer);
  window._adminToastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

document.addEventListener("DOMContentLoaded", async () => {
  // Korumalı sayfa kontrolü (login.html hariç tüm admin sayfalarında çalışır)
  const isLoginPage = document.getElementById("adminLoginForm");
  let session = null;
  if (!isLoginPage) {
    session = await mossynaAdminRequireAuth();
    if (!session) return; // login'e yönlendirildi
  }

  // Topbar kullanıcı bilgisi
  if (session) {
    const nameEl = document.querySelector("[data-admin-name]");
    const roleEl = document.querySelector("[data-admin-role]");
    const avatarEl = document.querySelector("[data-admin-avatar]");
    const displayName = session.username || session.email || "Yönetici";
    if (nameEl) nameEl.textContent = displayName;
    if (roleEl) roleEl.textContent = session.role === "superadmin" ? "Süper Yönetici" : "Yönetici";
    if (avatarEl) avatarEl.textContent = displayName.split(/[\s.@]+/).filter(Boolean).map(w => w[0]).join("").slice(0, 2).toUpperCase();
  }

  // Aktif menü linkini işaretle
  const currentPage = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".admin-nav a").forEach(link => {
    const href = link.getAttribute("href");
    if (href === currentPage) link.classList.add("active");
  });

  // Mobil sidebar aç/kapat
  const hamburger = document.querySelector(".hamburger-admin");
  const sidebar = document.querySelector(".admin-sidebar");
  hamburger?.addEventListener("click", () => sidebar.classList.toggle("open"));
  document.addEventListener("click", (e) => {
    if (sidebar?.classList.contains("open") && !sidebar.contains(e.target) && !hamburger.contains(e.target)) {
      sidebar.classList.remove("open");
    }
  });

  // Çıkış
  document.querySelectorAll("[data-admin-logout]").forEach(btn => {
    btn.addEventListener("click", mossynaAdminLogout);
  });

  if (isLoginPage) return;

  // Düşük stok / mesaj rozetleri — gerçek API'den sayım
  try {
    const lowStock = await mossynaAdminApi.get("/api/admin/products?status=low&page_size=1");
    const lowStockBadge = document.querySelector("[data-lowstock-badge]");
    if (lowStockBadge) {
      if (lowStock.total > 0) { lowStockBadge.textContent = lowStock.total; lowStockBadge.classList.remove("hidden"); }
      else lowStockBadge.classList.add("hidden");
    }
  } catch (err) {
    // Rozet güncellenemedi — sessizce yoksay, sayfa içeriği kendi hata durumunu ayrıca gösterir.
  }

  try {
    const newMessages = await mossynaAdminApi.get("/api/admin/messages?status=new");
    const msgBadge = document.querySelector("[data-messages-badge]");
    if (msgBadge) {
      if (newMessages.length > 0) { msgBadge.textContent = newMessages.length; msgBadge.classList.remove("hidden"); }
      else msgBadge.classList.add("hidden");
    }
  } catch (err) {
    // Rozet güncellenemedi — sessizce yoksay.
  }
});
