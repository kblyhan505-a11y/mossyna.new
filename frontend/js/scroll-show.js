/* =====================================================================
   MOSSYNA — Anasayfa Scroll Animasyonu (GSAP + ScrollTrigger)

   "Kullanıcı aşağı kaydırdıkça havadan gelen kırlentlerin bir kanepeye
   sırayla yerleştiği" efekti. Sadece index.html'de kullanılır.

   Not: gsap.min.js + ScrollTrigger.min.js CDN üzerinden bu dosyadan ÖNCE
   yüklenmelidir (bkz. index.html). CDN herhangi bir sebeple yüklenemezse
   (ağ engeli vb.) bu betik sessizce hiçbir şey yapmaz — kırlentler
   css/style.css'te tanımlı final konumlarında, animasyonsuz ama düzgün
   şekilde görüntülenir (progressive enhancement).
   ===================================================================== */
document.addEventListener("DOMContentLoaded", () => {
  const section = document.getElementById("pillowShow");
  if (!section) return;
  if (typeof gsap === "undefined" || typeof ScrollTrigger === "undefined") {
    console.warn("Mossyna: GSAP/ScrollTrigger yüklenemedi, kırlent animasyonu pasif (statik görünüm devam ediyor).");
    return;
  }

  gsap.registerPlugin(ScrollTrigger);

  const textEl = section.querySelector(".pillow-show-text");
  const pillows = gsap.utils.toArray(section.querySelectorAll(".pillow"));

  gsap.set(textEl, { opacity: 0, y: 24 });
  gsap.set(pillows, { opacity: 1 }); // gerçek başlangıç opaklığı .from() içinde belirlenir

  // Mobilde ekran daha küçük ve kaydırma mesafesi daha "değerli" olduğu için
  // sahneyi daha kısa tutuyoruz — kullanıcı sahnede uzun süre sıkışmış hissetmesin.
  const isCompact = window.matchMedia("(max-width: 640px)").matches;

  const tl = gsap.timeline({
    scrollTrigger: {
      trigger: section,
      start: "top top",
      end: isCompact ? "+=90%" : "+=140%",
      scrub: 0.6,
      pin: true,
      anticipatePin: 1,
    }
  });

  tl.to(textEl, { opacity: 1, y: 0, duration: 0.5, ease: "power1.out" });

  pillows.forEach((pillow, i) => {
    const dir = i % 2 === 0 ? -1 : 1;
    tl.from(pillow, {
      y: -520 - i * 30,
      x: dir * (140 + i * 10),
      rotation: dir * (55 + i * 8),
      opacity: 0,
      duration: 0.6,
      ease: "power2.out",
    }, i === 0 ? ">-0.1" : "<0.35");
  });
});
