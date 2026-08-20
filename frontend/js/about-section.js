/* =====================================================================
   MOSSYNA — Hakkımızda Galerisi (Ana Sayfa #about Bölümü)

   GET /api/about-photos (public) ile admin panelinde (hakkimizda.html)
   yüklenen üretim tesisi fotoğraflarını çeker ve #about bölümündeki galeriye
   basar. Henüz hiç fotoğraf yüklenmemişse galeri sessizce gizli kalır —
   yalnızca üstteki tanıtım metni gösterilir (bkz. index.html #about).
   ===================================================================== */

function mossynaAboutPhotoImgSrc(photo) {
  if (!photo.image_url) return "https://placehold.co/640x480/e4ede7/1a5c40?text=Mossyna";
  return /^https?:\/\//i.test(photo.image_url) ? photo.image_url : `${MOSSYNA_API_BASE_URL}${photo.image_url}`;
}

function mossynaAboutPhotoCaption(photo, lang) {
  const preferred = lang === "en" ? photo.caption_en : photo.caption_tr;
  const fallback = lang === "en" ? photo.caption_tr : photo.caption_en;
  return (preferred || fallback || "").trim();
}

async function mossynaLoadAboutGallery() {
  const gallery = document.querySelector("[data-about-gallery]");
  if (!gallery) return;

  let photos = [];
  try {
    photos = await mossynaApi.get("/api/about-photos");
  } catch (err) {
    photos = []; // Backend'e ulaşılamazsa galeri sessizce gizli kalır — sayfanın geri kalanı etkilenmez.
  }

  if (!photos.length) {
    gallery.classList.add("hidden");
    gallery.innerHTML = "";
    return;
  }

  const lang = mossynaGetLang();
  gallery.innerHTML = photos.map(p => {
    const caption = mossynaAboutPhotoCaption(p, lang);
    return `
      <figure class="about-photo-card">
        <img src="${mossynaAboutPhotoImgSrc(p)}" alt="${(caption || "Mossyna").replace(/"/g, "&quot;")}" loading="lazy" onerror="this.src='https://placehold.co/640x480/e4ede7/1a5c40?text=Mossyna'">
        ${caption ? `<figcaption>${caption}</figcaption>` : ""}
      </figure>
    `;
  }).join("");
  gallery.classList.remove("hidden");
}

document.addEventListener("DOMContentLoaded", mossynaLoadAboutGallery);
document.addEventListener("mossyna:languagechange", mossynaLoadAboutGallery);
