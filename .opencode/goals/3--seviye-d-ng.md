# GOAL
3+ seviye döngü + Stripe sk_live_ + f-string FN'leri kapatmak — bilinen sınır listesini daraltma (~45 dk)

## STATUS
done

## DONE_WHEN
- Motor: hasCircularImport 3+ seviye döngüleri (A→B→C→A) yakalıyor ✓
- Motor: secretRegex sk_live_ / pk_live_ token'larını yakalıyor (sk_live_ critical, pk_live_ medium) ✓
- Motor: Python f-string interpolasyonu (os.system(f"ls {user}")) enjeksiyon sayıyor; f-string'siz sabit (f"ls -la") saymıyor ✓
- Audit: yeni varyantlar eklendi (circular-3level, secret-stripe, injection-fstring) — tümü 0 FP/0 FN ✓
- Bilinen sınır listesi 2 madde daraldı (README EN/TR) ✓
- Tam doğrulama: audit 0/0/0, 171 test, build, lint, golden (TUSLA/kalite) bozulmadı ✓

## CONSTRAINTS
- Yalnızca kalite repo'su motoru (src/lib/local-analysis.ts) + audit/generator.mjs + README değişir
- Mevcut 2-seviye döngü davranışı ve diğer tarayıcılar bozulmamalı (audit 0/0/0 korunmalı)
- Severity kalibrasyonu: sk_live_ critical (EXPECTED_SEVERITY ile uyumlu), pk_live_ medium (yalnızca unit test — audit'e girmez)

## PLAN
1. Motor: hasCircularImport → DFS tabanlı genel döngü tespiti (3+ seviye dahil)
2. Motor: secretRegex'e sk_live_/pk_live_ desenleri + severity ayrımı
3. Motor: isStaticCommandArg'e Python f-string interpolasyon kontrolü (f"..." prefix + { })
4. Audit: yeni varyantlar (circular-3level-{lang}, secret-stripe-{lang}, injection-fstring-py ± güvenli)
5. README EN/TR: bilinen sınırlardan 3 maddeyi kaldır
6. Tam doğrulama + commit

## NEXT
(tamamlandı)

## PROGRESS
DONE 2026-08-04 — hasCircularImport DFS: A→B→C→A yakalanıyor; kendine import (A→A) ve ayrık zincir (A→B→C) döngü değil — 3 unit test
DONE 2026-08-04 — secretRegex: sk_live_ critical + pk_live_ medium (isClientKey) — 2 unit test
DONE 2026-08-04 — isStaticCommandArg: f-prefix + {expr} kontrolü; f"ls {x}" riskli, f"ls -la" sabit — 2 unit test
DONE 2026-08-04 — Audit +12 senaryo (429 repo): 0 FP / 0 FN / severity 0
DONE 2026-08-04 — README EN/TR: bilinen sınırlardan "3+ seviye döngü" ve "Stripe tarzı tokenlar" çıkarıldı
DONE 2026-08-04 — Doğrulama: 171/171 test, audit 0/0/0, build/lint OK, golden 3/3, TUSLA 62.6 korundu — commit 12d2e1d itildi

## RUNS
- started: 2026-08-04T18:15:27.800Z
