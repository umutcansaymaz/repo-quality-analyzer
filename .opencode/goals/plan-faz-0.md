# GOAL
Plan: Faz 0- Determinizm, Faz A- Taint derinliği, Faz B- Gerçek dünya genişletme, Faz C- Kombinasyon audit, Faz D- Performans + cap tutarlılığı — en mümkün en tutarlı analiz motoru

## STATUS
done

## DONE_WHEN
- Faz 0: 2× analiz determinizm testi (evidence diff = 0, id hariç) ✓; rastgelelik taraması (yalnızca jobId/analiz zamanı — bilinçli) ✓; cap sıralama determinizmi ✓
- Faz A: yeniden atama takibi ✓, değişken zinciri (döngü korumalı) ✓, taint kaynakları ✓; audit +8 varyant 0/0/0 ✓
- Faz B: Python (click 64.0) + Ruby (httparty 64.5) golden'ları ✓; 6 repo kalibrasyon ✓
- Faz C: çoklu-kategori ✓, iç içe fonksiyon ✓, agresif tuzaklar ✓ — audit 0/0/0 ✓
- Faz D: TUSLA 3.8 sn, audit 449 repo 3 sn ✓; MAX_EVIDENCE cap testleri ✓
- Nihai: audit 0/0/0, 180 test, build, lint, golden'lar korundu, commit itildi ✓

## CONSTRAINTS
- Yalnızca kalite repo'su değişir (motor, audit, tests, fixtures, README)
- Mevcut davranışlar bozulmamalı: audit 0/0/0 + golden'lar korunmalı
- Taint: regex tabanlı basit çözümler — parser/AST eklenmez (bilinçli sınır)
- Determinizm kuralı: motor çıktısında rastgelelik olmamalı (id dışında)

## PLAN
Faz 0: determinizm testi + rastgelelik taraması + cap sıralama doğrulaması
Faz A: taint derinliği (yeniden atama, zincir, kaynak) + audit varyantları
Faz B: Python/Ruby gerçek repo golden'ları + 6 repolu kalibrasyon
Faz C: kombinasyon senaryoları + iç içe fonksiyon + agresif tuzaklar
Faz D: performans ölçümü + cap kesim testi
Nihai doğrulama + commit + push

## NEXT
(tamamlandı)

## PROGRESS
DONE 2026-08-04 — Faz 0: determinizm 3/3 (rawEvidence + cap sıra + dosya listesi birebir); motor rastgeleliği yalnızca jobId/analiz zamanı (bilinçli)
DONE 2026-08-04 — Faz A: zincir (a=b; b="x"), yeniden atama (son atama), kaynaklar (req.query/environ) + literal zincir; +8 audit varyantı — 441 repo 0/0/0
DONE 2026-08-04 — Faz B: py-sample (pallets/click, 64.0) + rb-sample (httparty, 64.5) — 6 repolu kalibrasyon; click'te 14 gerçek circular import elle doğrulandı (exceptions↔core↔utils zinciri)
DONE 2026-08-04 — Faz C: combo +8 senaryo; GERÇEK FP: secret tarayıcı docstring masklemiyordu — triple-quote her zaman maskelenir; 449 repo 0/0/0
DONE 2026-08-04 — Faz D: TUSLA 2225 dosya 3.8 sn; audit 449 repo 3 sn; cap kesim 2/2 (300 cap, high korunur)
DONE 2026-08-04 — Temizlik: audit/ ve fixtures kalite analizinden dışlandı (test verisi) — kalite 71.3→75.4; golden güncellendi
DONE 2026-08-04 — Nihai: 180 test, audit 449 0/0/0, build/lint OK, golden 7/7, TUSLA 62.6 — commit 7054db9 itildi

## RUNS
- started: 2026-08-04T19:18:25.600Z
