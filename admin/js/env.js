/* =====================================================================
   MOSSYNA ADMIN — Ortam Ayarı (Production/Local otomatik geçiş)

   Bu dosya js/api.js'ten ÖNCE yüklenmelidir. Sayfa localhost/127.0.0.1
   üzerinde açıldıysa yerel backend'e (localhost:8000), başka bir adreste
   açıldıysa (ör. admin.mossyna.com) production API adresine bağlanır.

   Backend'i farklı bir alan adında barındırıyorsanız aşağıdaki
   PRODUCTION_API_URL değerini güncelleyip yeniden deploy edin.
   ===================================================================== */

(function () {
  var PRODUCTION_API_URL = "https://api.mossyna.com";
  var isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
  window.MOSSYNA_API_BASE_URL = isLocal ? "http://localhost:8000" : PRODUCTION_API_URL;
})();
