# GOAL
Kademeli (Doğrusal) Kalite Puanı — "Her Refactor Görünür Olsun"

## STATUS
active

## DONE_WHEN
- codeQuality formülü: `92 − min(45, round(problemRatio × 150))`, ratio < 0.01 → 0 ceza ✓
- 6 gerçek-repo golden aralığı ölçülen yeni değerlere göre (±1.0) güncellendi, golden testleri yeşil ✓
- scoring.test.ts "kötü repo < 50" yeni formülle yeşil (gerekirse repo güçlendirilir) ✓
- fix-loop.test.ts: 3 kademeli monotonluk testi (33→23→12 problemli dosya → cq kademeli artar) ✓
- Audit 469 repo: 0 FP / 0 FN korundu ✓
- Tüm testler + build + lint yeşil ✓
- README.tr.md puanlama bölümü doğrusal modelle güncellendi ✓
- Hedeflerim simülasyon tablosu PROGRESS'te kanıt olarak var ✓
- Commit atıldı ve itildi ✓

## CONSTRAINTS
- Yalnızca kalite repo'su değişir (motor, testler, audit, README)
- Tavan −45 korunur (kötü-durum puanı stabil kalır); ratio<0.01 eşiği korunur
- 1000+ satırlık large_file ek cezası (−1.5, max −15) korunur
- Mevcut davranışlar bozulmamalı: audit 0/0/0, bulgu üretimi değişmez (yalnızca skor formülü)
- Golden değerleri keyfi değil ÖLÇÜMLE güncellenir (yeni_değer ± 1.0)

## PLAN
1. local-analysis.ts:770-777 formül değişimi (doğrusal ceza)
2. Golden yeniden kalibrasyon: 6 gerçek repo yeni formülle taranır, aralıklar ölçülen değere göre güncellenir
3. scoring.test.ts kötü-repo testi doğrulanır (gerekirse güçlendirilir)
4. fix-loop.test.ts 3 kademeli monotonluk testi eklenir
5. README.tr.md puanlama bölümü güncellenir
6. Tam doğrulama: tüm testler + audit 469 + build + lint
7. Hedeflerim simülasyonu (33/23/12 dosya) kanıt olarak hesaplanır
8. Commit + push

## NEXT
1. [in_progress] Formül değişimi: doğrusal ceza (eğim 150)
2. Golden yeniden kalibrasyon (6 gerçek repo ölçümü)
3. scoring.test.ts doğrulama/güçlendirme
4. fix-loop.test.ts monotonluk testi
5. README güncellemesi
6. Tam doğrulama (test + audit + build + lint)
7. Hedeflerim simülasyonu kanıtı
8. Commit + push + final rapor

## PROGRESS
DONE 2026-08-05 — Formül: codeQuality = 92 − (ratio<0.01 ? 0 : min(45, round(ratio×150))); tavan −45 ve 0.01 eşiği korundu; hugeFiles ek cezası korundu
DONE 2026-08-05 — Golden yeniden kalibrasyon (ölçümlü): TUSLA 62.6→67.1, kalite 75.4→80.2, py 64.0→68.8, rb 64.5→66.8; go 74.7 ve java 65.6 DEĞİŞMEDİ (tavan bölgesinde) — golden-real 7/7
DONE 2026-08-05 — scoring.test.ts yeni formülle 9/9 (kötü repo <50 korundu — diğer boyutlar düşük)
DONE 2026-08-05 — fix-loop.test.ts +1 monotonluk testi: 9/30→47, 6/30→62, 3/30→77, 0/30→92 (kademeli artış kanıtı)
DONE 2026-08-05 — README.tr.md puanlama bölümü: doğrusal model + örnek tablo
DONE 2026-08-05 — Tam doğrulama: 206 test, audit 469 repo 0/0/0, build OK, lint 0 hata
DONE 2026-08-05 — Hedeflerim simülasyonu (104 dosya): 33→76.1 (korunur), 30→76.6, 23→79.1, 15→81.9, 12→83.1, 6→85.1 (A) — her dosya düzeltmesi görünür

## RUNS
- started: 2026-08-05T07:22:02.348Z
