/* =====================================================================
   MOSSYNA ADMIN — Hakkımızda Fotoğrafları — Backend'e Bağlı

   GET/POST/DELETE /api/admin/about-photos ve PUT /api/admin/about-photos/{id}
   uçlarını kullanır (bkz. backend/app/routers/about.py). Yükleme anında,
   HTML5 canvas ile TARAYICI TARAFINDA 4:3 oranında merkezden kırpılmış bir
   anlık önizleme gösterilir (0 sn gecikme) — ardından orijinal dosya sunucuya
   yüklenir; sunucu Pillow ile AYNI 4:3 oranında gerçek kırpmayı yapar ve
   kalıcı olarak kaydeder. Önizleme, gerçek sonucun neredeyse birebir aynısıdır.

   Açıklama alanları (TR/EN) alandan çıkıldığında (blur) otomatik kaydedilir;
   fotoğraf kaldırma işlemi de anında sunucudan siler — ayrı bir "Kaydet"
   butonu yoktur (bkz. proje genelindeki "anında kaydet" tasarım tercihi).
   ===================================================================== */

const ABOUT_CROP_RATIO = 4 / 3; // genişlik / yükseklik — üretim tesisi galerisi için standart oran
const ABOUT_CROP_W = 640;
const ABOUT_CROP_H = 480;

let aboutPhotosCache = []; // sunucudan gelen gerçek kayıtlar: { id, image_url, caption_tr, caption_en, sort_order, _uploading? }

/** Bir File'ı 4:3 oranında merkezden kırpılmış bir data URL önizlemesine dönüştürür (yalnızca anlık önizleme içindir). */
function mossynaCropImageCenter(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const srcRatio = img.width / img.height;
        let sx, sy, sw, sh;
        if (srcRatio > ABOUT_CROP_RATIO) {
          sh = img.height;
          sw = sh * ABOUT_CROP_RATIO;
          sx = (img.width - sw) / 2;
          sy = 0;
        } else {
          sw = img.width;
          sh = sw / ABOUT_CROP_RATIO;
          sx = 0;
          sy = (img.height - sh) / 2;
        }
        const canvas = document.createElement("canvas");
        canvas.width = ABOUT_CROP_W;
        canvas.height = ABOUT_CROP_H;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, ABOUT_CROP_W, ABOUT_CROP_H);
        resolve(canvas.toDataURL("image/jpeg", 0.88));
      };
      img.onerror = () => reject(new Error("Görsel okunamadı"));
      img.src = e.target.result;
    };
    reader.onerror = () => reject(new Error("Dosya okunamadı"));
    reader.readAsDataURL(file);
  });
}

/** Hem gerçek sunucu yollarını (/media/...) hem de geçici data: URL önizlemelerini doğru şekilde çözer. */
function mossynaAboutPhotoSrc(photo) {
  if (!photo.image_url) return "";
  if (photo.image_url.startsWith("data:") || /^https?:\/\//.test(photo.image_url)) return photo.image_url;
  return `${MOSSYNA_API_BASE_URL}${photo.image_url}`;
}

function mossynaRenderAboutPhotoGrid() {
  const grid = document.getElementById("aboutPhotoGrid");
  const emptyState = document.getElementById("aboutPhotoEmptyState");
  document.getElementById("aboutPhotoCountLabel").textContent = `Fotoğraflar (${aboutPhotosCache.length})`;

  if (!aboutPhotosCache.length) {
    grid.classList.add("hidden");
    grid.innerHTML = ""; // Son fotoğraf kaldırıldığında eski (gizli ama DOM'da kalan) kartları da temizle
    emptyState.classList.remove("hidden");
    return;
  }
  emptyState.classList.add("hidden");
  grid.classList.remove("hidden");

  grid.innerHTML = aboutPhotosCache.map((photo) => `
    <div class="crop-preview-item">
      <img class="crop-thumb" src="${mossynaAboutPhotoSrc(photo)}" alt="Kırpma önizlemesi" style="${photo._uploading ? "opacity:.5;" : ""}">
      ${photo._uploading ? '<div class="form-hint" style="margin:4px 0;">Yükleniyor…</div>' : ""}
      <div class="crop-body">
        <input type="text" data-caption-tr="${photo.id}" value="${(photo.caption_tr || "").replace(/"/g, "&quot;")}" placeholder="Açıklama (TR) — ör. Dokuma Atölyesi" ${photo._uploading ? "disabled" : ""}>
        <input type="text" data-caption-en="${photo.id}" value="${(photo.caption_en || "").replace(/"/g, "&quot;")}" placeholder="Caption (EN)" ${photo._uploading ? "disabled" : ""}>
        <div class="crop-actions">
          <button type="button" class="btn btn-danger btn-sm" data-remove-about="${photo.id}" ${photo._uploading ? "disabled" : ""}>Kaldır</button>
        </div>
      </div>
    </div>
  `).join("");
}

async function mossynaLoadAboutPhotos() {
  try {
    aboutPhotosCache = await mossynaAdminApi.get("/api/admin/about-photos");
  } catch (err) {
    aboutPhotosCache = [];
    mossynaAdminShowToast(err.message, true);
  }
  mossynaRenderAboutPhotoGrid();
}

async function mossynaHandleAboutFiles(files) {
  for (const file of Array.from(files)) {
    if (!file.type.startsWith("image/")) continue;

    const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    let previewUrl = "";
    try {
      previewUrl = await mossynaCropImageCenter(file);
    } catch (err) {
      // Anlık önizleme oluşturulamasa bile yükleme denemesi yapılır.
    }
    aboutPhotosCache.push({ id: tempId, image_url: previewUrl, caption_tr: "", caption_en: "", _uploading: true });
    mossynaRenderAboutPhotoGrid();

    const form = new FormData();
    form.append("file", file);
    try {
      const saved = await mossynaAdminApi.post("/api/admin/about-photos", form, true);
      const idx = aboutPhotosCache.findIndex(p => p.id === tempId);
      if (idx > -1) aboutPhotosCache[idx] = saved;
    } catch (err) {
      aboutPhotosCache = aboutPhotosCache.filter(p => p.id !== tempId);
      mossynaAdminShowToast(`Fotoğraf yüklenemedi: ${err.message}`, true);
    }
    mossynaRenderAboutPhotoGrid();
  }
}

async function mossynaSaveAboutCaption(photoId) {
  const photo = aboutPhotosCache.find(p => String(p.id) === String(photoId));
  if (!photo || photo._uploading) return;

  const trInput = document.querySelector(`[data-caption-tr="${photoId}"]`);
  const enInput = document.querySelector(`[data-caption-en="${photoId}"]`);
  const payload = {
    caption_tr: trInput ? (trInput.value.trim() || null) : photo.caption_tr,
    caption_en: enInput ? (enInput.value.trim() || null) : photo.caption_en,
  };
  if (payload.caption_tr === (photo.caption_tr || null) && payload.caption_en === (photo.caption_en || null)) return; // değişiklik yok

  try {
    const updated = await mossynaAdminApi.put(`/api/admin/about-photos/${photoId}`, payload);
    Object.assign(photo, updated);
  } catch (err) {
    mossynaAdminShowToast(err.message, true);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  const uploadZone = document.getElementById("aboutUploadZone");
  if (!uploadZone) return; // bu script yalnızca hakkimizda.html'de çalışır
  if (!mossynaAdminIsLoggedIn()) return;

  const imageInput = document.getElementById("aboutImageInput");
  uploadZone.addEventListener("click", () => imageInput.click());
  imageInput.addEventListener("change", (e) => mossynaHandleAboutFiles(e.target.files));
  uploadZone.addEventListener("dragover", (e) => { e.preventDefault(); uploadZone.classList.add("dragover"); });
  uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
  uploadZone.addEventListener("drop", (e) => {
    e.preventDefault(); uploadZone.classList.remove("dragover");
    mossynaHandleAboutFiles(e.dataTransfer.files);
  });

  // Açıklama alanları odağı kaybettiğinde (blur) otomatik kaydedilir.
  // NOT: "blur" olayı yukarı doğru yayılmaz (bubble etmez) — bu yüzden dinleyici
  // "capture" aşamasında (üçüncü parametre = true) eklenmiştir.
  document.getElementById("aboutPhotoGrid").addEventListener("blur", (e) => {
    const photoId = e.target.getAttribute("data-caption-tr") || e.target.getAttribute("data-caption-en");
    if (photoId) mossynaSaveAboutCaption(photoId);
  }, true);

  document.getElementById("aboutPhotoGrid").addEventListener("click", async (e) => {
    const photoId = e.target.getAttribute("data-remove-about");
    if (!photoId) return;
    if (!confirm("Bu fotoğrafı kaldırmak istediğinizden emin misiniz? Bu işlem geri alınamaz.")) return;
    try {
      await mossynaAdminApi.del(`/api/admin/about-photos/${photoId}`);
      aboutPhotosCache = aboutPhotosCache.filter(p => String(p.id) !== photoId);
      mossynaRenderAboutPhotoGrid();
      mossynaAdminShowToast("Fotoğraf kaldırıldı.");
    } catch (err) {
      mossynaAdminShowToast(err.message, true);
    }
  });

  await mossynaLoadAboutPhotos();
});
