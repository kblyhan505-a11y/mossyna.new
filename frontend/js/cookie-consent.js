/* =====================================================================
   MOSSYNA — Çerez Onay Bandı (Cookie Consent)
   KVKK/GDPR uyumluluğu için: kullanıcının tercihi (kabul/reddet)
   localStorage'da saklanır, dil değişince bant metni otomatik güncellenir,
   footer'daki "Çerez Tercihleri" bağlantısıyla tercih her zaman yeniden
   açılıp değiştirilebilir. Şu an sitede zorunlu/işlevsel çerezler dışında
   (analytics/reklam) bir takip aracı bulunmuyor; mossynaHasAnalyticsConsent()
   ileride böyle bir araç eklenirse (ör. Google Analytics) kullanılmak
   üzere hazır bekliyor.
   ===================================================================== */

const MOSSYNA_COOKIE_CONSENT_KEY = "mossyna_cookie_consent";

function mossynaGetCookieConsent() {
  return localStorage.getItem(MOSSYNA_COOKIE_CONSENT_KEY) || "";
}

function mossynaSetCookieConsent(value) {
  localStorage.setItem(MOSSYNA_COOKIE_CONSENT_KEY, value);
}

function mossynaHasAnalyticsConsent() {
  return mossynaGetCookieConsent() === "accepted";
}

function mossynaCookieBannerHTML() {
  return `
    <div class="cookie-consent-inner">
      <p class="cookie-consent-text">
        ${mossynaT("cookies.banner.text")}
        <a href="kvkk.html#cerezler">${mossynaT("cookies.banner.link")}</a>
      </p>
      <div class="cookie-consent-actions">
        <button type="button" class="btn btn-outline btn-sm" data-cookie-reject>${mossynaT("cookies.banner.reject")}</button>
        <button type="button" class="btn btn-primary btn-sm" data-cookie-accept>${mossynaT("cookies.banner.accept")}</button>
      </div>
    </div>
  `;
}

function mossynaGetOrCreateCookieBannerEl() {
  let el = document.getElementById("cookieConsentBanner");
  if (!el) {
    el = document.createElement("div");
    el.id = "cookieConsentBanner";
    el.className = "cookie-consent-banner";
    document.body.appendChild(el);
  }
  return el;
}

function mossynaShowCookieBanner() {
  const el = mossynaGetOrCreateCookieBannerEl();
  el.innerHTML = mossynaCookieBannerHTML();
  document.body.classList.add("has-cookie-banner");
  requestAnimationFrame(() => el.classList.add("visible"));
}

function mossynaHideCookieBanner() {
  const el = document.getElementById("cookieConsentBanner");
  if (el) el.classList.remove("visible");
  document.body.classList.remove("has-cookie-banner");
}

// Footer'daki "Çerez Tercihleri" bağlantısından tercihleri tekrar açmak için
function mossynaOpenCookiePreferences() {
  mossynaShowCookieBanner();
}

document.addEventListener("DOMContentLoaded", () => {
  if (!mossynaGetCookieConsent()) {
    setTimeout(mossynaShowCookieBanner, 700);
  }
});

// Kabul / Reddet / "Çerez Tercihleri" tıklamaları — olay delegasyonu ile
// dinleniyor (bant sonradan DOM'a eklendiği için document üzerinden bağlanır)
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-cookie-accept]")) {
    mossynaSetCookieConsent("accepted");
    mossynaHideCookieBanner();
  } else if (e.target.closest("[data-cookie-reject]")) {
    mossynaSetCookieConsent("rejected");
    mossynaHideCookieBanner();
  } else if (e.target.closest("[data-open-cookie-settings]")) {
    e.preventDefault();
    mossynaOpenCookiePreferences();
  }
});

// Dil değişince, bant açık durumdaysa metnini güncelle
document.addEventListener("mossyna:languagechange", () => {
  const el = document.getElementById("cookieConsentBanner");
  if (el && el.classList.contains("visible")) {
    el.innerHTML = mossynaCookieBannerHTML();
  }
});
