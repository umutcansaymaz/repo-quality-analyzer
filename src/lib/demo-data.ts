/**
 * Shared demo-data generator.
 *
 * Used by:
 *  - Mock API routes  (src/app/api/analyze, /api/result/[id], /api/report)
 *  - Client-side fallback (src/app/page.tsx `getDemoData`)
 *
 * Produces a deterministic-but-varied analysis result for any repository URL
 * so the app works end-to-end without the real Python backend.
 *
 * When `useLLM` is true (user has saved an API key), the engineering review
 * is generated as if an LLM produced it (offline: false, richer sections,
 * model info, token usage).
 */

// Lightweight deterministic hash so the same URL always yields the same numbers.
function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

function seeded(n: number, min: number, max: number): number {
  return min + (n % 1000) / 1000 * (max - min);
}

function pick<T>(arr: T[], n: number): T {
  return arr[n % arr.length];
}

export interface DemoResult {
  id: string;
  status: string;
  repository: { url: string; owner: string; name: string; host: string; access: string };
  repository_metadata: Record<string, unknown>;
  ai_review: { health_score: Record<string, number>; security_review: Record<string, unknown> };
  root_causes: Record<string, unknown>;
  engineering_plan: Record<string, unknown>;
  evidence: Record<string, unknown>;
  knowledge_graph: Record<string, unknown>;
  file_inventory: Record<string, unknown>;
  engineering_review: Record<string, unknown>;
  analyzed_at: string;
}

export interface GenerateOptions {
  useLLM?: boolean;
  llmProvider?: string;
  llmModel?: string;
}

export function generateDemoData(repoUrl: string, options?: GenerateOptions): DemoResult {
  const owner = repoUrl.split("/").slice(-2)[0] || "example";
  const name = repoUrl.split("/").slice(-1)[0]?.replace(".git", "") || "repo";
  const h = hashString(repoUrl);
  const useLLM = options?.useLLM ?? false;
  const llmProvider = options?.llmProvider || "offline";
  const llmModel = options?.llmModel || "deterministic-fallback";

  // Vary scores deterministically by URL so different repos feel different.
  const overall = Number(seeded(h, 58, 88).toFixed(1));
  const grade = overall >= 80 ? "A" : overall >= 70 ? "B" : overall >= 60 ? "B-" : overall >= 50 ? "C" : "D";
  const security = Number(seeded(h + 1, 65, 95).toFixed(1));
  const architecture = Number(seeded(h + 2, 50, 82).toFixed(1));
  const maintainability = Number(seeded(h + 3, 55, 85).toFixed(1));
  const performance = Number(seeded(h + 4, 60, 88).toFixed(1));
  const documentation = Number(seeded(h + 5, 40, 78).toFixed(1));
  const testing = Number(seeded(h + 6, 35, 80).toFixed(1));
  const developerExperience = Number(seeded(h + 7, 55, 82).toFixed(1));
  const scalability = Number(seeded(h + 8, 58, 85).toFixed(1));
  const codeQuality = Number(seeded(h + 9, 55, 84).toFixed(1));

  const totalCommits = 80 + (h % 400);
  const contributors = ["alice", "bob", "charlie", "dave", "eve"].slice(0, 2 + (h % 4));
  const sizeBytes = 120000 + (h % 800000);
  const license = pick(["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0", "ISC"], h);

  // --- LLM review sections — written like a senior architect talking,
  // NOT restating metrics. Each section gives genuine insight, practical
  // advice, and context that the raw data alone doesn't provide.
  const reviewSections = useLLM
    ? [
        {
          section_type: "executive_summary",
          title: "Özet",
          body: `Bu depoyu inceledim ve açıkçası temel mimari sağlam görünüyor ama birkaç noktada teknik borç biriktirmişsiniz. En belirgin sorun: UserService sınıfı her şeyi yapıyor — kullanıcı oluşturma, kimlik doğrulama, bildirim gönderme, veritabanı sorguları... Bu sınıf büyüdükçe değiştirmek gittikçe zorlaşıyor ve her dokunuş başka bir şeyi kırma riski taşıyor. İyi haber: bu düzeltilebilir ve önünüzde net bir yol haritası var. Önemli olan paralel değil, sıralı ilerlemek — önce en kritik bağımlılığı (UserService) çözün, gerisi daha kolay gelecek.`,
          confidence: "high",
        },
        {
          section_type: "top_root_causes",
          title: "Asıl Sorunlar",
          body: `Şunu fark ettim: buradaki sorunlar birbirinden bağımsız değil, zincirleme etkiliyorlar. UserService'in çok büyümesi (Tanrı Sınıf anti-deseni) doğal olarak sıkı bağlılığa yol açıyor — çünkü her şey bu sınıfa bağımlı. Döngüsel bağımlılık (auth ↔ user) ise muhtemelen "şunu da buradan çağırayım" yaklaşımının sonucu. Yani kök neden tek aslında: sorumlulukların iyi ayrılmamış olması. Bunu çözerseniz, diğer sorunlar da büyük ölçüde kendiliğinden düzelecek.`,
          confidence: "high",
        },
        {
          section_type: "highest_roi_refactoring",
          title: "En Değerli Düzeltme",
          body: "İlginçtir, en yüksek getirili düzeltme en kolayı: loglama kodunu tek bir yere toplamak. Şu anda log formatını değiştirmek istediğinizde 8 dosyayı açmanız gerekiyor — bu sadece zaman kaybı değil, birini atladığınızda tutarsız loglar elde ediyorsunuz. 4 saatlik bir iş ve getirisi çok yüksek. Bunu ilk sprint'e taşıyın — ekibin morali için iyi bir başlangıç olur ve güven oluşturur.",
          confidence: "high",
        },
        {
          section_type: "architecture_review",
          title: "Mimari Değerlendirmem",
          body: `Dürüst olmak gerekirse, bu depo "çalışıyor ama büyürken acı çekecek" kategorisinde. Katman ayrımı kısmen var ama UserService bir "kara delik" oluşturmuş — her şey oraya çekiliyor. Döngüsel bağımlılık (auth ↔ user) özellikle tehlikeli çünkü test yazmayı zorlaştırıyor: auth'ı test etmek için user'a, user'ı test etmek için auth'a ihtiyaç var. Bu birim testleri imkânsız değil ama çok kırılgan hale getiriyor. Bağımlılık enjeksiyonu (DI) tamamen eksik — servisler doğrudan veritabanına ulaşıyor. Bu, ilerde veritabanını değiştirmek istediğinizde büyük acı verecek. Tavsiyem: Facade deseniyle başlayın — UserService'i olduğu gibi bırakın ama yeni kodları ayrı servislere yazın. Zamanla eski kod da göç eder.`,
          confidence: "high",
        },
        {
          section_type: "risk_assessment",
          title: "Riskleri Açıkça Paylaşıyorum",
          body: "UserService'i parçalamak riskli bir iş — 40 saat, 2 geliştirici ve kritik yolları etkiliyor. Bu yüzden 'big bang' yaklaşımı yerine kademeli geçiş şart. Önce bir Facade oluşturun, yeni servisleri arka planda yazın, eski UserService'i facade'a yönlendirin ve sonra kademeli olarak içini boşaltın. Döngüsel bağımlılığı kırmak da benzer şekilde riskli ama şaşırtıcı derecede hızlı sonuç veriyor — ortak mantığı yeni bir modüle çekmek genelde bir gün sürüyor. Test kapsamının %35 olması beni endişelendiriyor: bu kadar düşük kapsamda büyük refactor yapmak yürürken uçurumun kenarında yürümek gibi. Önce testleri yazın, sonra refactor yapın.",
          confidence: "medium",
        },
        {
          section_type: "long_term_vision",
          title: "İleriye Dönük Düşüncelerim",
          body: `Bu depoyu 6 ay sonra 'bakması keyifli bir kod tabanı' haline getirebilirsiniz ama disiplinli olmanız gerek. Her sprint'te bir kök nedeni ele alın — paralel değil, sıralı. CI/CD'ye mimari kalite kapısı ekleyin: döngüsel bağımlılık otomatik engellensin, karmaşıklık eşiği aşıldığında uyarı verilsin. Test kapsamını %35'ten en az %60'a çıkarın — bu bir hedef değil, refactor için güvenlik ağı. Bağımlılık enjeksiyonu standart hale gelmeli. Ve en önemlisi: yeni özellikler eklerken 'UserService'e koyalım' demeyin — her yeni sorumluluk için yeni bir servis oluşturun. Bu disiplin 3-4 sprint sonra alışkanlık haline gelecek.`,
          confidence: "low",
        },
        {
          section_type: "challenge",
          title: "Plana Itirazlarım",
          body: `Plan genel olarak mantıklı ama birkaç noktada itirazım var. Birincisi: Adım 1 (UserService parçalama) çok agresif. 5 günde 2 geliştirici ile 'split God Class' demek, o sırada başka hiçbir özellik geliştirilemeyecek demek. Bunun yerine Facade + Delegate ile başlayın — geriye dönük uyumlu, riski düşük. İkincisi: hızlı kazançlar neden 3. sprint'te? Onları 1. sprint'e taşıyın — ekibin 'bir şeyi tamamladık' hissi yaşaması motivasyon için kritik. Üçüncüsü: test kapsamı %35 iken büyük refactor yapmak çok riskli. Test yazmadan başlamayın.`,
          confidence: "medium",
        },
        {
          section_type: "recommendation",
          title: "Pratik Tavsiyelerim",
          body: "Bunları sırayla yapın:\n1. Önce loglama yardımcı fonksiyonunu çıkarın (4 saat, düşük risk)\n2. Kullanılmayan import'ları temizleyin (15 dakika, anında sonuç)\n3. UserService için test yazın — en azından process_user metodunu\n4. Facade deseni uygulayın, yeni servisleri arkadan yazın\n5. Döngüsel bağımlılığı kırın (ortak mantığı çıkar)\n6. Repository arayüzü tanımlayın (DI için)\nBu sıra önemli: düşük riskli işlerle başlayın, güven oluşturun, sonra büyük refactor'a geçin.",
          confidence: "high",
        },
      ]
    : [
        {
          section_type: "executive_summary",
          title: "Yönetici Özeti",
          body: `Kök neden analizi 4 mimari sorun tespit etti (ortalama güven %80). Mühendislik planı 3 sprint'te 4 adım öneriyor, ~92 saat. 2 hızlı kazanç mevcut. Genel sağlık: ${overall.toFixed(1)}/100 (${grade}).`,
          confidence: "high",
        },
        {
          section_type: "top_root_causes",
          title: "En Önemli Kök Nedenler",
          body: "- Tanrı Sınıf: UserService (yüksek, %85)\n- Döngüsel Bağımlılık: auth ↔ user (yüksek, %92)\n- Sıkı Bağlılık: Veritabanı katmanı (orta, %75)\n- Saçma Değişiklik: Loglama (düşük, %68%)",
          confidence: "high",
        },
        {
          section_type: "highest_roi_refactoring",
          title: "En Yüksek Getirili Yeniden Düzenleme",
          body: "Adım 4: Ortak loglama yardımcı fonksiyonu çıkar\nROI: 5.42\nÖncelik: düşük\nTahmini süre: 4 saat",
          confidence: "high",
        },
        {
          section_type: "long_term_vision",
          title: "Uzun Vadeli Vizyon",
          body: "Önümüzdeki 6 ayda büyük sınıfları tek sorumluluklu bileşenlere ayırın.",
          confidence: "low",
        },
      ];

  return {
    id: `demo-${h.toString(36)}`,
    status: "completed",
    repository: { url: repoUrl, owner, name, host: "github.com", access: "public" },
    repository_metadata: {
      name, owner,
      description: `${owner}/${name} — AI Yazılım Mimarı tarafından analiz edildi`,
      default_branch: "main",
      license,
      total_commits: totalCommits,
      total_branches: 2 + (h % 5),
      contributors,
      size_bytes: sizeBytes,
    },
    ai_review: {
      health_score: {
        overall, grade, security, architecture, maintainability, performance,
        documentation, testing, developer_experience: developerExperience,
        scalability, code_quality: codeQuality,
      },
      security_review: { security_score: security, findings: [], overall_severity: "info" },
    },
    root_causes: {
      root_causes: [
        {
          id: "rc-1",
          category: "god_class",
          title: `Tanrı Sınıf: ${pick(["UserService", "OrderManager", "ApiClient", "DataProcessor"], h)}`,
          severity: "high",
          confidence: 0.85,
          description: "Tek bir sınıf çok sayıda farklı sorumluluğu üstlenmiş — kullanıcı iş mantığı, veri erişimi, bildirimler ve doğrulama hepsi aynı sınıfta. Bu, sınıfın anlaşılmasını, test edilmesini ve bakımını zorlaştırır.",
          technical_rationale: "3 farklı analizörden 4 ayrı belirti tespit edildi: yüksek döngüsel karmaşıklık (CC=41), uzun metod (process_user), büyük dosya (650 SLOC) ve düşük kohesiyon.",
          root_cause_origin: "Zamanla organik büyüme — yeni özellikler eklendikçe tek sınıfa yığılmış, refactor yapılmamış.",
          affected_files: ["src/services/user_service.py", "src/api/user_routes.py"],
          affected_classes: ["UserService"],
          affected_modules: ["services.user"],
          evidence_count: 8,
          evidence_links: [
            { evidence_id: "ev-1", contribution: 0.9, reason: "Yüksek karmaşıklık" },
            { evidence_id: "ev-2", contribution: 0.8, reason: "Uzun metod" },
            { evidence_id: "ev-3", contribution: 0.7, reason: "Büyük dosya" },
          ],
        },
        {
          id: "rc-2",
          category: "circular_dependency",
          title: "Döngüsel Bağımlılık: auth ↔ user",
          severity: "high",
          confidence: 0.92,
          description: "auth modülü user modülünü, user modülü de auth modülünü içe aktarıyor. Bu döngü, modüllerin bağımsız test edilmesini engeller ve başlatma sırasında hatalara yol açabilir.",
          technical_rationale: "Import grafiğinde doğrudan döngü tespit edildi: auth → user → auth.",
          root_cause_origin: "Modüller import yönü kontrol edilmeden eklenmiş. Ortak mantık alt seviye bir modüle çıkarılmamış.",
          affected_files: ["src/auth/service.py", "src/user/service.py"],
          affected_modules: ["auth", "user"],
          evidence_count: 3,
          evidence_links: [{ evidence_id: "ev-4", contribution: 1.0, reason: "Doğrudan döngü" }],
        },
        {
          id: "rc-3",
          category: "tight_coupling",
          title: "Sıkı Bağlılık: Veritabanı Katmanı",
          severity: "medium",
          confidence: 0.75,
          description: "Birden fazla servis doğrudan veritabanı istemcisine bağlı. Veritabanı uygulaması değişirse, tüm servislerin güncellenmesi gerekiyor. Test için mock veritabanı kullanmak zor.",
          technical_rationale: "Graf analizi aşırı bağımlılık kenarları gösteriyor — servisler arayüz (interface) yerine somut DB istemcisine bağlı.",
          root_cause_origin: "Soyutlama (abstraction) yerine doğrudan bağımlılık kullanılmış. Bağımlılık enjeksiyonu (DI) uygulanmamış.",
          affected_files: ["src/services/user_service.py", "src/services/order_service.py"],
          affected_modules: ["services"],
          evidence_count: 5,
          evidence_links: [{ evidence_id: "ev-5", contribution: 0.8, reason: "Yüksek bağlılık ölçümü" }],
        },
        {
          id: "rc-4",
          category: "shotgun_surgery",
          title: "Saçma Değişiklik: Loglama",
          severity: "low",
          confidence: 0.68,
          description: "Loglama formatı değiştiğinde 8 farklı dosyada değişiklik yapmak gerekiyor. Bu, merkezi bir loglama yardımcı fonksiyonu olmamasından kaynaklanıyor.",
          technical_rationale: "Aynı belirti 8 farklı dosyada tespit edildi — copy-paste ile yayılmış.",
          root_cause_origin: "Ortak bir yardımcı fonksiyon çıkarılmadan copy-paste yapılmış.",
          affected_files: ["src/api/users.py", "src/api/orders.py", "src/api/products.py", "src/api/payments.py", "src/services/user_service.py"],
          affected_modules: ["api", "services"],
          evidence_count: 8,
          evidence_links: [{ evidence_id: "ev-6", contribution: 0.7, reason: "Sistemik desen" }],
        },
      ],
      relationships: [{ source_root_cause_id: "rc-1", target_root_cause_id: "rc-3", relationship_type: "causes", detail: "Tanrı Sınıf, sıkı bağlılığa neden oluyor" }],
      statistics: { total_root_causes: 4, average_confidence: 0.80, by_category_counts: { god_class: 1, circular_dependency: 1, tight_coupling: 1, shotgun_surgery: 1 }, by_severity_counts: { high: 2, medium: 1, low: 1 } },
      // Root Cause Validation: each RC has analyzer_consensus (how many independent
      // analyzers support it) and conflicting_evidence (if any analyzer disagrees).
      validation: {
        "rc-1": { analyzer_consensus: 3, supporting_analyzers: ["karmaşılık-analizörü", "kod-kalitesi-motoru", "metrik-motoru"], conflicting_evidence: [], validation_status: "verified", min_analyzers_required: 2 },
        "rc-2": { analyzer_consensus: 2, supporting_analyzers: ["import-analizörü", "mimari-inceleme-motoru"], conflicting_evidence: [], validation_status: "verified", min_analyzers_required: 2 },
        "rc-3": { analyzer_consensus: 2, supporting_analyzers: ["mimari-inceleme-motoru", "karmaşılık-analizörü"], conflicting_evidence: [], validation_status: "verified", min_analyzers_required: 2 },
        "rc-4": { analyzer_consensus: 1, supporting_analyzers: ["import-analizörü"], conflicting_evidence: [], validation_status: "partial", min_analyzers_required: 2 },
      },
    },
    engineering_plan: {
      steps: [
        {
          id: "step-1",
          step_number: 1,
          title: "Tanrı Sınıf'ı parçalara ayır",
          technical_description: "UserService'i auth, profile, notifications ve settings olmak üzere 4 ayrı servise böl. Her servis tek bir sorumluluğa sahip olmalı.",
          root_cause_id: "rc-1",
          root_cause_category: "god_class",
          priority: "high",
          roi: 2.25,
          estimate: { hours: 40, display: "5 gün", developers: 2, confidence: 0.5 },
          risk: "high",
          risk_reason: "Büyük ölçekli refactor — kritik yolları etkiliyor.",
          expected_outcomes: ["Bakım yapılabilirlik +%90", "Test edilebilirlik +%80"],
          prerequisites: [],
          alternatives: [
            { id: "alt-1", name: "Sınıf Çıkarımı", description: "Odaklı sınıflara böl.", advantages: ["Net sorumluluklar", "Kolay test"], disadvantages: ["Daha fazla dosya"], risk: "medium", maintenance_cost: "low", performance_impact: "neutral", migration_difficulty: "medium" },
            { id: "alt-2", name: "Facade + Yetkilendir", description: "Facade olarak kal, içten yetkilendir.", advantages: ["Geriye dönük uyumlu", "Kademeli geçiş"], disadvantages: ["Facade hala var"], risk: "low", maintenance_cost: "medium", performance_impact: "neutral", migration_difficulty: "low" },
          ],
          affected_files: ["src/services/user_service.py"],
          verified_status: "verified",
          evidence_chain: ["ev-1", "ev-2", "ev-3"],
        },
        {
          id: "step-2",
          step_number: 2,
          title: "Döngüsel bağımlılığı kır: auth ↔ user",
          technical_description: "Ortak mantığı yeni bir alt seviye modüle taşı (örn. shared/auth_utils). Böylece auth ve user modülleri bu modüle bağımlı olur ama birbirine değil.",
          root_cause_id: "rc-2",
          root_cause_category: "circular_dependency",
          priority: "high",
          roi: 3.54,
          estimate: { hours: 24, display: "3 gün", developers: 1, confidence: 0.5 },
          risk: "high",
          risk_reason: "Değişiklikler kritik yolları etkiliyor.",
          expected_outcomes: ["Bakım yapılabilirlik +%85", "Test edilebilirlik +%80"],
          prerequisites: ["step-1"],
          alternatives: [],
          affected_files: ["src/auth/service.py", "src/user/service.py"],
          verified_status: "verified",
          evidence_chain: ["ev-4", "ev-5"],
        },
        {
          id: "step-3",
          step_number: 3,
          title: "Veritabanı erişimi için repository arayüzü tanımla",
          technical_description: "Soyut bir repository arayüzü (interface) oluştur ve bağımlılık enjeksiyonu (DI) ile kullan. Servisler somut DB istemcisine değil arayüze bağımlı olur.",
          root_cause_id: "rc-3",
          root_cause_category: "tight_coupling",
          priority: "medium",
          roi: 1.88,
          estimate: { hours: 24, display: "3 gün", developers: 1, confidence: 0.5 },
          risk: "medium",
          risk_reason: "Orta ölçekli değişiklikler.",
          expected_outcomes: ["Test edilebilirlik +%70", "Bakım yapılabilirlik +%75"],
          prerequisites: ["step-1"],
          alternatives: [],
          affected_files: ["src/services/user_service.py", "src/services/order_service.py"],
          verified_status: "evidence_backed",
          evidence_chain: ["ev-5", "ev-1"],
        },
        {
          id: "step-4",
          step_number: 4,
          title: "Ortak loglama yardımcı fonksiyonu çıkar",
          technical_description: "Merkezi bir loglama sarmalayıcı (wrapper) oluştur. Tüm dosyalar bunu kullansın. Loglama formatı tek yerden yönetilsin.",
          root_cause_id: "rc-4",
          root_cause_category: "shotgun_surgery",
          priority: "low",
          roi: 5.42,
          estimate: { hours: 4, display: "4 saat", developers: 1, confidence: 0.7 },
          risk: "low",
          risk_reason: "Düşük risk — izole değişiklikler.",
          expected_outcomes: ["Teknik borç azaldı", "Tutarlı loglama"],
          prerequisites: [],
          alternatives: [],
          affected_files: ["src/api/users.py", "src/api/orders.py"],
          verified_status: "partially_verified",
          evidence_chain: ["ev-6"],
        },
      ],
      roadmap: {
        sprints: [
          { sprint_number: 1, title: "Sprint 1: Kritik Refactor", step_ids: ["step-1"], total_estimated_hours: 40, goals: ["Tanrı Sınıf'ı parçala"], steps: [] },
          { sprint_number: 2, title: "Sprint 2: Mimari Düzeltmeler", step_ids: ["step-2", "step-3"], total_estimated_hours: 48, goals: ["Döngüsel bağımlılığı kır", "Repository arayüzü tanımla"], steps: [] },
          { sprint_number: 3, title: "Sprint 3: Temizlik ve Bakım", step_ids: ["step-4"], total_estimated_hours: 4, goals: ["Ortak loglama çıkar"], steps: [] },
        ],
        total_estimated_hours: 92,
        total_steps: 4,
        summary: "3 sprint, 4 adım, ~92 saat toplam.",
      },
      quick_wins: [
        { id: "qw-1", title: "Ortak loglama yardımcı fonksiyonu çıkar", description: "Merkezi loglama sarmalayıcı oluştur.", effort_minutes: 240, benefit: "Fayda skoru: 65/100", planning_step_id: "step-4", root_cause_id: "rc-4" },
        { id: "qw-2", title: "Kullanılmayan import'ları kaldır", description: "5 kullanılmayan import tespit edildi.", effort_minutes: 15, benefit: "Hızlı düzeltme: ölü kod", planning_step_id: null, root_cause_id: null },
      ],
      blockers: [{ id: "blk-1", blocker_root_cause_id: "rc-1", blocked_root_cause_ids: ["rc-3"], reason: "Tanrı Sınıf önce ele alınmalı.", planning_step_id: "step-1" }],
      statistics: { total_steps: 4, total_quick_wins: 2, total_blockers: 1, average_roi: 3.27, priority_counts: { high: 2, medium: 1, low: 1 }, risk_counts: { high: 2, medium: 1, low: 1 } },
    },
    evidence: {
      evidence: [
        { id: "ev-1", analyzer: "karmaşılık-analizörü", finding_type: "complexity", severity: "high", confidence: 1.0, category: "cyclomatic_complexity", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "Yüksek karmaşıklık: process_user (Döngüsel Karmaşıklık=41)", tags: ["complexity", "E"], metrics: { complexity: 41, rank: "E" }, validation_status: "pass", validated_by: ["karmaşılık-analizörü", "metrik-motoru"] },
        { id: "ev-2", analyzer: "kod-kalitesi-motoru", finding_type: "code_quality", severity: "medium", confidence: 0.8, category: "long_method", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "Uzun metod: process_user", tags: ["long_method", "high"], validation_status: "pass", validated_by: ["kod-kalitesi-motoru", "karmaşılık-analizörü"] },
        { id: "ev-3", analyzer: "metrik-motoru", finding_type: "metric", severity: "medium", confidence: 1.0, category: "large_file", file_path: "src/services/user_service.py", message: "Büyük dosya (650 SLOC)", tags: ["large_file"], metrics: { sloc: 650 }, validation_status: "pass", validated_by: ["metrik-motoru"] },
        { id: "ev-4", analyzer: "import-analizörü", finding_type: "import", severity: "high", confidence: 1.0, category: "circular_import", message: "Döngüsel import: auth → user → auth", tags: ["circular_import"], validation_status: "pass", validated_by: ["import-analizörü", "mimari-inceleme-motoru"] },
        { id: "ev-5", analyzer: "mimari-inceleme-motoru", finding_type: "architecture", severity: "medium", confidence: 0.7, category: "high_coupling", file_path: "src/services/user_service.py", message: "Yüksek bağlılık (0.85)", tags: ["high_coupling"], validation_status: "warning", validated_by: ["mimari-inceleme-motoru"] },
        { id: "ev-6", analyzer: "import-analizörü", finding_type: "import", severity: "low", confidence: 0.9, category: "unused_import", file_path: "src/api/users.py", message: "Kullanılmayan import: os", tags: ["unused_import", "dead_code"], validation_status: "pass", validated_by: ["import-analizörü"] },
        { id: "ev-7", analyzer: "güvenlik-motoru", finding_type: "security", severity: "critical", confidence: 0.9, category: "hardcoded_password", file_path: "src/config.py", line: 10, message: "Sabit kodlanmış şifre", tags: ["hardcoded_password"], validation_status: "pass", validated_by: ["güvenlik-motoru", "kod-kalitesi-motoru"] },
        { id: "ev-8", analyzer: "test-kapsamı-analizörü", finding_type: "test", severity: "medium", confidence: 0.9, category: "low_coverage", message: "Düşük test kapsamı: %35", tags: ["testing", "low_coverage"], metrics: { estimated_coverage: 35 }, validation_status: "warning", validated_by: ["test-kapsamı-analizörü"] },
      ],
      relationships: [],
      statistics: { total_evidence: 8, passed: 6, warning: 2, failed: 0, by_type_counts: { complexity: 1, code_quality: 1, metric: 1, import: 2, architecture: 1, security: 1, test: 1 }, by_severity_counts: { critical: 1, high: 2, medium: 3, low: 2 }, by_analyzer_counts: { "karmaşılık-analizörü": 1, "kod-kalitesi-motoru": 1, "metrik-motoru": 1, "import-analizörü": 2, "mimari-inceleme-motoru": 1, "güvenlik-motoru": 1, "test-kapsamı-analizörü": 1 } },
    },
    knowledge_graph: {
      nodes: [
        { id: "n1", node_type: "repository", label: `${owner}/${name}`, key: "repo:1" },
        { id: "n2", node_type: "file", label: "src/services/user_service.py", key: "file:1", file_path: "src/services/user_service.py" },
        { id: "n3", node_type: "file", label: "src/api/users.py", key: "file:2", file_path: "src/api/users.py" },
        { id: "n4", node_type: "class", label: "UserService", key: "class:1", file_path: "src/services/user_service.py", class_name: "UserService" },
        { id: "n5", node_type: "function", label: "process_user", key: "func:1", file_path: "src/services/user_service.py", function_name: "process_user" },
        { id: "n6", node_type: "module", label: "services.user", key: "module:1", module: "services.user" },
        { id: "n7", node_type: "module", label: "auth", key: "module:2", module: "auth" },
        { id: "n8", node_type: "security_finding", label: "Sabit kodlanmış şifre", key: "ev:7", file_path: "src/config.py", severity: "critical", evidence_id: "ev-7", metadata: { analyzer: "güvenlik-motoru" } },
        { id: "n9", node_type: "metric_finding", label: "Yüksek karmaşıklık: process_user", key: "ev:1", file_path: "src/services/user_service.py", severity: "high", evidence_id: "ev-1", metadata: { analyzer: "karmaşılık-analizörü" } },
        { id: "n10", node_type: "dependency", label: "requests", key: "dep:1", metadata: {} },
      ],
      edges: [
        { id: "e1", source_id: "n2", target_id: "n1", edge_type: "belongs_to" },
        { id: "e2", source_id: "n3", target_id: "n1", edge_type: "belongs_to" },
        { id: "e3", source_id: "n4", target_id: "n2", edge_type: "belongs_to" },
        { id: "e4", source_id: "n5", target_id: "n2", edge_type: "belongs_to" },
        { id: "e5", source_id: "n9", target_id: "n5", edge_type: "affects" },
        { id: "e6", source_id: "n8", target_id: "n2", edge_type: "affects" },
      ],
      total_nodes: 10, total_edges: 6,
    },
    file_inventory: { total_files: 24, total_directories: 8, total_bytes: sizeBytes, files: ["src/services/user_service.py", "src/api/users.py", "src/api/orders.py", "src/auth/service.py", "src/user/service.py", "src/config.py", "src/models/user.py", "src/utils/helpers.py", "tests/test_user_service.py", "README.md"] },
    engineering_review: {
      offline: !useLLM,
      sections: reviewSections,
      challenges: useLLM
        ? [
            { target_step_id: "step-1", challenge_type: "too_aggressive", description: "UserService'i 5 günde parçalamaya çalışmak çok agresif. Bu süre zarfında başka özellik geliştiremeyeceksiniz ve kritik yolları etkileyecek. Daha güvenli yol: önce bir Facade oluşturun, yeni servisleri arka planda yazın, eski kodu kademeli olarak taşıyın.", alternative: "Facade + Delegate deseni ile kademeli geçiş. İlk sprint'te sadece yapısını kurun, ikinci sprint'te tek bir sorumluluğu taşıyın." },
            { target_step_id: "step-3", challenge_type: "insufficient_evidence", description: "Adım 3'ü adım 1'den önce yapmaya çalışmak tehlikeli — her ikisi de UserService'i değiştiriyor. Paralel çalışırsanız merge conflict'ler kaosa döner.", alternative: "Adım 1 tamamen bittikten sonra adım 3'ü başlatın. Arada en az bir sprint olsun." },
          ]
        : [],
      recommendations: useLLM
        ? [
            { title: "Hızlı kazançları ilk sprint'e taşıyın", description: "Loglama yardımcı fonksiyonu ve kullanılmayan import temizliği çok hızlı ve düşük riskli. Ekibin 'bir şeyi tamamladık' hissi yaşaması motivasyon için kritik.", priority: "medium", confidence: "high", rationale: "Düşük risk, yüksek görünürlük, anında sonuç.", linked_step_ids: ["step-4"], linked_root_cause_ids: ["rc-4"] },
            { title: "Refactor öncesi test yazın", description: "Test kapsamı %35 — bu, büyük refactor yaparken 'ne yaptığımı bilmiyorum' demek. Önce UserService için en azından process_user metodunu test edin.", priority: "high", confidence: "high", rationale: "Mevcut düşük kapsam, refactor sırasında regresyon riskini çok artırıyor.", linked_step_ids: ["step-1"], linked_root_cause_ids: [] },
            { title: "Yeni kod için DI kullanın", description: "Mevcut servisleri değiştirmesen bile, yeni yazdığınız her servis bağımlılık enjeksiyonu kullansın. Bu, gelecekteki refactor'ları çok kolaylaştıracak.", priority: "low", confidence: "medium", rationale: "Kademeli geçiş — yeni kod kaliteli olsun, eski kod zamanla göç etsin.", linked_step_ids: ["step-3"], linked_root_cause_ids: ["rc-3"] },
          ]
        : [],
      model_info: useLLM
        ? { provider: llmProvider, model: llmModel, temperature: 0.3 }
        : { provider: "offline", model: "deterministic-fallback" },
      prompt_tokens: useLLM ? 2847 : 0,
      completion_tokens: useLLM ? 1923 : 0,
      statistics: { total_sections: reviewSections.length, total_challenges: useLLM ? 2 : 0, offline: !useLLM },
      // Claim Verification Engine: each LLM sentence is verified against evidence.
      // Claims without evidence are marked "opinion", claims with evidence are "verified".
      claim_verification: useLLM ? {
        total_claims: 24,
        verified: 18,
        opinion: 5,
        rejected: 1,
        verification_rate: 0.75,
        claims: [
          { id: "claim-1", text: "UserService sınıfı her şeyi yapıyor", evidence_ids: ["ev-1", "ev-2", "ev-3"], status: "verified", reason: "3 kanıt bulgusu doğruladı" },
          { id: "claim-2", text: "Döngüsel bağımlılık test yazmayı zorlaştırıyor", evidence_ids: ["ev-4"], status: "verified", reason: "Import analizörü doğruladı" },
          { id: "claim-3", text: "Bağımlılık enjeksiyonu tamamen eksik", evidence_ids: [], status: "opinion", reason: "Kanıt bulunamadı — mimari yorum" },
          { id: "claim-4", text: "Loglama 8 dosyada dağınık", evidence_ids: ["ev-6"], status: "verified", reason: "Import analizörü doğruladı" },
          { id: "claim-5", text: "Test kapsamı %35", evidence_ids: ["ev-8"], status: "verified", reason: "Test kapsamı analizörü doğruladı" },
          { id: "claim-6", text: "Sabit kodlanmış şifre tespit edildi", evidence_ids: ["ev-7"], status: "verified", reason: "Güvenlik motoru doğruladı" },
          { id: "claim-7", text: "6 ayda bakması keyifli kod tabanı olabilir", evidence_ids: [], status: "opinion", reason: "Gelecek tahmini — kanıtlanamaz" },
          { id: "claim-8", text: "Facade deseni en güvenli geçiş yolu", evidence_ids: [], status: "opinion", reason: "Mimari öneri — kanıtla doğrulanamaz" },
        ],
      } : null,
      // Confidence Model: multi-component confidence calculation.
      // NOT a single number — broken down by component so users can see WHY.
      confidence_model: {
        deterministic_confidence: Math.round(((6 / 8) * 100 + (3 / 4) * 100) / 2), // evidence pass rate + RC consensus
        evidence_coverage: Math.round((7 / 8) * 100), // 7 of 8 evidence items have file_path
        claim_verification_rate: useLLM ? 75 : 100, // % of LLM claims verified (100% when offline — no claims)
        analyzer_consensus: Math.round((3 / 4) * 100), // % of root causes with ≥2 analyzers
        hallucination_risk: useLLM ? 21 : 0, // 5 opinion + 1 rejected out of 24 claims
        verified_findings: 3, // 3 of 4 recommendations are verified/evidence_backed
        ai_opinions: useLLM ? 5 : 0,
        rejected_claims: useLLM ? 1 : 0,
        conflict_penalty: 0, // no conflicting evidence
        missing_evidence_penalty: useLLM ? 6 : 0, // 1 step has only 1 evidence
      },
    },
    analyzed_at: new Date().toISOString(),
  };
}

/**
 * Build a human-readable report from a demo result.
 * Supports: markdown ("md"), json, html, text.
 */
export function buildReport(result: DemoResult, format: string): { content: string; contentType: string; filename: string } {
  const hs = result.ai_review.health_score as any;
  const repo = result.repository;
  const rc = result.root_causes as any;
  const plan = result.engineering_plan as any;

  if (format === "json") {
    return {
      content: JSON.stringify(result, null, 2),
      contentType: "application/json",
      filename: `${repo.owner}-${repo.name}-report.json`,
    };
  }

  if (format === "html") {
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>Rapor — ${repo.owner}/${repo.name}</title>
<style>body{font-family:system-ui,sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;color:#222}h1{color:#1a1a1a}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:6px 8px;text-align:left}th{background:#f5f5f5}</style>
</head><body>
<h1>AI Yazılım Mimarı — Rapor</h1>
<p><strong>Depo:</strong> ${repo.owner}/${repo.name}</p>
<p><strong>Sağlık:</strong> ${hs.overall}/100 (Not ${hs.grade})</p>
<h2>Sağlık Skorları</h2>
<table><tr><th>Boyut</th><th>Skor</th></tr>
<tr><td>Güvenlik</td><td>${hs.security}</td></tr>
<tr><td>Mimari</td><td>${hs.architecture}</td></tr>
<tr><td>Bakım Yapılabilirlik</td><td>${hs.maintainability}</td></tr>
<tr><td>Test</td><td>${hs.testing}</td></tr>
<tr><td>Dokümantasyon</td><td>${hs.documentation}</td></tr>
</table>
<h2>Kök Nedenler (${rc.root_causes.length})</h2>
<ul>${rc.root_causes.map((r: any) => `<li><strong>${r.title}</strong> — ${r.severity}, ${(r.confidence * 100).toFixed(0)}% güven</li>`).join("")}</ul>
<h2>Mühendislik Planı (${plan.steps.length} adım)</h2>
<ol>${plan.steps.map((s: any) => `<li><strong>${s.title}</strong> — ROI ${s.roi.toFixed(2)}, ${s.estimate.display}, risk: ${s.risk}</li>`).join("")}</ol>
</body></html>`;
    return {
      content: html,
      contentType: "text/html",
      filename: `${repo.owner}-${repo.name}-report.html`,
    };
  }

  // Default: markdown
  const lines: string[] = [];
  lines.push(`# AI Yazılım Mimarı — Rapor`);
  lines.push("");
  lines.push(`**Depo:** ${repo.owner}/${repo.name}`);
  lines.push(`**URL:** ${repo.url}`);
  lines.push(`**Analiz zamanı:** ${result.analyzed_at}`);
  lines.push("");
  lines.push(`## Sağlık Skoru`);
  lines.push("");
  lines.push(`| Boyut | Skor |`);
  lines.push(`|---|---|`);
  lines.push(`| Genel | **${hs.overall}/100** (Not ${hs.grade}) |`);
  lines.push(`| Güvenlik | ${hs.security} |`);
  lines.push(`| Mimari | ${hs.architecture} |`);
  lines.push(`| Bakım Yapılabilirlik | ${hs.maintainability} |`);
  lines.push(`| Test | ${hs.testing} |`);
  lines.push(`| Dokümantasyon | ${hs.documentation} |`);
  lines.push("");
  lines.push(`## Kök Nedenler (${rc.root_causes.length})`);
  lines.push("");
  rc.root_causes.forEach((r: any) => {
    lines.push(`### ${r.title}`);
    lines.push(`- **Önem:** ${r.severity}`);
    lines.push(`- **Güven:** ${(r.confidence * 100).toFixed(0)}%`);
    lines.push(`- **Kategori:** ${r.category}`);
    lines.push(`- **Kanıt sayısı:** ${r.evidence_count}`);
    if (r.description) lines.push(`- **Açıklama:** ${r.description}`);
    lines.push("");
  });
  lines.push(`## Mühendislik Planı (${plan.steps.length} adım)`);
  lines.push("");
  plan.steps.forEach((s: any) => {
    lines.push(`### ${s.step_number}. ${s.title}`);
    lines.push(`- **Öncelik:** ${s.priority}`);
    lines.push(`- **ROI:** ${s.roi.toFixed(2)}`);
    lines.push(`- **Tahmini süre:** ${s.estimate.display} (${s.estimate.hours} saat)`);
    lines.push(`- **Risk:** ${s.risk}`);
    if (s.technical_description) lines.push(`- **Açıklama:** ${s.technical_description}`);
    lines.push("");
  });
  lines.push(`---`);
  lines.push(`*AI Yazılım Mimarı tarafından üretildi*`);
  return {
    content: lines.join("\n"),
    contentType: "text/markdown",
    filename: `${repo.owner}-${repo.name}-report.md`,
  };
}
