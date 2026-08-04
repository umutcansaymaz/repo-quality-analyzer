# GOAL
Plan: Faz 0- Determinizm, Faz A- Taint derinliği, Faz B- Gerçek dünya genişletme, Faz C- Kombinasyon audit, Faz D- Performans + cap tutarlılığı — en mümkün en tutarlı analiz motoru

## STATUS
active

## DONE_WHEN
- Faz 0: 2× analiz determinizm testi (evidence diff = 0, id hariç); rand()/Math.random()/Date.now() taraması temiz; cap sıralama determinizmi doğrulu
- Faz A: yeniden atama takibi, değişken zinciri (döngü korumalı), taint kaynakları (req.query/argv/input/environ); audit +8 varyant 0/0/0
- Faz B: Python + Ruby gerçek repo golden'ları (fixtures); kalibrasyon 6 repo (TS/JS, Go, Java, Python, Ruby, kendi kodu)
- Faz C: çoklu-kategori kombinasyonları, iç içe fonksiyon + eşik çiftleri, agresif maskeleme tuzakları — audit 0/0/0
- Faz D: büyük repo süresi ölçümü + MAX_EVIDENCE cap kesim davranışı testi
- Nihai: audit 0/0/0, tüm testler, build, lint, mevcut golden'lar korundu, commit itildi

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
- [ ] Faz 0: Determinizm testi + rastgelelik taraması
- [ ] Faz A: Taint derinliği (yeniden atama/zincir/kaynak) + audit +8
- [ ] Faz B: Python + Ruby golden'ları (6 repo kalibrasyon)
- [ ] Faz C: Kombinasyon audit
- [ ] Faz D: Performans + cap testi
- [ ] Nihai doğrulama + commit + push

## PROGRESS
(başlangıç)

## RUNS
- started: 2026-08-04T19:18:25.600Z
