# Deterministik Güven ve Kanıt Kapsamını %100'e Çekme Planı

## Mevcut durum

Trust Panel metrikleri ana dashboard'da `engineering_review.confidence_model` alanından okunuyor.
Demo akışında bu model `src/lib/demo-data.ts` içinde elle üretiliyor.
Gerçek batch sonuçlarında `validation_results/validation_summary.json` tarafında `avg_coverage` zaten 100, fakat `avg_confidence` yaklaşık 0.81.

Ana eksikler:

- `deterministic_confidence`: Demo veride 75. Sebep: 8 kanıttan 6'sı pass ve 4 kök nedenden 3'ü tam verified.
- `evidence_coverage`: Demo veride 88. Sebep: 8 kanıttan 7'sinde dosya yolu var.
- `claim_verification_rate`: LLM açıkken 75. Sebep: 24 claim varsayılıyor, 18 verified, 5 opinion, 1 rejected.
- `coverage_score`: Demo veride 67-73 aralığında. Sebep: step-1, step-3, step-4 ihtiyaç duyduğu kanıt sayısını tamamlamıyor.
- `analyzer_consensus`: Demo veride 75. Sebep: rc-4 sadece 1 analizör tarafından destekleniyor.
- `hallucination_risk`: LLM açıkken 21. Sebep: opinion + rejected claim'ler var.

## %100 için kabul kriterleri

Bir analiz sonucunda Deterministik Güven ve Kanıt Kapsamı %100 sayılabilsin diye şu koşullar birlikte sağlanmalı:

1. Her evidence `validation_status: "pass"` olmalı.
2. Her evidence bir `file_path` veya açıkça dosyasız olduğunu belirten kanıt tipi taşımalı. Dosyasız mimari/idari yorumlar coverage hesabına dahil edilmemeli.
3. Her root cause `validation_status: "verified"` olmalı.
4. Her root cause en az 2 bağımsız analizör tarafından desteklenmeli.
5. Her recommendation/plan step `verified_status: "verified"` olmalı.
6. Her step için `coverage_engine[step].has_evidence === needs_evidence` olmalı.
7. Her step kalite kapılarında `evidence_validation`, `claim_validation`, `graph_validation` pass olmalı.
8. Her LLM claim ya verified olmalı ya da deterministik güven hesabından ayrı `commentary/opinion` olarak etiketlenmeli. Kanıtsız iddia güven skoruna girmemeli.
9. Her graph reasoning path `verified: true` olmalı.
10. Conflicting evidence varsa çözülmeden %100 verilmemeli.

## Demo veride doğrudan düzeltilmesi gerekenler

- `ev-4` için `file_path` ekle: `src/auth/service.py` veya iki dosyalı bir alanla `src/auth/service.py`, `src/user/service.py`.
- `ev-8` için `file_path` ekle: örneğin `tests/test_user_service.py` veya coverage raporu artefaktı.
- `rc-4` için ikinci bağımsız kanıt ekle. Öneri: `logging-consistency-analyzer` veya `duplication-analyzer` ile `ev-9`.
- `step-1` evidence_chain'i 4 kanıta tamamla. Öneri: `ev-8` test kapsamı refactor ön koşulu olarak bağlansın.
- `step-3` evidence_chain'i 3 kanıta tamamla. Öneri: DB bağımlılığı için yeni `ev-10` somut client bağımlılığı kanıtı.
- `step-4` evidence_chain'i 2 kanıta tamamla. Öneri: `ev-6` + yeni `ev-9` duplicate/logging spread kanıtı.
- `claim-3`, `claim-7`, `claim-8` gibi kanıtsız claim'ler ya verified kanıta bağlanmalı ya da `opinion` olarak güven skorundan çıkarılmalı.
- Rejected claim güven modeline girmeden önce ya kanıtla doğrulanmalı ya da AI commentary bölümünde ayrı gösterilmeli.

## Gerçek analiz motorunda yapılması gerekenler

1. Evidence schema'ya `source_artifact` ve `traceability` alanları ekle: file, line, symbol, analyzer, metric, graph node.
2. Root cause confidence hesabını tek değer değil bileşenlerle üret: evidence pass rate, analyzer consensus, graph verification, conflict penalty, missing evidence penalty.
3. Coverage Engine'i hardcoded değil, her step'in `evidence_chain`, `root_cause_id`, `affected_files`, `quality_gates` alanlarından türet.
4. Claim Verification Engine'i LLM çıktısından iddia çıkarıp her iddiayı evidence id'lerine bağlayacak şekilde zorunlu hale getir.
5. Kanıtsız LLM yorumlarını `ai_opinion` olarak ayır; deterministik güven skoruna dahil etme.
6. CI'ya trust gate ekle: deterministic confidence, evidence coverage, coverage score ve claim verification target altında ise raporu `not_verified` üret.

## Formül önerisi

`deterministic_confidence`:

```text
round(avg(
  evidence_pass_rate,
  root_cause_verified_rate,
  analyzer_consensus_rate,
  graph_verified_rate,
  recommendation_verified_rate
)) - conflict_penalty - missing_evidence_penalty
```

`evidence_coverage`:

```text
round(traceable_evidence_count / required_traceable_evidence_count * 100)
```

`claim_verification_rate`:

```text
round(verified_claim_count / verifiable_claim_count * 100)
```

Not: `opinion`, `future_prediction`, `taste/preference` gibi kanıtlanamaz claim'ler `verifiable_claim_count` içine girmemeli.

## Sonuç

%100'e ulaşmanın doğru yolu sayıları 100 yapmak değil, tüm deterministik bulgular için tam izlenebilirlik zinciri kurmak:

`Analyzer -> Evidence -> File/Symbol/Metric -> Root Cause -> Recommendation -> Claim -> Graph Path`

Bu zincirde boş halka kalmadığında Trust Panel metrikleri doğal olarak %100'e gelir.