# repo-quality-analyzer

**[English](README.md) | [Türkçe](README.tr.md)**

Gizlilik öncelikli, yerel çalışan bir depo kalite analizörü. Bir depoyu
klonlayın (veya yerel bir klasörü taratın) ve 14 statik-analiz boyutunda
sağlık puanınızı alın — tamamı tarayıcınızda, kendi API anahtarınızla
(kendin-getir) LLM açıklamaları dahil.

## Neden bu araç?

- **Gizlilik öncelikli**: dosya içerikleri **tarayıcınızda** analiz edilir —
  kodunuz makinenizden asla çıkmaz. Sunucu yalnızca özet raporu saklar.
- **Kanıtlanmış motor**: her algılayıcı, bilinen doğruluk verisiyle 417
  sentetik depoya karşı kara kutu denetiminden geçer — **0 yanlış pozitif,
  0 yanlış negatif** (bkz. [Denetim](#denetim)).
- **Kendi anahtarını getir**: yapay zekâ açıklamaları isterseniz arayüzden
  kendi OpenAI/Anthropic anahtarınızı ekleyin. Anahtar tarayıcınızın
  localStorage'ında saklanır ve **sunucuya asla gönderilmez**.
- **Çok dilli**: TypeScript, Python, Go, Ruby, Java — aynı eşikler, aynı
  kurallar.

## Özellikler

| Boyut | Neyi algılar |
|---|---|
| Güvenlik | sabit kodlanmış sırlar (API anahtarları, AWS, GitHub token'ları, Firebase), komut enjeksiyonu, zayıf kripto (MD5/SHA-1/DES) |
| Mimari | tanrı sınıflar, sıkı bağlılık, döngüsel bağımlılıklar (2 seviye) |
| Kalite | uzun fonksiyonlar, derin iç içe yapılar, yüksek karmaşıklık, boş hata yakalayıcılar, sihirli sayılar |
| Metrikler | büyük dosyalar, TODO borcu |
| Test | eksik test dosyaları |
| Dokümantasyon | dokümantasyon varlığı |
| Raporlar | sağlık puanı (A–F), kök nedenler, satır numaralı kanıtlar, bilgi grafiği, yol haritası, açıklamalar (LLM veya deterministik) |

## Başlangıç

### 1. Çalıştırın

```bash
npm install
cp .env.example .env      # isteğe bağlı — yalnızca SQLite deposu için DATABASE_URL
npm run dev               # http://localhost:3000
```

### 2. Analiz edin

- **Yerel klasör**: sürükleyip bırakın veya klasör seçin — tarayıcınızda
  analiz edilir.
- **GitHub deposu**: bir URL yapıştırın — sunucuda sığ (shallow) klonlanır
  ve aynı motorla taranır.

### 3. (İsteğe bağlı) Yapay zekâ açıklamaları

Arayüzdeki ayarlardan bir sağlayıcı seçin (OpenAI, Anthropic, Azure OpenAI,
Ollama, Gemini, OpenRouter) ve anahtarınızı yapıştırın. Analizden sonra LLM
durum kartındaki **"LLM açıklamaları üret"** düğmesine tıklayın — çağrı
tarayıcınızdan doğrudan sağlayıcıya gider; anahtar **sunucuya asla
gönderilmez**.

## Mimari

```
tarayıcı (page.tsx)
 ├─ analyzeLocalFiles()  → dosyaları tarar, kanıt üretir  [local-analysis.ts]
 ├─ buildLocalReport()   → puan + kök nedenler + grafik   [local-analysis.ts]
 └─ POST /api/analyze-local (yalnızca rapor — dosya içeriği değil)
sunucu
 ├─ /api/analyze         → depoyu klonlar (URL) + aynı motor + SSRF doğrulaması
 ├─ /api/result/:id      → saklanan raporu getirir
 └─ db/analysis-results/ → saklanan JSON raporlar (SQLite Prisma ile isteğe bağlı)
```

Motor (`src/lib/local-analysis.ts`) deterministik, regex + yapısal tarayıcı
melezidir: her bulgu `dosya`, `satır`, kanıt parçacığı, güven puanı ve ikinci
geçiş doğrulama durumu (`verified`/`partial`/`unverified`) taşır.

## Bilinen sınırlar

Motor, algılayamadığı şeyler konusunda bilinçli olarak şeffaftır — bunlar
denetimde **bilinen sınırlar** olarak izlenir ve `npm run audit` çıktısında
raporlanır:

- **Birleştirilmiş sırlar**: `"sk-" + "abc..."` (regex tek parça bulur)
- **Base64 ile kodlanmış sırlar**
- **Dinamik kripto algoritmaları**: `createHash(process.env.ALGO)`
- Taint/akış analizi yok: `const cmd = "ls"; exec(cmd)` — `cmd` sabit olsa
  bile raporlanır
- 3+ seviye içe aktarma döngüleri (A→B→C→A) algılanmaz — yalnızca 2 seviye
- Kopya kod / ölü kod / CVE veritabanı analizi yok

## Denetim

Motor, kara kutu denetçisiyle birlikte gelir: bilinen doğruluk verisine sahip
yüzlerce mini depo üretir, bunlara karşı **gerçek** motoru çalıştırır ve
yanlış pozitifleri / yanlış negatifleri / şiddet kalibrasyonunu raporlar.

```bash
npm run audit
```

Güncel sonuç:

```
DENETİM — 417 depo | 539 beklenen bulgu
  YANLIŞ POZİTİF: 0 | YANLIŞ NEGATİF: 0 | Hassasiyet %100 | Duyarlılık %100
  ŞİDDET UYUMSUZLUĞU: 0 (14 kategorinin tümü beklenen şiddeti üretiyor)
  BİLİNEN SINIRLAR: 11 (kasıtlı FN'ler, ayrıca izlenir)
```

Kapsanan kategoriler: hardcoded_secret, command_injection, weak_crypto,
empty_handler, long_function, deep_nesting, high_complexity, large_file,
god_class, tight_coupling, circular_dependency, magic_number, todo_debt,
missing_tests — TS / Python / Go / Ruby / Java dillerinde, sınır eşikleri
(her eşiğin tam altı/üstü) ve zararsız benzer tuzaklar dahil.

## Geliştirme

```bash
npm run test        # 164 birim + entegrasyon + altın testler
npm run lint
npm run audit       # motor kara kutu denetimi (yukarıda)
npm run build
```

## Lisans

MIT — bkz. [LICENSE](LICENSE).
