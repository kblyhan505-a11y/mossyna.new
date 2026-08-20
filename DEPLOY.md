# Mossyna — Production'a Alma Rehberi (Render + Cloudflare)

Bu rehber, projeyi gerçek bir domain üzerinden internete açmak için gereken adımları sırayla anlatır. Mimari: **Render** (backend + veritabanı + iki statik site) + **Cloudflare** (domain, DNS, görsel depolama için R2). Kod zaten GitHub'da olduğu için doğrudan buradan başlayabilirsin.

Sırayla ilerle — her adım bir sonrakinin ön koşulu.

---

## 1. Domain satın al (Cloudflare Registrar)

1. [dash.cloudflare.com](https://dash.cloudflare.com) → hesap aç (yoksa) → sol menüden **Domain Registration**.
2. İstediğin alan adını ara (ör. `mossyna.com`) ve satın al. Cloudflare kâr marjı eklemiyor, registry'nin ücretini alıyor (`.com` için yıllık ~10-15$).
3. Satın aldığında domain otomatik olarak aynı Cloudflare hesabında bir "zone" olarak DNS yönetimine açılır — ekstra bir şey yapmana gerek yok, sıradaki adımlarda buraya kayıt ekleyeceğiz.

---

## 2. Görsel depolama için Cloudflare R2 bucket oluştur

Backend'i birden fazla kopya (autoscaling) çalışacak şekilde kuracağımız için ürün görselleri artık backend'in kendi diskine değil, paylaşılan bir nesne depolamaya (R2) yazılacak.

1. Cloudflare Dashboard → sol menüden **R2 Object Storage** → **Create bucket**. İsim: `mossyna-media`.
2. Bucket'a girip **Settings** sekmesi → **Custom Domains** → **Add** → `media.mossyna.com` yaz → **Continue** → **Connect Domain** (Cloudflare gerekli DNS kaydını domain zaten kendi hesabında olduğu için otomatik ekler; birkaç dakika içinde "Active" olur).
3. R2 ana sayfasında **Account Details** kutusunda **API Tokens** yanındaki **Manage** → **Create API Token**. Yetki olarak **Object Read & Write** seç, sadece `mossyna-media` bucket'ına kapsayabilirsin (opsiyonel ama önerilir). Oluşturunca sana bir **Access Key ID** ve **Secret Access Key** gösterilir — **bu ekrandan ayrılırsan Secret Access Key'i bir daha göremezsin**, ikisini de bir yere kopyala (adım 4'te Render'a gireceğiz).
4. Aynı sayfada hesap ID'ni (Account ID) not al — endpoint URL'in bir parçası: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.

Elinde şunlar olmalı: Access Key ID, Secret Access Key, Endpoint URL, bucket adı (`mossyna-media`), public base URL (`https://media.mossyna.com`).

---

## 3. Render'da Blueprint ile deploy et

1. [render.com](https://render.com) → hesap aç → kredi kartını ekle (Pro kademeler için gerekli).
2. **New +** → **Blueprint** → GitHub hesabını bağla, `mossyna` reposunu seç. Render, repo kökündeki `render.yaml` dosyasını otomatik bulur ve üç servisi (veritabanı, backend, iki statik site) tek seferde önerir.
3. Deploy'u onaylamadan önce Render sana `sync: false` işaretli değişkenleri soracak — bunları şimdi gir (PayTR/Stripe anahtarların yoksa boş bırakıp sonra da girebilirsin, ama S3/R2 bilgilerini şimdi gir):
   - `S3_ENDPOINT_URL` → adım 2.4'teki endpoint
   - `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` → adım 2.3
   - `S3_BUCKET_NAME` → `mossyna-media`
   - `S3_PUBLIC_BASE_URL` → `https://media.mossyna.com`
   - `PAYTR_MERCHANT_ID`, `PAYTR_MERCHANT_KEY`, `PAYTR_MERCHANT_SALT` (PayTR mağaza panelinden)
   - `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY` (Stripe Dashboard → Developers → API keys)
4. **Apply** de. Render veritabanını oluşturur, backend'i build edip başlatır, iki statik siteyi yayınlar. İlk deploy birkaç dakika sürer — `mossyna-backend` servisinin "Live" olduğunu Render panelinden takip edebilirsin.

> Not: `render.yaml` backend'i **Standard** ($25/ay), veritabanını **Pro-4GB** ($55/ay'dan başlar, yüksek erişilebilirlik + otomatik yedekleme dahil) kademesinde tanımlıyor. Trafiğe göre Render panelinden **Pro** kademesine geçip otomatik ölçeklendirmeyi (autoscaling) açabilirsin — bu ayar sadece panelden yapılır, `render.yaml`'da yer almaz.

---

## 4. Veritabanını hazırla (tablo + admin hesabı + örnek veri)

Backend ilk kez "Live" olduğunda veritabanı boştur. Render panelinde `mossyna-backend` servisine gir → **Shell** sekmesi (Pro plan gerektirir) → şunu çalıştır:

```bash
python -m app.scripts.seed
```

Bu, tabloları oluşturur ve `admin@mossyna.com` / `admin123` süper yönetici hesabını ekler. **İlk girişten hemen sonra bu şifreyi değiştir.**

(Shell sekmesi yoksa/kapalıysa: aynı komutu bir "Job" olarak Render panelinden bir kerelik çalıştırabilirsin — Render dokümantasyonundaki "One-Off Jobs" bölümüne bak.)

---

## 5. Domain'leri servislere bağla

Render panelinde her servisin **Settings → Custom Domains** kısmına girip şu eşlemeyi ekle:

| Servis | Domain |
|---|---|
| `mossyna-frontend` | `mossyna.com` ve `www.mossyna.com` |
| `mossyna-admin` | `admin.mossyna.com` |
| `mossyna-backend` | `api.mossyna.com` |

Her biri için Render sana eklemen gereken bir DNS kaydı (genelde bir CNAME) gösterir. Cloudflare Dashboard → domain'in **DNS** sekmesine gidip bu kayıtları ekle (turuncu bulut/proxy simgesini bu kayıtlar için **kapalı** bırakman önerilir, aksi halde Render'ın kendi SSL sertifikası doğrulaması zorlaşabilir — sorun yaşarsan geçici olarak "DNS only" moduna al). Birkaç dakika içinde her üç domain de otomatik HTTPS sertifikasıyla aktif olur.

Frontend/admin kodundaki `js/env.js` dosyaları zaten `api.mossyna.com` adresine bağlanacak şekilde ayarlı — bu adres eşleşmesini değiştirmediysen ekstra bir şey yapmana gerek yok. Farklı bir alt domain kullandıysan `frontend/js/env.js` ve `admin/js/env.js` içindeki `PRODUCTION_API_URL` değerini güncelleyip GitHub'a tekrar push et (Render otomatik yeniden deploy eder).

---

## 6. Shopify (ödeme sayfası) ve Google (tek tık giriş) — production

Site artık kart ödemesi için Shopify'ın kendi güvenli ödeme sayfasına yönlendiriyor, kart bilgisi hiç Mossyna sunucusuna değmiyor. Google girişi de benzer şekilde ayrı bir hesap gerektiriyor. İkisi de birer hesap açıp buradan kopyala-yapıştır yapmaktan ibaret.

### 6.1 Shopify

1. [shopify.com](https://www.shopify.com) üzerinden mağazanızı açın (yoksa).
2. Shopify Admin → **Ayarlar → Uygulamalar ve satış kanalları → Uygulama Geliştir → Uygulama oluştur**. **Storefront API** yetkilerini açıp uygulamayı yükleyin (Install) — size bir **Storefront API erişim belirteci** verecek. Aynı ekranda webhook imzalama sırrını (secret) da not alın.
3. Render'da `mossyna-backend` servisinin **Environment** sekmesinden şu değerleri gir:
   - `SHOPIFY_STORE_DOMAIN` → mağazanızın `.myshopify.com` adresi
   - `SHOPIFY_STOREFRONT_ACCESS_TOKEN` → adım 2'deki belirteç
   - `SHOPIFY_WEBHOOK_SECRET` → adım 2'deki webhook sırrı
4. Shopify Admin → **Ayarlar → Bildirimler** sayfasının en altında **Webhooks** bölümü → **Webhook oluştur** → olay: **Order payment** (sipariş ödemesi), format: JSON, URL: `https://api.mossyna.com/api/payments/webhook/shopify`. Bu adım, müşteri Shopify'da ödemeyi tamamladığında Mossyna'ya "ödeme alındı" haberini gönderir — siparişin durumu otomatik güncellensin diye gereklidir.
5. Mossyna'daki her ürünü Shopify'daki karşılığıyla eşleştirin: Shopify'da ürünü oluşturup varyant ID'sini kopyalayın, `admin.mossyna.com` → Ürünler → ilgili ürünü düzenle → **Shopify Variant ID** alanına yapıştırın. Bu alanı boş bırakılan bir ürün sepete alınıp ödemeye geçildiğinde müşteriye "şu ürün için ödeme hazır değil" gibi açıklayıcı bir hata gösterir — sessizce yanlış çalışmaz.

### 6.2 Google ile Giriş

1. [console.cloud.google.com](https://console.cloud.google.com) → **APIs & Services → Credentials → Create Credentials → OAuth Client ID** → tür: **Web application**.
2. **Authorized JavaScript origins** kısmına `https://mossyna.com` (ve kullanıyorsanız `https://www.mossyna.com`) ekleyin.
3. Size verilen **Client ID**'yi kopyalayın (Client Secret'a hiç ihtiyacımız yok, boş verin).
4. Bu Client ID'yi İKİ yere de aynen yapıştırın:
   - Render'da backend servisinin **Environment** sekmesi → `GOOGLE_OAUTH_CLIENT_ID`
   - `frontend/js/auth-google.js` dosyasındaki `MOSSYNA_GOOGLE_CLIENT_ID` satırı → değiştirip GitHub'a push edin (Render statik siteyi otomatik yeniden deploy eder)

   İkisi birbirinden farklı olursa Google girişi çalışmaz — birebir aynı değeri kullandığınızdan emin olun.

Herhangi bir env var değiştirdiğinde Render backend servisini otomatik yeniden başlatır.

### 6.3 PayTR / Stripe (artık kullanılmıyor — bu adım isteğe bağlı)

Projenin daha önceki bir aşamasında ödeme sayfası PayTR/Stripe üzerinden kurulmuştu; site artık ödemeyi Shopify'a yönlendirdiği için bu ikisine **ihtiyacınız yok** ve bu adımı atlayabilirsiniz. Kod arka planda hâlâ duruyor (ileride isterseniz ek bir ödeme seçeneği olarak devreye alınabilir), o yüzden silinmedi; sadece şu an müşteri tarafında hiçbir yerden çağrılmıyor. Env değerlerini boş bırakmanız yeterli.

---

## 7. Son kontrol listesi

- [ ] `https://mossyna.com` açılıyor, ürünler listeleniyor (backend'e bağlı, "Sunucuya bağlanılamadı" hatası yok)
- [ ] `https://admin.mossyna.com` açılıyor, `admin@mossyna.com` ile giriş yapılabiliyor (şifreyi değiştirdin mi?)
- [ ] Admin panelden bir ürüne görsel yükleyip `https://media.mossyna.com/...` üzerinden görüntülenebildiğini doğrula
- [ ] Admin panelde bir ürünün DE/FR/RU/AR sekmelerine çeviri girip kaydet, sayfayı yenileyip geri geldiğini doğrula
- [ ] Admin panelde "Hakkımızda" sayfasından bir fotoğraf yükleyip anasayfadaki "Hakkımızda" bölümünde göründüğünü doğrula
- [ ] Test siparişi oluşturup "Ödeme Yap"a bastığında gerçekten Shopify'ın ödeme sayfasına yönlendirdiğini doğrula; test kartıyla ödemeyi tamamlayıp Mossyna admin panelinde siparişin "ödendi" durumuna geçtiğini kontrol et (webhook'un çalıştığının kanıtı)
- [ ] "Google ile Giriş" butonunun gerçekten bir Google hesap seçici açtığını ve giriş sonrası siteye yönlendirdiğini doğrula
- [ ] `https://api.mossyna.com/docs` üzerinden Swagger arayüzünün açıldığını doğrula (bu, herkese açık olmasını istemiyorsan ileride kapatılabilir)

Bir adımda takılırsan hangi adımda olduğunu söylemen yeterli, birlikte devam ederiz.
