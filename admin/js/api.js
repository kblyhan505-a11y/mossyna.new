/* =====================================================================
   MOSSYNA ADMIN — Ortak API İstemcisi

   Backend adresini değiştirmek için, bu dosyayı yüklemeden önce
   `window.MOSSYNA_API_BASE_URL = "https://api.mossyna.com.tr";` tanımlayın.
   ===================================================================== */

const MOSSYNA_API_BASE_URL = window.MOSSYNA_API_BASE_URL || "http://localhost:8000";
const MOSSYNA_ADMIN_TOKEN_KEY = "mossyna_admin_access_token";

class MossynaApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = "MossynaApiError";
    this.status = status;
    this.data = data;
  }
}

function mossynaAdminGetToken() {
  return localStorage.getItem(MOSSYNA_ADMIN_TOKEN_KEY);
}

function mossynaAdminSetToken(token) {
  localStorage.setItem(MOSSYNA_ADMIN_TOKEN_KEY, token);
}

function mossynaAdminClearToken() {
  localStorage.removeItem(MOSSYNA_ADMIN_TOKEN_KEY);
}

/**
 * Admin backend uçlarına istek atan ortak fonksiyon. Varsayılan olarak
 * Authorization header'ı ekler (admin uçlarının neredeyse tamamı korumalıdır).
 */
async function mossynaAdminApiRequest(path, options = {}) {
  const { method = "GET", body = null, auth = true, isForm = false } = options;

  const headers = {};
  if (!isForm && body) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = mossynaAdminGetToken();
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
      "Backend sunucusuna bağlanılamadı. `uvicorn app.main:app --reload` ile çalıştığından emin olun.",
      0,
      null
    );
  }

  if (response.status === 401 && auth) {
    // Oturum süresi dolmuş veya geçersiz — yönetici girişe geri gönderilir
    mossynaAdminClearToken();
    if (!window.location.pathname.endsWith("login.html")) {
      window.location.href = "login.html";
    }
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

const mossynaAdminApi = {
  get: (path) => mossynaAdminApiRequest(path, { method: "GET" }),
  post: (path, body, isForm = false) => mossynaAdminApiRequest(path, { method: "POST", body, isForm }),
  put: (path, body) => mossynaAdminApiRequest(path, { method: "PUT", body }),
  del: (path) => mossynaAdminApiRequest(path, { method: "DELETE" }),
  postPublic: (path, body) => mossynaAdminApiRequest(path, { method: "POST", body, auth: false }),
  getPublic: (path) => mossynaAdminApiRequest(path, { method: "GET", auth: false }),
};

/** Backend'den dönen "/media/…" gibi göreli görsel yollarını tam URL'e çevirir. */
function mossynaAdminImageUrl(path) {
  if (!path) return "";
  return /^https?:\/\//.test(path) ? path : `${MOSSYNA_API_BASE_URL}${path}`;
}
