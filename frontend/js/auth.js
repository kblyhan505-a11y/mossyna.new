/* =====================================================================
   MOSSYNA — Kimlik Doğrulama (Auth) Modülü — Backend'e Bağlı

   POST /api/auth/register ve POST /api/auth/login uçlarını çağırır,
   dönen JWT (access + refresh token) localStorage'a kaydedilir
   (bkz. js/api.js — mossynaSetTokens). Aşama 5 backend'inin gerçek
   bcrypt + JWT akışıdır; artık simülasyon değildir.
   ===================================================================== */

const MOSSYNA_PROFILE_KEY = "mossyna_profile";

function mossynaGetProfile() {
  try { return JSON.parse(localStorage.getItem(MOSSYNA_PROFILE_KEY)); } catch (e) { return null; }
}

function mossynaSaveProfile(profile) {
  localStorage.setItem(MOSSYNA_PROFILE_KEY, JSON.stringify(profile));
}

function mossynaLogout() {
  mossynaClearTokens();
  localStorage.removeItem(MOSSYNA_PROFILE_KEY);
  window.location.href = "login.html";
}

function mossynaIsValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function mossynaSetFieldError(inputEl, message) {
  const group = inputEl.closest(".form-group");
  if (!group) return;
  group.classList.add("has-error");
  let errEl = group.querySelector(".field-error");
  if (!errEl) {
    errEl = document.createElement("div");
    errEl.className = "field-error";
    group.appendChild(errEl);
  }
  errEl.textContent = message;
}

function mossynaClearFieldError(inputEl) {
  const group = inputEl.closest(".form-group");
  if (!group) return;
  group.classList.remove("has-error");
}

/* Giriş/kayıt sonrası profil bilgisini çekip local'e kaydeder (header'da isim göstermek için) */
async function mossynaFetchAndStoreProfile() {
  try {
    const profile = await mossynaApi.get("/api/auth/me", true);
    mossynaSaveProfile(profile);
    return profile;
  } catch (err) {
    return null;
  }
}

/* ---------- Şifre göster/gizle ---------- */
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".toggle-pw");
  if (!btn) return;
  const input = btn.previousElementSibling;
  if (!input) return;
  input.type = input.type === "password" ? "text" : "password";
  btn.textContent = input.type === "password" ? "Göster" : "Gizle";
});

/* ---------- Kayıt Formu ---------- */
function mossynaInitRegisterForm() {
  const form = document.getElementById("registerForm");
  if (!form) return;

  const roleRadios = form.querySelectorAll('input[name="role"]');
  const corporateFields = document.getElementById("registerCorporateFields");
  const b2bBenefits = document.getElementById("b2bBenefitsBox");

  roleRadios.forEach(r => r.addEventListener("change", (e) => {
    const isCorporate = e.target.value === "corporate";
    corporateFields.classList.toggle("hidden", !isCorporate);
    if (b2bBenefits) b2bBenefits.classList.toggle("hidden", !isCorporate);
  }));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    let valid = true;

    const firstName = form.querySelector("#regFirstName");
    const lastName = form.querySelector("#regLastName");
    const email = form.querySelector("#regEmail");
    const phone = form.querySelector("#regPhone");
    const password = form.querySelector("#regPassword");
    const confirmPassword = form.querySelector("#regConfirmPassword");
    const kvkk = form.querySelector("#regKvkk");
    const role = form.querySelector('input[name="role"]:checked')?.value || "individual";

    [firstName, lastName, email, phone, password, confirmPassword].forEach(mossynaClearFieldError);

    [firstName, lastName, phone].forEach(input => {
      if (!input.value.trim()) { mossynaSetFieldError(input, mossynaT("auth.error.required")); valid = false; }
    });

    if (!email.value.trim() || !mossynaIsValidEmail(email.value.trim())) {
      mossynaSetFieldError(email, mossynaT("auth.error.email"));
      valid = false;
    }
    if (password.value.length < 6) {
      mossynaSetFieldError(password, mossynaT("auth.error.passwordlen"));
      valid = false;
    }
    if (password.value !== confirmPassword.value) {
      mossynaSetFieldError(confirmPassword, mossynaT("auth.error.passwordmismatch"));
      valid = false;
    }
    if (!kvkk.checked) {
      mossynaShowToast(mossynaT("auth.error.kvkk"));
      valid = false;
    }
    if (role === "corporate") {
      const company = form.querySelector("#regCompanyName");
      const taxNumber = form.querySelector("#regTaxNumber");
      if (!company.value.trim() || !taxNumber.value.trim()) {
        mossynaShowToast(mossynaGetLang() === "tr"
          ? "Kurumsal hesaplar için firma adı ve vergi no zorunludur."
          : "Company name and tax number are required for corporate accounts.");
        valid = false;
      }
    }

    if (!valid) return;

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;

    try {
      const payload = {
        first_name: firstName.value.trim(),
        last_name: lastName.value.trim(),
        email: email.value.trim(),
        phone: phone.value.trim(),
        password: password.value,
        role,
        company_name: role === "corporate" ? form.querySelector("#regCompanyName").value.trim() : null,
        tax_office: role === "corporate" ? form.querySelector("#regTaxOffice").value.trim() : null,
        tax_number: role === "corporate" ? form.querySelector("#regTaxNumber").value.trim() : null,
      };

      const tokens = await mossynaApi.post("/api/auth/register", payload);
      mossynaSetTokens(tokens.access_token, tokens.refresh_token);
      await mossynaFetchAndStoreProfile();

      mossynaShowToast(mossynaT("auth.welcomeToast"));
      setTimeout(() => { window.location.href = "index.html"; }, 1400);
    } catch (err) {
      if (err.status === 409) {
        mossynaSetFieldError(email, mossynaT("auth.error.emailexists"));
      } else {
        mossynaShowToast(err.message, true);
      }
      submitBtn.disabled = false;
    }
  });
}

/* ---------- Giriş Formu ---------- */
function mossynaInitLoginForm() {
  const form = document.getElementById("loginForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = form.querySelector("#loginEmail");
    const password = form.querySelector("#loginPassword");

    mossynaClearFieldError(email);
    mossynaClearFieldError(password);

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;

    try {
      const tokens = await mossynaApi.post("/api/auth/login", { email: email.value.trim(), password: password.value });
      mossynaSetTokens(tokens.access_token, tokens.refresh_token);
      await mossynaFetchAndStoreProfile();

      mossynaShowToast(mossynaT("auth.loginToast"));
      setTimeout(() => { window.location.href = "index.html"; }, 900);
    } catch (err) {
      if (err.status === 401) {
        mossynaSetFieldError(password, mossynaT("auth.error.invalidlogin"));
      } else {
        mossynaShowToast(err.message, true);
      }
      submitBtn.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  mossynaInitRegisterForm();
  mossynaInitLoginForm();

  // Header'daki hesap ikonunu oturum durumuna göre güncelle (varsa)
  const accountLink = document.querySelector("[data-account-link]");
  if (accountLink && mossynaIsLoggedIn()) {
    const profile = mossynaGetProfile();
    if (profile) accountLink.setAttribute("title", `${profile.first_name} ${profile.last_name}`);
  }
});
