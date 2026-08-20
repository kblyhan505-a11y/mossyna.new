/* =====================================================================
   MOSSYNA — Vitrin İçin Örnek (Mock) Veri

   Amaç: Backend henüz canlıya alınmadığında ya da veritabanı boşken bile
   anasayfa ve ürünler sayfası "boş" görünmesin — göz alıcı, dolu bir
   vitrin göstersin. mossynaFetchProducts/mossynaFetchCategories gerçek
   API'ye ulaşamazsa ya da boş sonuç dönerse (bkz. main.js, products.html)
   buradaki veriler otomatik olarak devreye girer. Sepete ekleme dahil her
   şey gerçek ürünlerle birebir aynı şekilde çalışır (MOSSYNA_PRODUCT_CACHE
   üzerinden).

   Gerçek backend canlıya alınıp ürünler admin panelden eklendiğinde bu
   dosyaya hiç dokunmaya gerek yok — gerçek veri geldiği an mock veri
   otomatik olarak devre dışı kalır.
   ===================================================================== */

const MOSSYNA_MOCK_CATEGORIES = [
  { id: 1, slug: "yatak", name_tr: "Yatak Odası", name_en: "Bedroom", image_url: null },
  { id: 2, slug: "banyo", name_tr: "Banyo", name_en: "Bath", image_url: null },
  { id: 3, slug: "sofra", name_tr: "Sofra & Mutfak", name_en: "Dining & Kitchen", image_url: null },
  { id: 4, slug: "dekor", name_tr: "Dekoratif", name_en: "Decorative", image_url: null },
];

const MOSSYNA_MOCK_PRODUCTS = [
  {
    id: 9001, category_slug: "yatak", is_featured: true, stock_quantity: 18,
    name_tr: "Organik Pamuklu Nevresim Takımı", name_en: "Organic Cotton Duvet Cover Set",
    short_desc_tr: "Çift kişilik, %100 organik pamuk saten dokuma", short_desc_en: "Double size, 100% organic cotton sateen weave",
    price_try: 1290, compare_at_price: 1590,
    primary_image_url: "https://placehold.co/500x500/e4ede7/1a5c40?text=Nevresim+Tak%C4%B1m%C4%B1",
  },
  {
    id: 9002, category_slug: "yatak", is_featured: true, stock_quantity: 12,
    name_tr: "Zeytin Yaprağı Desenli Nevresim Takımı", name_en: "Olive Leaf Patterned Duvet Set",
    short_desc_tr: "Doğadan ilhamla tasarlanmış nakışlı desen", short_desc_en: "Embroidered pattern inspired by nature",
    price_try: 1150, compare_at_price: null,
    primary_image_url: "https://placehold.co/500x500/efece2/1a5c40?text=Zeytin+Yapra%C4%9F%C4%B1",
  },
  {
    id: 9003, category_slug: "banyo", is_featured: true, stock_quantity: 30,
    name_tr: "Otel Tipi Pamuklu Havlu Seti (4'lü)", name_en: "Hotel-Style Cotton Towel Set (4-Piece)",
    short_desc_tr: "600 gr/m² yumuşak ve emici pamuklu havlu", short_desc_en: "600 gsm soft & absorbent cotton towels",
    price_try: 650, compare_at_price: 790,
    primary_image_url: "https://placehold.co/500x500/e4ede7/b8955a?text=Havlu+Seti",
  },
  {
    id: 9004, category_slug: "banyo", is_featured: true, stock_quantity: 15,
    name_tr: "Keten Karışımlı Bornoz", name_en: "Linen-Blend Bathrobe",
    short_desc_tr: "Nefes alabilen keten-pamuk karışımı kumaş", short_desc_en: "Breathable linen-cotton blend fabric",
    price_try: 990, compare_at_price: null,
    primary_image_url: "https://placehold.co/500x500/efece2/1a5c40?text=Bornoz",
  },
  {
    id: 9005, category_slug: "dekor", is_featured: false, stock_quantity: 40,
    name_tr: "Kadife Dekoratif Yastık Kılıfı", name_en: "Velvet Decorative Cushion Cover",
    short_desc_tr: "45x45 cm, gizli fermuarlı kadife kılıf", short_desc_en: "45x45 cm, hidden-zip velvet cover",
    price_try: 340, compare_at_price: null,
    primary_image_url: "https://placehold.co/500x500/e4ede7/1a5c40?text=Yast%C4%B1k+K%C4%B1l%C4%B1f%C4%B1",
  },
  {
    id: 9006, category_slug: "yatak", is_featured: true, stock_quantity: 9,
    name_tr: "Pike Yatak Örtüsü Takımı", name_en: "Quilted Bedspread Set",
    short_desc_tr: "Mevsimlik, iki yüzü kullanılabilir pike", short_desc_en: "Seasonal, reversible quilted bedspread",
    price_try: 1590, compare_at_price: null,
    primary_image_url: "https://placehold.co/500x500/efece2/b8955a?text=Pike+Tak%C4%B1m%C4%B1",
  },
  {
    id: 9007, category_slug: "banyo", is_featured: false, stock_quantity: 25,
    name_tr: "Waffle Dokuma Banyo Havlusu", name_en: "Waffle Weave Bath Towel",
    short_desc_tr: "Hızlı kuruyan waffle doku, otel konforu", short_desc_en: "Fast-drying waffle weave, hotel comfort",
    price_try: 420, compare_at_price: null,
    primary_image_url: "https://placehold.co/500x500/e4ede7/1a5c40?text=Waffle+Havlu",
  },
  {
    id: 9008, category_slug: "yatak", is_featured: true, stock_quantity: 11,
    name_tr: "Organik Keten Çarşaf Takımı", name_en: "Organic Linen Sheet Set",
    short_desc_tr: "Nefes alabilir, sertifikalı organik keten", short_desc_en: "Breathable, certified organic linen",
    price_try: 1450, compare_at_price: 1690,
    primary_image_url: "https://placehold.co/500x500/efece2/1a5c40?text=Keten+%C3%87ar%C5%9Faf",
  },
  {
    id: 9009, category_slug: "sofra", is_featured: false, stock_quantity: 20,
    name_tr: "Jakarlı Sofra Örtüsü", name_en: "Jacquard Table Cloth",
    short_desc_tr: "160x220 cm, leke tutmaz dokuma", short_desc_en: "160x220 cm, stain-resistant weave",
    price_try: 590, compare_at_price: null,
    primary_image_url: "https://placehold.co/500x500/e4ede7/b8955a?text=Sofra+%C3%96rt%C3%BCs%C3%BC",
  },
  {
    id: 9010, category_slug: "sofra", is_featured: false, stock_quantity: 35,
    name_tr: "Keten Peçete Seti (6'lı)", name_en: "Linen Napkin Set (6-Piece)",
    short_desc_tr: "%100 keten, günlük ve özel günler için", short_desc_en: "100% linen, for everyday & special occasions",
    price_try: 290, compare_at_price: null,
    primary_image_url: "https://placehold.co/500x500/efece2/1a5c40?text=Pe%C3%A7ete+Seti",
  },
];

function mossynaGetMockCategories() {
  return MOSSYNA_MOCK_CATEGORIES;
}

/**
 * Gerçek mossynaFetchProducts ile aynı filtre imzasını kabul eder, aynı
 * şekilde MOSSYNA_PRODUCT_CACHE'e kaydeder — böylece sepete ekleme mock
 * ürünlerde de sorunsuz çalışır.
 */
function mossynaGetMockProducts(filters = {}) {
  let list = MOSSYNA_MOCK_PRODUCTS.slice();

  if (filters.category) list = list.filter(p => p.category_slug === filters.category);
  if (filters.isFeatured) list = list.filter(p => p.is_featured);
  if (filters.minPrice !== undefined) list = list.filter(p => p.price_try >= filters.minPrice);
  if (filters.maxPrice !== undefined) list = list.filter(p => p.price_try <= filters.maxPrice);
  if (filters.search) {
    const q = filters.search.toLowerCase();
    list = list.filter(p => p.name_tr.toLowerCase().includes(q) || p.name_en.toLowerCase().includes(q));
  }

  if (filters.sort === "priceAsc") list.sort((a, b) => a.price_try - b.price_try);
  else if (filters.sort === "priceDesc") list.sort((a, b) => b.price_try - a.price_try);
  else list.sort((a, b) => (b.is_featured ? 1 : 0) - (a.is_featured ? 1 : 0));

  if (filters.pageSize) list = list.slice(0, filters.pageSize);

  list.forEach(p => { MOSSYNA_PRODUCT_CACHE[p.id] = p; });
  return list;
}
