# AGENTS.md — kalite (repo-quality-analyzer)

> **Kural**: Her task başlangıcında bu dosya okunur. Değişiklik yapmadan önce ilgili guardrail'ler uygulanır.
> Dil: Türkçe — commit mesajları dahil her şey Türkçe yazılır.

## Hızlı İndeks

| ID | Kategori | Kural |
|----|----------|-------|
| GR-Q01 | Kalite | Analiz motoru deterministik kalmalı — LLM yalnızca açıklama üretir, skor üretmez |
| GR-Q02 | Kalite | Sıfır yanlış pozitif/negatif vaadi — motor değişince audit/ altındaki 417 sentetik repo testi koşulur |
| GR-Q03 | TypeScript | `any` yasak; strict mode; tip daraltma (narrowing) zorunlu |
| GR-Q04 | Next.js | Server Component / Client Component ayrımına dikkat; `"use client"` bilinçli konur |
| GR-Q05 | Gizlilik | Kod asla sunucuya gönderilmez — analiz tarayıcıda biter (privacy-first) |
| GR-Q06 | Test | Yeni analiz kuralı = önce vitest testi (kırmızı→yeşil) |
| GR-Q07 | Spagetti | Fonksiyon max 80 satır, nested max 2, DRY |
| GR-Q08 | Temizlik | console.log/TODO/ölü kod yasak; magic number → sabit |

## Komutlar

```bash
npm run dev        # next dev -p 3000
npm run build      # next build (standalone çıktı)
npm run lint       # eslint .
npm test           # vitest run
npm run audit      # node audit/run.mjs — motor kalite kapısı (417 repo)
```

## Kurallar

### GR-Q01 — Motor deterministik
- Skorlar ve bulgular **yalnızca** statik analizden (kod ağacı, regex, pattern eşleştirme) üretilir.
- LLM açıklaması (bring-your-own-key) son adımdır; skoru asla değiştiremez.
- Rastgelelik/geçici deneysellik üretim yoluna giremez — `spike/` klasörü test eder.

### GR-Q02 — Kalite kapısı
- `audit/` altındaki sentetik repo seti (417 repo) motorun doğruluk garantisidir.
- Analiz kuralı değiştiğinde `npm run audit` **zorunlu** — 0 FP / 0 FN bozulursa değişiklik kabul edilmez.

### GR-Q05 — Gizlilik (mimari sınır)
- Analiz tamamen tarayıcıda çalışır. Kullanıcı kodunu dışarı gönderen bir değişiklik **kritik ihlal**dir — yapılmaz, önerilmez.

### GR-Q06 — TDD
- Her yeni kural/tespit için önce `vitest` testi yaz, kırmızı gör, sonra uygula, yeşil gör.

### GR-Q07 — Spagetti önleme
- Fonksiyon ≤ 80 satır, iç içe blok ≤ 2 seviye, aynı mantık 2+ yerde → helper'a çıkar.

## Task Tamamlama

- [ ] `npm run lint` temiz
- [ ] `npm test` yeşil
- [ ] Motor değiştiyse `npm run audit` → 0 FP / 0 FN
- [ ] `npm run build` başarılı
