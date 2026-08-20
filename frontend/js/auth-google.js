/* =====================================================================
   MOSSYNA — Google ile Tek Tık Giriş (Google Identity Services)

   Backend ucu (POST /api/auth/google) hazır ve bağlı — bkz.
   backend/app/routers/auth.py. Bu özelliği açmak için tek yapmanız gereken:

   1) Google Cloud Console → "APIs & Services" → "Credentials" → "Create
      OAuth client ID" (Web application) ile bir Client ID oluşturun.
      Yetkili JavaScript kökenlerine (Authorized JavaScript origins) hem
      https://mossyna.com.tr hem de test ettiğiniz adresi ekleyin.
   2) Aşağıdaki MOSSYNA_GOOGLE_CLIENT_ID değerini bu Client ID ile değiştirin.
   3) AYNI Client ID'yi backend/.env dosyasındaki GOOGLE_OAUTH_CLIENT_ID
      alanına da yapıştırın — ikisi BİREBİR AYNI olmalıdır. (Client Secret
      gerekmez, sadece Client ID yeterlidir.)

   Placeholder değer değiştirilmeden bırakılırsa buton, kullanıcıya sessizce
   hata vermek yerine anlaşılır bir bilgi mesajı gösterir.
   ===================================================================== */

const MOSSYNA_GOOGLE_CLIENT_ID = "BURAYA_YAPISTIR"; // Google Cloud Console → OAuth Client ID (backend/.env → GOOGLE_OAUTH_CLIENT_ID ile aynı olmalı)

function mossynaGoogleButtonClick() {
  if (!MOSSYNA_GOOGLE_CLIENT_ID || MOSSYNA_GOOGLE_CLIENT_ID === "BURAYA_YAPISTIR") {
    mossynaShowToast(mossynaGetLang() === "tr"
      ? "Google girişi henüz yapılandırılmadı. (Google Client ID eklenmeli.)"
      : "Google sign-in isn't configured yet. (Google Client ID needs to be added.)");
    return;
  }
  if (typeof google === "undefined" || !google.accounts) {
    mossynaShowToast(mossynaGetLang() === "tr"
      ? "Google servislerine ulaşılamadı, lütfen internet bağlantınızı kontrol edin."
      : "Couldn't reach Google services, please check your internet connection.");
    return;
  }
  google.accounts.id.initialize({
    client_id: MOSSYNA_GOOGLE_CLIENT_ID,
    callback: mossynaHandleGoogleCredential,
  });
  google.accounts.id.prompt();
}

async function mossynaHandleGoogleCredential(response) {
  try {
    const result = await mossynaApi.post("/api/auth/google", { credential: response.credential });
    mossynaSetTokens(result.access_token, result.refresh_token);
    mossynaShowToast(mossynaT("auth.loginToast"));
    setTimeout(() => { window.location.href = "index.html"; }, 700);
  } catch (err) {
    mossynaShowToast(err.message);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-google-login]").forEach(btn => {
    btn.addEventListener("click", mossynaGoogleButtonClick);
  });
});
