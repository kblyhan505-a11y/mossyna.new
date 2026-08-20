# Mossyna — Kurulum ve Çalıştırma Rehberi

Bu rehber, teslim edilen zip dosyasını açtıktan sonra projeyi kendi bilgisayarınızda nasıl çalıştıracağınızı adım adım anlatır.

## Güncelleme: Artık tek, bağlı bir sistem

Önceki teslimatta `frontend/` ve `admin/` demo modunda (localStorage üzerinde sahte veriyle) çalışıyordu. **Artık bağlılar**: müşteri sitesi ve yönetici paneli, gerçek verileri `backend/`'deki FastAPI + PostgreSQL API'sinden çekiyor — ürünler, sepet→sipariş dönüşümü, giriş/kayıt (JWT), döviz kuru, ödeme başlatma ve iletişim formu dahil. Bu yüzden **artık önce backend'in ayakta olması gerekiyor**; backend çalışmadan siteyi açarsanız ürün listeleri ve formlar "Sunucuya bağlanılamadı" hatası gösterir.

Aşağıdaki adımlar sırayla: (1) backend'i kurup çalıştırma, (2) frontend/admin'i aynı bilgisayarda servis etme.

---

## 1. Backend'i kurun ve çalıştırın

Gereken: **Python 3.11+** ve **PostgreSQL**.

### 1.1 PostgreSQL kurulumu

- **Mac:** `brew install postgresql@16` sonra `brew services start postgresql@16`
- **Windows:** [postgresql.org/download](https://www.postgresql.org/download/windows/) adresinden yükleyiciyi indirip kurun.
- **Linux (Ubuntu/Debian):** `sudo apt install postgresql`

Kurulumdan sonra bir veritabanı oluşturun:
```bash
createdb mossyna_db
```
(Windows'ta pgAdmin arayüzünden de "mossyna_db" adında boş bir veritabanı oluşturabilirsiniz.)

### 1.2 Backend bağımlılıklarını kurun

```bash
cd mossyna/backend
python3 -m venv venv

# Sanal ortamı aktif edin:
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 1.3 Ayarları yapılandırın

```bash
cp .env.example .env
```
`.env` dosyasını bir metin editörüyle açıp en azından şu satırı kendi bilgisayarınıza göre düzenleyin:
```
DATABASE_URL=postgresql://KULLANICI_ADINIZ:ŞİFRENİZ@localhost:5432/mossyna_db
```
`CORS_ORIGINS` satırı varsayılan olarak `http://localhost:5500`'dür — aşağıda frontend'i de aynı port üzerinden açacağız, bu yüzden bu değeri değiştirmenize gerek yok.

`.env` dosyasındaki `CHANGE_ME` yazan tüm satırları şimdilik olduğu gibi bırakabilirsiniz — bilgisayarınızda deneme yaparken bunlara ihtiyacınız yok. Sadece şunu bilin: `SHOPIFY_...` ve `GOOGLE_OAUTH_CLIENT_ID` satırları doldurulmadan (1) ödeme adımında "Ödeme Yap" butonuna basıldığında sistem nazikçe "ödeme sayfasına şu an ulaşılamıyor" mesajı gösterir (sipariş yine de oluşur, kaybolmaz) ve (2) "Google ile Giriş" butonuna basıldığında "Google girişi henüz yapılandırılmadı" uyarısı çıkar. Bunlar hata değil, kasıtlı bir güvenlik davranışıdır — gerçek bilgileri gireceğiniz an her ikisi de sorunsuz çalışmaya başlar. Bu iki bağlantıyı gerçek domain'inizde nasıl kuracağınız aşağıda "Canlıya geçmeden önce eklemeniz gereken 2 bağlantı" bölümünde ve `DEPLOY.md`'de adım adım anlatılıyor. PayTR/Stripe satırları ise artık kullanılmıyor (bkz. aşağıdaki not) — boş bırakabilirsiniz.

### 1.4 Veritabanı tablolarını ve başlangıç verisini oluşturun

```bash
python -m app.scripts.seed
```
Bu komut otomatik olarak: tüm tabloları oluşturur, bir süper yönetici hesabı (**admin@mossyna.com** / **admin123**), kategoriler, örnek ürün kataloğu, "WELCOME10" indirim kuponu ve başlangıç döviz kuru ekler.

> Güvenlik notu: `admin@mossyna.com` / `admin123` yalnızca ilk giriş içindir. Gerçek kullanıma geçmeden önce admin panelinden (veya veritabanından) şifreyi değiştirin.

### 1.5 Sunucuyu başlatın

```bash
uvicorn app.main:app --reload --port 8000
```

Bu terminali açık bırakın — backend bu pencerede çalışmaya devam eder. Tarayıcıda `http://localhost:8000/docs` adresine giderek Swagger arayüzünden tüm API uçlarını (ürünler, sipariş oluşturma, kur güncelleme, ödeme başlatma vb.) tek tek deneyebilirsiniz.

---

## 2. Frontend ve admin paneli servis edin

Backend çalışırken **yeni bir terminal penceresi** açın (öncekini kapatmayın) ve proje kök klasöründen:

```bash
cd mossyna
python3 -m http.server 5500
```
(Windows'ta `python` yazmanız gerekebilir: `python -m http.server 5500`)

Tarayıcınızda şu adresleri açın:
- **Müşteri sitesi:** `http://localhost:5500/frontend/index.html`
- **Yönetici paneli:** `http://localhost:5500/admin/login.html` → **admin@mossyna.com** / **admin123**

> Not: Doğrudan dosyaya çift tıklayıp tarayıcıda açmayın (`file://...`) — bazı tarayıcı güvenlik kısıtlamaları yüzünden JavaScript modülleri ve API istekleri düzgün çalışmaz. Mutlaka yukarıdaki gibi bir yerel sunucu üzerinden açın.

Backend'in adresini değiştirmek isterseniz (ör. başka bir bilgisayarda/portta çalıştırıyorsanız), `frontend/` ve `admin/` klasörlerindeki her HTML dosyasının `<script src="js/api.js">` etiketinden **önce** şunu ekleyin:
```html
<script>window.MOSSYNA_API_BASE_URL = "http://başka-adres:port";</script>
```

---

## Neler artık gerçek, neler hâlâ demo/basitleştirilmiş?

- ✅ Ürün listeleme, filtreleme, sepet→sipariş oluşturma, giriş/kayıt (JWT), iletişim formu, admin ürün/kategori/mesaj/kur yönetimi — hepsi gerçek API çağrılarıyla çalışıyor.
- ✅ Ürün görselleri admin panelinden gerçek dosya yüklemesiyle (`backend/media/` altına) kaydediliyor.
- ✅ **Ödeme adımı artık Shopify'a bağlı:** Müşteri "Ödeme Yap"a bastığında, kart bilgisi hiç Mossyna sunucusuna değmeden doğrudan Shopify'ın kendi güvenli ödeme sayfasına yönlendiriliyor. Aşağıdaki "Canlıya geçmeden önce eklemeniz gereken 2 bağlantı" bölümünde anlatılan Shopify bilgilerini girmeniz yeterli — kod tarafında ekstra bir şey yapmanıza gerek yok. (Eski PayTR/Stripe kart-formu kodu artık kullanılmıyor; `.env`'deki o satırları boş bırakabilirsiniz.)
- ✅ **Google ile tek tık giriş** de bağlı — yalnızca bir Google Client ID eklemeniz yeterli (Client Secret gerekmez), aşağıda anlatılıyor.
- ✅ **Çoklu dil ürün çevirileri (DE/FR/RU/AR)** artık admin panelinden girildiğinde gerçekten kaydediliyor ve sitede o dile geçildiğinde gösteriliyor. Bir dili boş bırakırsanız, o dildeki ziyaretçiye otomatik olarak Türkçe metin gösterilir — hiçbir ürün "boş" görünmez.
- ✅ **Hakkımızda fotoğrafları:** Admin panelinden yüklediğiniz üretim tesisi fotoğrafları otomatik olarak 4:3 oranında kırpılıp anasayfadaki "Hakkımızda" bölümünde yayınlanıyor.
- ⚠️ **Misafir sipariş adresi:** `addresses` tablosu şu an yalnızca kayıtlı kullanıcılara bağlı olacak şekilde tasarlandı; misafir siparişlerde teslimat adresi sipariş kaydına kalıcı olarak yazılmaz (sipariş yine oluşturulur, tutar ve ürünler doğru kaydedilir). Gerçek kullanıma geçmeden önce bu, ayrı bir "misafir adres" alanı eklenerek tamamlanmalıdır.
- ⚠️ **E-posta bildirimleri** (sipariş onayı, mesaj yanıtı vb.) kod içinde yer tutucu olarak belirtilmiştir; gerçek bir e-posta servisi (SendGrid, SES vb.) bağlanmamıştır.

---

## Canlıya geçmeden önce eklemeniz gereken 2 bağlantı

Site tasarım, yönetim paneli ve sunucu tarafı artık tamamen hazır ve birbirine bağlı. Geriye, güvenlik gereği sizin elinizle girmeniz gereken yalnızca **iki** bağlantı bilgisi kaldı — ikisi de birer hesap açıp oradan kopyala-yapıştır yapmaktan ibaret, kod yazmanız gerekmiyor.

### 1) Shopify — ödeme sayfası

Mossyna, ürün ve fiyat bilgisini kendi sisteminde tutmaya devam ediyor; Shopify yalnızca kart bilgisinin güvenle alındığı ödeme ekranı olarak kullanılıyor.

1. [shopify.com](https://www.shopify.com) üzerinden bir mağaza açın (deneme sürümüyle de başlayabilirsiniz).
2. Shopify Admin → **Ayarlar → Uygulamalar ve satış kanalları → Uygulama Geliştir → Uygulama oluştur**. Açılan uygulamada **Storefront API** yetkilerini açın ve uygulamayı yükleyin (Install). Size bir **Storefront API erişim belirteci (access token)** verecek.
3. Aynı ekrandaki webhook imzalama sırrını (secret) not alın.
4. Bu 3 bilgiyi `backend/.env` dosyasında ilgili yerlere yapıştırın: `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_STOREFRONT_ACCESS_TOKEN`, `SHOPIFY_WEBHOOK_SECRET`.
5. Mossyna'daki her ürünü Shopify tarafındaki karşılığına eşlemeniz gerekiyor: Shopify'da ürünü oluşturup varyant ID'sini kopyalayın, Mossyna admin panelinde (Ürünler → ilgili ürünü düzenle) **Shopify Variant ID** alanına yapıştırın. Bu alan boş kalan bir ürün, sepete eklenip ödemeye geçildiğinde açıklayıcı bir hata verir — yani sessizce yanlış çalışmaz, hemen fark edersiniz.

Production'da (gerçek domain'inizde) bu adımların tam sürümü ve webhook'un Shopify'a nasıl kaydedileceği `DEPLOY.md` içinde adım adım var.

### 2) Google — tek tık giriş

1. [console.cloud.google.com](https://console.cloud.google.com) → **APIs & Services → Credentials → Create Credentials → OAuth Client ID** → Uygulama türü olarak **Web application** seçin.
2. **Authorized JavaScript origins** kısmına hem `https://mossyna.com.tr` hem de test ettiğiniz adresi (ör. `http://localhost:5500`) ekleyin.
3. Oluşturduğunuzda size yalnızca bir **Client ID** verilecek (bir de Client Secret gösterilir ama **buna hiç ihtiyacımız yok**, kullanmayacağız).
4. Bu Client ID'yi İKİ yere de aynen yapıştırın: `frontend/js/auth-google.js` içindeki `MOSSYNA_GOOGLE_CLIENT_ID` ve `backend/.env` içindeki `GOOGLE_OAUTH_CLIENT_ID`. İkisi birbirinden farklı olursa giriş çalışmaz — birebir aynı değeri kullandığınızdan emin olun.

Bu iki bağlantıyı eklemeden önce site tamamen çalışır durumda kalır; sadece o iki buton "henüz hazır değil" mesajı gösterir. Yani istediğiniz zaman, acele etmeden ekleyebilirsiniz.

---

## Sorun Giderme

- **"Sunucuya bağlanılamadı" hatası (frontend/admin'de):** Backend'in (`uvicorn app.main:app --reload --port 8000`) ayrı bir terminalde çalışır durumda olduğundan emin olun.
- **"psycopg2" veya "pg_config" hatası alıyorum:** PostgreSQL'in geliştirici araçları eksik olabilir. Mac'te `brew install postgresql`, Ubuntu'da `sudo apt install libpq-dev` çalıştırıp `pip install -r requirements.txt` komutunu tekrar deneyin.
- **"Address already in use" hatası:** 5500 veya 8000 portu başka bir uygulama tarafından kullanılıyor olabilir; komuttaki port numarasını (ör. `5501`, `8001`) değiştirip tekrar deneyin — 8000 dışında bir port kullanırsanız yukarıdaki `MOSSYNA_API_BASE_URL` notuna bakın.
- **CORS hatası (tarayıcı konsolunda "blocked by CORS policy"):** Frontend'i 5500 dışında bir portta açtıysanız, backend'in `.env` dosyasındaki `CORS_ORIGINS` değerini o adrese göre güncelleyip backend'i yeniden başlatın.
- **Admin panelinde giriş yapamıyorum:** `python -m app.scripts.seed` komutunu çalıştırdığınızdan ve backend'in ayakta olduğundan emin olun; hesap artık backend'deki `admin_users` tablosunda tutuluyor (tarayıcı localStorage'ında değil).

---

## Sırada ne var?

İsterseniz bir sonraki adımda ekleyebileceklerim:

1. Alembic migration dosyaları (şu an tablo oluşturma `Base.metadata.create_all` ile yapılıyor),
2. Docker Compose kurulumu (tek komutla PostgreSQL + backend + frontend),
3. Gerçek e-posta bildirimleri (sipariş onayı, mesaj yanıtı) için bir servis entegrasyonu,
4. Misafir sipariş adreslerinin kalıcı kaydı için küçük bir şema güncellemesi.

Hangisiyle devam etmek istediğinizi söylemeniz yeterli.
