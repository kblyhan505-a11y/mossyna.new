/* =====================================================================
   MOSSYNA — Ortak API İstemcisi (Müşteri Arayüzü)

   Backend'in çalıştığı adresi değiştirmek isterseniz, bu dosyayı yüklemeden
   önce bir <script> içinde `window.MOSSYNA_API_BASE_URL = "https://api.mossyna.com";`
   tanımlayabilirsiniz. Tanımlanmazsa yerel geliştirme adresi kullanılır.
   ===================================================================== */

const MOSSYNA_API_BASE_URL = window.MOSSYNA_API_BASE_URL || "http://localhost:8000";

const MOSSYNA_ACCESS_TOKEN_KEY = "mossyna_access_token";
const MOSSYNA_REFRESH_TOKEN_KEY = "mossyna_refresh_token";

class MossynaApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = "MossynaApiError";
    this.status = status;
    this.data = data;
  }
}

function mossynaGetAccessToken() {
  return localStorage.getItem(MOSSYNA_ACCESS_TOKEN_KEY);
}

function mossynaSetTokens(accessToken, refreshToken) {
  localStorage.setItem(MOSSYNA_ACCESS_TOKEN_KEY, accessToken);
  if (refreshToken) localStorage.setItem(MOSSYNA_REFRESH_TOKEN_KEY, refreshToken);
}

function mossynaClearTokens() {
  localStorage.removeItem(MOSSYNA_ACCESS_TOKEN_KEY);
  localStorage.removeItem(MOSSYNA_REFRESH_TOKEN_KEY);
}

function mossynaIsLoggedIn() {
  return !!mossynaGetAccessToken();
}

/**
 * Backend'e istek atan ortak fonksiyon.
 * @param {string} path - örn. "/api/products"
 * @param {object} options - { method, body, auth, isForm }
 */
async function mossynaApiRequest(path, options = {}) {
  const { method = "GET", body = null, auth = false, isForm = false } = options;

  const headers = {};
  if (!isForm && body) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = mossynaGetAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${MOSSYNA_API_BASE_URL}${path}`, {
      method,
      headers,
      body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
    });
  } catch (networkError) {
    throw new MossynaApiError(
      "Sunucuya bağlanılamadı. Backend'in çalıştığından ve adresin doğru olduğundan emin olun (bkz. KURULUM_REHBERI.md).",
      0,
      null
    );
  }

  const contentType = response.headers.get("content-type") || "";
  let data = null;
  if (contentType.includes("application/json")) {
    data = await response.json().catch(() => null);
  }

  if (!response.ok) {
    const detail = data && (data.detail || data.message);
    const message = typeof detail === "string" ? detail : `İstek başarısız oldu (HTTP ${response.status})`;
    throw new MossynaApiError(message, response.status, data);
  }

  return data;
}

/* ---------- Kısayol fonksiyonlar ---------- */
const mossynaApi = {
  get: (path, auth = false) => mossynaApiRequest(path, { method: "GET", auth }),
  post: (path, body, auth = false) => mossynaApiRequest(path, { method: "POST", body, auth }),
  put: (path, body, auth = false) => mossynaApiRequest(path, { method: "PUT", body, auth }),
  del: (path, auth = false) => mossynaApiRequest(path, { method: "DELETE", auth }),
};
