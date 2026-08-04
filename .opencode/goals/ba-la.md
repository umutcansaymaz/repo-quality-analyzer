# GOAL
başla.

## STATUS
done

## DONE_WHEN
- TUSLA analizi tam evidence envanteriyle alındı (skor, kategoriler, örnekler) ✓
- Her ana kategoriden örnek bulgular TUSLA kaynağında manuel doğrulandı (FP oranı raporlandı) ✓
- Motorun kaçırdığı gerçek sorunlar tespit edildi (FN listesi) ✓
- Skor boyutları (security/architecture/testing/documentation) gerçek kod durumuyla karşılaştırıldı ✓
- Nihai rapor: FP %, FN listesi, skor-tutarlılık, kalibrasyon önerileri ✓

## CONSTRAINTS
- TUSLA reposuna ASLA kod müdahalesi: ne sil, ne ekle, ne değiştir — yalnızca okuma
- Motor analiz sonuçları TUSLA dışına (temp) yazılır
- Kalibrasyon önerileri yalnızca kalite repo'sunun motoruna uygulanabilir (TUSLA'ya değil)

## PLAN
1. Motor çıktısı: CLI ile TUSLA analizi → evidence JSON (temp)
2. FP doğrulama: long_function/high_complexity/deep_nesting/empty_handler/large_file/god_class örneklerini TUSLA kaynağında açıp doğrula
3. FN taraması: parçalı secret, sabit credential, 3+ seviye döngü, .env, zayıf bağımlılıklar
4. Skor boyut kalibrasyonu: testing/documentation/security/architecture gerçek durumla karşılaştır
5. Nihai rapor + kalibrasyon önerileri

## NEXT
(tamamlandı)

## PROGRESS
DONE 2026-08-04 — Aşama 1: TUSLA 62.6 (C), 2225 dosya, 300 kanıt (high_complexity 51, large_file 14, god_class 1, long_function 157, deep_nesting 48, empty_handler 28, hardcoded_secret 1)
DONE 2026-08-04 — Aşama 2 (FP doğrulama): 6/6 kategori örnekleri DOĞRU — long_function 130 satır gövde ✓, high_complexity 26 dal (birebir) ✓, deep_nesting 6 brace derinliği ✓, empty_handler yorumlu boş catch (hata yutuyor) ✓, god_class 70 metot ✓, large_file >600 satır ✓, secret 1 (Firebase AIzaSy) ✓ — örneklemde FP %0
DONE 2026-08-04 — Aşama 3 (FN taraması): parçalı/base64/alternatif token secret YOK, sabit credential YOK, service account YOK, .env yalnızca SALT (motor taramıyor — bilinen sınır, yerel dosya), 3+ seviye döngü için motor 2 seviye bile bulmadı (düşük risk), bağımlılıklar güncel (Firebase 12, Vite 6) — gerçek FN bulunamadı
DONE 2026-08-04 — Aşama 4 (skor kalibrasyonu): testing 60 (18-26 test noktası — makul), documentation 35 (docs/ 3 dosya, README YOK — doğru), architecture 68 (src/ iyi modüler — makul), security 66 (tek client Firebase key — makul)
DONE 2026-08-04 — Aşama 5: NİHAİ RAPOR — TUSLA 62.6 (C) güvenilir; örneklemde FP %0, gerçek FN yok, skor boyutları kod durumuyla tutarlı; kalibrasyon değişikliği GEREKMİYOR

## RUNS
- started: 2026-08-04T18:08:04.691Z
