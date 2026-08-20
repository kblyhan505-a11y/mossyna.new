/* =====================================================================
   MOSSYNA ADMIN — Kimlik Doğrulama (Auth) — Backend'e Bağlı

   POST /api/admin/auth/login çağrılır, dönen JWT (aud=mossyna-admin)
   localStorage'a kaydedilir (bkz. js/api.js). Token, admin_users
   tablosuna karşı bcrypt ile doğrulanır — Aşama 4'teki sabit
   demo hesap (admin@mossyna.com / admin123) artık kullanılmaz;
   gerçek hesap `python -m app.scripts.seed` ile oluşturulur
   (bkz. backend/README.md).
   ===================================================================== */

const MOSSYNA_ADMIN_PROFILE_KEY = "mossyna_admin_profile";

function mossynaAdminGetProfile() {
  try { return JSON.parse(localStorage.getItem(MOSSYNA_ADMIN_PROFILE_KEY)); } catch (e) { return null; }
}

function mossynaAdminSaveProfile(profile) {
  localStorage.setItem(MOSSYNA_ADMIN_PROFILE_KEY, JSON.stringify(profile));
}

function mossynaAdminIsLoggedIn() {
  return !!mossynaAdminGetToken();
}

function mossynaAdminLogout() {
  mossynaAdminClearToken();
  localStorage.removeItem(MOSSYNA_ADMIN_PROFILE_KEY);
  window.location.href = "login.html";
}

/* Korumalı sayfaların en üstünde çağrılır; token yoksa/işe yaramazsa login'e
   yönlendirir, aksi halde önbellekteki (veya API'den taze çekilen) profili döner. */
async function mossynaAdminRequireAuth() {
  if (!mossynaAdminIsLoggedIn()) {
    window.location.href = "login.html";
    return null;
  }
  let profile = mossynaAdminGetProfile();
  if (profile) return profile;
  try {
    profile = await mossynaAdminApi.get("/api/admin/auth/me");
    mossynaAdminSaveProfile(profile);
    return profile;
  } catch (err) {
    // 401 durumunda mossynaAdminApiRequest zaten login.html'e yönlendirir.
    return null;
  }
}

function mossynaAdminInitLoginForm() {
  const form = document.getElementById("adminLoginForm");
  if (!form) return;

  // Zaten geçerli bir token varsa doğrudan dashboard'a yönlendir
  if (mossynaAdminIsLoggedIn()) {
    window.location.href = "index.html";
    return;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("adminUsername").value.trim();
    const password = document.getElementById("adminPassword").value;
    const errorBox = document.getElementById("adminLoginError");
    errorBox.style.display = "none";

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;

    try {
      const tokens = await mossynaAdminApi.postPublic("/api/admin/auth/login", { username, password });
      mossynaAdminSetToken(tokens.access_token);
      const profile = await mossynaAdminApi.get("/api/admin/auth/me");
      mossynaAdminSaveProfile(profile);
      window.location.href = "index.html";
    } catch (err) {
      errorBox.textContent = err.status === 401
        ? "Kullanıcı adı veya şifre hatalı."
        : err.message;
      errorBox.style.display = "block";
      submitBtn.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", mossynaAdminInitLoginForm);
