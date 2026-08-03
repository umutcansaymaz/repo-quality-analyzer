# repo-quality-analyzer

**[English](README.md) | [Türkçe](README.tr.md)**

Gizlilik öncelikli, yerel çalışan bir depo kalite analizörü. Bir depoyu
klonlayın (veya yerel bir klasörü taratın) ve 14 statik-analiz boyutunda
sağlık puanınızı alın — tamamı tarayıcınızda, kendi API anahtarınızla
(kendin-getir) LLM açıklamaları dahil.

| | |
|---|---|
| Analiz | **tarayıcınızda** — kodunuz makinenizden asla çıkmaz |
| Motor | deterministik, kara kutu denetimli — 417 sentetik depoda **0 yanlış pozitif / 0 yanlış negatif** |
| Diller | TypeScript · Python · Go · Ruby · Java (3 dil ailesi) |
| Bulgular | 14 kategori, tüm şiddet seviyeleri, ikinci-geçiş doğrulamalı satır bazlı kanıtlar |
| Yapay zekâ açıklamaları | isteğe bağlı, kendi anahtarını getir (OpenAI, Anthropic, Gemini, Azure, OpenRouter, Ollama) |
| Kurulum | `npm run dev`, Docker veya kendi sunucunda |

---

## Neden bu araç?

**1. Gizlilik varsayılandır, bir özellik bayrağı değil.**

Dosya içerikleri **tarayıcıda** taranır. Yerel klasör analizinde sunucu
yalnızca özet raporu alır — kaynak kodunuzu asla. GitHub URL analizinde
depo sunucuda sığ (shallow) klonlanır ve aynı motorla taranır. Her iki
durumda da kodunuz hiçbir yerde saklanmaz, günlüğe yazılmaz veya paylaşılmaz.

**2. Motor "iddia" değil, kanıttır.**

Her algılayıcı bir kara kutu denetçisiyle gelir: proje, *bilinen* doğruluk
verisine sahip 417 mini depo üretir, bunlara karşı **gerçek** motoru
çalıştırır ve bir yanlış pozitif ya da yanlış negatif çıkarsa derlemeyi
durdurur. Ayrıntılar ve güncel sayılar için bkz. [Denetim](#denetim).

**3. Kendi anahtarını getir — hesap yok, fatura yok.**

Yapay zekâ açıklamaları isteğe bağlı bir katmandır. Arayüzden kendi
sağlayıcı anahtarınızı yapılandırın (tarayıcınızın localStorage'ında
saklanır) ve tek tıkla açıklama üretin. Anahtar **sunucuya asla
gönderilmez**; çağrı tarayıcınızdan doğrudan sağlayıcıya gider.

**4. Çok dilli, tutarlı kurallar.**

TypeScript, Python, Go, Ruby ve Java aynı eşikleri ve aynı şiddet
kalibrasyonunu paylaşır — 50 satırlık bir fonksiyon Python'da ne ise Go'da
da odur. Dile özgü sözdizimi (girinti tabanlı bloklar, `end` blokları,
süslü parantez sayımı) dil ailesine göre ayrı ele alınır.

---

## Özellikler

| Boyut | Neyi algılar |
|---|---|
| Güvenlik | sabit kodlanmış sırlar (API anahtarları, AWS, GitHub token'ları, Firebase, JWT), komut enjeksiyonu, zayıf kripto (MD5/SHA-1/DES) |
| Mimari | tanrı sınıflar (>20 metot), sıkı bağlılık (>15 içe aktarma), döngüsel bağımlılıklar (2 seviye) |
| Kalite | uzun fonksiyonlar (>50 satır), derin iç içe yapı (≥6 seviye), yüksek karmaşıklık (≥25 dal), boş hata yakalayıcılar, sihirli sayılar |
| Metrikler | büyük dosyalar (>600 satır), TODO borcu |
| Test | eksik test dosyaları (5'ten çok dosyalı ve testsiz depolar) |
| Dokümantasyon | dokümantasyon varlığı |
| Raporlar | sağlık puanı (A–F), kök nedenler, satır bazlı kanıtlar, bilgi grafiği, yol haritası, açıklamalar (LLM veya deterministik) |

Her bulgu şunları taşır:

- `file_path` + `line` + `evidence_snippet` (gerçek kaynak satırı)
- `severity` (`critical` → `low`), kategoriye göre kalibreli ve denetimli
- `confidence` (algılayıcıya özgü, sezgisel bulgularda dürüst)
- `validation_status`: **verified / partial / unverified** — aynı kod
  üzerinde ikinci, bağımsız bir geçişle üretilir
- dosya+kategori bazında özelleştirme (çift başına en fazla 5) — bir
  dosyadaki üç enjeksiyon üç bulgudur, bir değil

---

## Mimari

```
tarayıcı (page.tsx)
 ├─ analyzeLocalFiles()  → dosyaları tarar, kanıt üretir   [local-analysis.ts]
 ├─ buildLocalReport()   → puan + kök nedenler + grafik    [local-analysis.ts]
 ├─ explainWithLLM()     → isteğe bağlı BYOK LLM çağrısı   [llm.ts]
 └─ POST /api/analyze-local (yalnızca rapor — dosya içeriği değil)
sunucu
 ├─ /api/analyze         → depoyu klonlar (URL) + aynı motor + SSRF doğrulaması
 ├─ /api/result/:id      → saklanan raporu getirir
 ├─ /api/benchmark       → canlı motor öz-testi (gerçek 417 depoluk denetimi çalıştırır)
 └─ db/analysis-results/ → saklanan JSON raporlar
```

### Motor (`src/lib/local-analysis.ts`)

**Regex tarayıcılar** ile **yapısal tarayıcıların** deterministik bir melezi:

- **Dil aileleri** — `brace` (TS/JS/Java/C#/Go/Rust/Kotlin/C/C++/PHP),
  `python` (girinti tabanlı bloklar), `ruby` (`def...end` blokları). Blok
  tespiti, iç içe derinlik ve dal sayımı aileye duyarlıdır.
- **Maskeleme katmanı** — desen eşleşmesinden önce yorumlar, dizeler,
  şablon literalleri, üçlü tırnaklı docstring'ler ve regex literal'leri
  maskelenir; böylece `// const key = "sk-..."` bir bulgu değildir. Bölme
  işlemi (`x / 2`) regex literal'le karıştırılmaz; regex içindeki karakter
  sınıfları doğru işlenir.
- **İçe aktarma çözümlemesi** — göreli yollar, `@/` takma adları, Python
  `from x import`, Go `import "pkg"`, Ruby `require_relative`, Java paket
  yolları; kendine aktarma döngü değildir; yorum içindeki aktarmalar
  yok sayılır.
- **İkinci-geçiş doğrulama** — her bulgu bağımsız bir yöntemle yeniden
  kontrol edilir (yeniden tespit, entropi kontrolü, yeniden sayım). Sonuç,
  arayüzün dürüstçe gösterdiği `validation_status`'tür.
- **Çoklu bulgu** — yalnızca ilk bulgu değil, tüm bulgular toplanır:
  `capEvidenceByPriority` dosya+kategori başına en fazla 5 tutar ve nihai
  şiddet sıralı kesimi uygular.

### Puanlama

`computeHealthScore`, 8 boyutlu, oran tabanlı, ölçekten bağımsız bir puan
üretir:

| Boyut | Ağırlık |
|---|---|
| Güvenlik | %15 |
| Mimari | %20 |
| Kalite | %25 |
| Test | %15 |
| Dokümantasyon | %10 |
| Performans | %5 |
| Geliştirici Deneyimi | %5 |
| Ölçeklenebilirlik | %5 |

Kritik bir sabit sır −15 ceza uygular. Notlar: **A ≥ 85, B ≥ 70, C ≥ 55,
D ≥ 40, F < 40**. Puan oran tabanlı olduğu için 5 dosyalık bir depo ile
5.000 dosyalık bir depo aynı cetvelle ölçülür.

---

## Denetim — motor nasıl dürüst tutuluyor

Proje, kendi **kara kutu denetçisiyle** gelir (`npm run audit`):

1. `audit/generator.mjs` — *bilinen* doğruluk verisine sahip yüzlerce mini
   depo üretir: temiz varyantlar, tek/çift/çoklu sorunlar, zararsız
   benzer tuzaklar (yorum, dize, regex literal, test dosyası, üretilmiş/
   şifreli/yedek dosyalar), sınır eşikleri (her eşiğin tam altı ve üstü),
   5 dilde.
2. **Gerçek** motor (arayüzün kullandığı kod yolunun aynısı —
   `src/lib/cli.ts`) her depoya karşı çalışır.
3. `audit/compare.mjs` yanlış pozitif/negatif hesaplar; koşucu ayrıca her
   kategorinin **şiddet kalibrasyonunu** doğrular.
4. Motorun bilinçli olarak yakalayamadığı desenler (birleştirilmiş sırlar,
   base64 blokları, dinamik kripto) **bilinen sınırlar** olarak izlenir —
   ayrı raporlanır, geçer/kalır sayılarının içine gizlenmez.

Güncel sonuç:

```
DENETİM — 417 depo | 539 beklenen bulgu
  YANLIŞ POZİTİF: 0 | YANLIŞ NEGATİF: 0 | Hassasiyet %100 | Duyarlılık %100
  ŞİDDET UYUMSUZLUĞU: 0 (14 kategorinin tümü beklenen şiddeti üretiyor)
  BİLİNEN SINIRLAR: 11 (kasıtlı FN'ler, ayrıca izlenir)
```

Kapsanan kategoriler: `hardcoded_secret`, `command_injection`,
`weak_crypto`, `empty_handler`, `long_function`, `deep_nesting`,
`high_complexity`, `large_file`, `god_class`, `tight_coupling`,
`circular_dependency`, `magic_number`, `todo_debt`, `missing_tests` — TS /
Python / Go / Ruby / Java dillerinde.

Arayüzdeki **Motor Kendini Test** sekmesi bu denetimin aynısını canlı
çalıştırır (`/api/benchmark` — 417 depo, ~1 saniye) ve sayıları yalnızca
README'de değil, ürünün içinde gösterir.

Denetim bir regresyon kalkanıdır: **herhangi** bir motor değişikliği
`YANLIŞ POZİTİF: 0 | YANLIŞ NEGATİF: 0 | ŞİDDET UYUMSUZLUĞU: 0` tutmalıdır.
Bkz. [CONTRIBUTING.md](CONTRIBUTING.md).

### Gerçek dünya altın testleri

`tests/golden-real.test.ts`, motorun davranışını gerçek depolara karşı
kilitler (TUSLA ve bu projenin kendisi) — puan aralığı, sır sayısı ve FP'siz
garantiler. Bir motor değişikliği gerçek dünya puanını kilitli aralığın
dışına çıkarırsa test başarısız olur.

---

## LLM açıklamaları (kendi anahtarını getir)

- Sağlayıcılar: **OpenAI, Anthropic, Google Gemini, Azure OpenAI,
  OpenRouter, Ollama (yerel)**.
- Akış: analiz çalıştırın → LLM durum kartındaki **"LLM açıklamaları
  üret"** düğmesine tıklayın → çağrı tarayıcınızdan doğrudan sağlayıcıya
  gider.
- Prompt kompakt ve kanıta dayalıdır: en önemli 10 kök neden + en kritik 3
  doğrulanmış kanıt parçacığı. Modelden istenen, **doğrulanmış bulguları
  açıklamasıdır — yeni şeyler uydurması değil**.
- Çıktı JSON olarak ayrıştırılır (`{sections:[{title, body, confidence}]}`)
  ve düz metin yedeği vardır — bozuk bir yanıt raporu asla bozmaz.
- Hatalar anlaşılır mesajlara çevrilir (kota, geçersiz anahtar, zaman
  aşımı); analizin kendisi LLM olmadan da tamamen deterministik ve
  kullanılabilirdir.

**Dürüst not:** LLM ile üretilen açıklamalar henüz kalıcı değildir — yalnızca
oturum durumunda yaşarlar. Bunlar bir zenginleştirme katmanıdır;
deterministik açıklamalar temel seviyedir.

---

## Başlangıç

### 1. Çalıştırın

> Gereksinim: **Node.js 20+** ve npm (veya bun).

```bash
npm ci
npm run dev               # http://localhost:3000
```

Ortam yapılandırması gerekmez — `.env.example` güvenli bir varsayılan
olarak sunulur ve hiçbir sır içermez. Raporlar `db/analysis-results/`
klasörüne otomatik kaydedilir.

Üretim (standalone sunucu):

```bash
npm run build
npm start                 # http://localhost:3000
```

Docker ile:

```bash
docker compose up --build   # http://localhost:3000
```

### 2. Analiz edin

- **Yerel klasör**: sürükleyip bırakın veya klasör seçin — tarayıcınızda
  analiz edilir.
- **GitHub deposu**: bir URL yapıştırın — sunucuda sığ klonlanır (SSRF
  doğrulamalı) ve aynı motorla taranır.

### 3. (İsteğe bağlı) Yapay zekâ açıklamaları

Arayüzdeki ayarlardan bir sağlayıcı seçin ve anahtarınızı yapıştırın.
Analizden sonra LLM durum kartındaki **"LLM açıklamaları üret"** düğmesine
tıklayın.

---

## Güvenlik modeli

- **Yükleme yok**: yerel klasör kodunuz sunucuya asla ulaşmaz.
- **Sunucuda anahtar saklanmaz**: LLM anahtarları tarayıcınızda yaşar.
- **SSRF koruması**: `/api/analyze` yalnızca genel http/https URL kabul
  eder; `localhost`, özel IP aralıkları (10.x, 172.16–31.x, 192.168.x,
  169.254.x), IPv6 loopback/link-local/ULA ve DNS-rebinding hedefleri
  reddedilir (`validateRepositoryUrl`).
- **Kapsamlı klonlama**: klonlar `validation_workspace/` altında, salt-okunur
  yeniden kullanımla; hiçbir git yazma işlemi yapılmaz.
- **Derleme hilesi yok**: `ignoreBuildErrors` kapalıdır — TypeScript hataları
  CI'da da yerelde de derlemeyi durdurur.

Bkz. [SECURITY.md](SECURITY.md).

---

## Bilinen sınırlar

Motor, algılayamadığı şeyler konusunda bilinçli olarak şeffaftır. Bunlar
denetimde **bilinen sınırlar** olarak izlenir ve `npm run audit` çıktısında
raporlanır:

- **Birleştirilmiş sırlar**: `"sk-" + "abc..."` (regex tek parça bulur)
- **Base64 ile kodlanmış sırlar**
- **Dinamik kripto algoritmaları**: `createHash(process.env.ALGO)`
- **Taint/akış analizi yok**: `const cmd = "ls"; exec(cmd)` — `cmd` sabit
  olsa bile raporlanır (yanlışlıkla gözden kaçırmak yerine işaretlemeyi
  tercih ederiz)
- **3+ seviye içe aktarma döngüleri** (A→B→C→A) algılanmaz — yalnızca 2
  seviye
- **Kopya kod / ölü kod / CVE veritabanı analizi yok**
- **`.env` dosyalarındaki sırlar** taranmaz (env dosyaları tasarım gereği
  hariç tutulur — zaten commit edilmemelidir)
- **Stripe tarzı token'lar** (`sk_live_...`) sır regex'inde yoktur (yalnızca
  tire ayraçlı `sk-`)
- **AST/ayrıştırıcı yok** — motor regex + yapısal taramadır; *niyeti*
  anlayamaz (ör. bir değerin gerçekten kullanıcı girdisi olup olmadığını)

Bunlar dürüst sınırlardır, gizli kusurlar değil: her biri hassasiyet, hız ve
basitlik arasında bilinçli bir takastır ve her biri kullanıcının görebileceği
bir yerde belgelenmiştir.

---

## Geliştirme

```bash
npm run test        # 164 birim + entegrasyon + altın testler
npm run lint
npm run audit       # motor kara kutu denetimi (0/0/0 kalmalı)
npm run build       # TypeScript hataları derlemeyi durdurur
```

- Motor değişiklikleri denetimi yeşil tutmalıdır (`0 FP / 0 FN / 0 şiddet
  uyumsuzluğu`). Yeni algılayıcılar denetim varyantlarıyla gelmelidir:
  temiz, tek, çift, komşu, çoklu, gürültü + sınır eşikleri + zararsız
  tuzaklar.
- Altın testler gerçek dünya davranışını kilitler (bkz.
  [CONTRIBUTING.md](CONTRIBUTING.md)).
- CI hattı (GitHub Actions) her gönderimde lint, test, denetim, üretim
  derlemesi ve Docker imaj derlemesi çalıştırır.

---

## SSS

**Kodum bir yere yükleniyor mu?** Hayır. Yerel klasör analizi tamamen
tarayıcınızda gerçekleşir. Yalnızca kompakt rapor (dosya içeriği olmadan)
saklanır.

**"0 yanlış pozitif" iddiası gerçek mi?** İddia değil, ölçümdür: denetim
paketi bilinen doğruluk verisiyle üretilir ve her CI koşusunda gerçek
motora karşı çalıştırılır. Yine de dürüst olalım: denetim *sentetiktir* —
gerçek dünya kodu daha dağınıktır ve altın testler (gerçek depolar) ikinci
savunma hattıdır. README her ikisini de dürüstçe anlatır.

**Aracı kullanmak için LLM anahtarı gerekli mi?** Hayır. Yapay zekâ
açıklamaları dışında her şey anahtarsız çalışır ve açıklamalar varsayılan
olarak deterministiktir.

**Neden SonarQube / Semgrep / ESLint değil?** Bunlar mükemmel ve daha derin
araçlardır. Bu proje, onların genellikle sunmadığı üç şeye odaklanır:
gizlilik öncelikli tarayıcı analizi, denetimle kanıtlanmış FP/FN'siz kural
seti ve 5 dilde sıfır yapılandırmayla tek ve tutarlı bir puan.

---

## Lisans

MIT — bkz. [LICENSE](LICENSE).
