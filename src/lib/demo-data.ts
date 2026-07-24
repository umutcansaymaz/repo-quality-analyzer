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

  // --- LLM review sections (richer when useLLM is true) ---
  const reviewSections = useLLM
    ? [
        {
          section_type: "executive_summary",
          title: "Yönetici Özeti",
          body: `${owner}/${name} deposu analiz edildi. Genel sağlık skoru ${overall.toFixed(1)}/100 (${grade}). 4 mimari kök neden tespit edildi (ortalama güven %80). Mühendislik planı 4 adım öneriyor — 3 sprint'te ~92 saat. 2 hızlı kazanç mevcut. En kritik sorun: "Tanrı Sınıf" (God Class) anti-deseni ve döngüsel bağımlılık. Önerilen ilk adım: UserService sınıfını parçalara ayırmak.`,
          confidence: "high",
        },
        {
          section_type: "top_root_causes",
          title: "En Önemli Kök Nedenler",
          body: "1. Tanrı Sınıf: UserService — çok sayıda sorumluluğu tek sınıfta toplamış (yüksek, %85)\n2. Döngüsel Bağımlılık: auth ↔ user — modüller birbirini içe aktarıyor (yüksek, %92)\n3. Sıkı Bağlılık: Veritabanı katmanı — servisler doğrudan DB'ye bağlı (orta, %75)\n4. Saçma Değişiklik: Loglama — tek değişiklik 8 dosyayı etkiliyor (düşük, %68)",
          confidence: "high",
        },
        {
          section_type: "highest_roi_refactoring",
          title: "En Yüksek Getirili Yeniden Düzenleme",
          body: "Adım 4: Ortak loglama yardımcı fonksiyonu çıkar\nROI: 5.42\nÖncelik: düşük\nTahmini süre: 4 saat",
          confidence: "high",
        },
        {
          section_type: "architecture_review",
          title: "Mimari İnceleme",
          body: `Depo mimarisi ${architecture.toFixed(0)}/100 puan aldı. Katmanlı yapı kısmen mevcut ama servis katmanında sorumluluk ayrımı zayıf. UserService sınıfı hem iş mantığı hem veri erişimi hem de bildirimleri yönetiyor — bu "Tanrı Sınıf" anti-desenine işaret ediyor. Modüller arası döngüsel bağımlılık (auth ↔ user) test edilebilirliği zorlaştırıyor. Bağımlılık enjeksiyonu (DI) kullanılmadığı için servisler veritabanı istemcisine sıkı bağlı. Önerilen yaklaşım: önce Tanrı Sınıf'ı parçalara ayır, ardından arayüz (interface) tabanlı bağımlılık enjeksiyonu geç.`,
          confidence: "high",
        },
        {
          section_type: "risk_assessment",
          title: "Risk Değerlendirmesi",
          body: "Yüksek riskli adımlar: UserService parçalama (40 saat, 2 geliştirici) ve döngüsel bağımlılık kırma (24 saat). Her ikisi de kritik yolları etkiliyor. Geçiş stratejisi: 'Facade + Delegate' deseni kullanılarak geriye dönük uyumlu, kademeli geçiş önerilir. Düşük riskli hızlı kazançlar: loglama yardımcı fonksiyonu (4 saat) ve kullanılmayan import temizliği (15 dakika).",
          confidence: "medium",
        },
        {
          section_type: "long_term_vision",
          title: "Uzun Vadeli Vizyon",
          body: "Önümüzdeki 6 ayda büyük sınıfları tek sorumluluklu (single-responsibility) bileşenlere ayırın. Her sprint'te en az bir kök nedeni ele alın. Test kapsamı %35'ten %70'e çıkarılmalı. Bağımlılık enjeksiyonu çerçevesi (örn. FastAPI Depends) tüm servisler için standart hale gelmeli. CI/CD pipeline'ına mimari kalite kapısı ekleyin: döngüsel bağımlılık ve yüksek karmaşıklık otomatik engellenmeli.",
          confidence: "low",
        },
        {
          section_type: "challenge",
          title: "Plan Eleştirisi",
          body: "Adım 1 (UserService parçalama) çok agresif — 5 gün, 2 geliştirici. Alternatif olarak, önce Facade deseniyle geriye dönük uyumlu bir geçiş yapılabilir. Adım 3'ün adım 1'e bağımlılığı var ama her ikisi de yüksek riskli — paralel değil sıralı yapılmalı. Hızlı kazançlar (qw-1, qw-2) ilk sprinte taşınmalı — erken başarı motivasyonu sağlar.",
          confidence: "medium",
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
        { id: "ev-1", analyzer: "karmaşılık-analizörü", finding_type: "complexity", severity: "high", confidence: 1.0, category: "cyclomatic_complexity", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "Yüksek karmaşıklık: process_user (Döngüsel Karmaşıklık=41)", tags: ["complexity", "E"], metrics: { complexity: 41, rank: "E" } },
        { id: "ev-2", analyzer: "kod-kalitesi-motoru", finding_type: "code_quality", severity: "medium", confidence: 0.8, category: "long_method", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "Uzun metod: process_user", tags: ["long_method", "high"] },
        { id: "ev-3", analyzer: "metrik-motoru", finding_type: "metric", severity: "medium", confidence: 1.0, category: "large_file", file_path: "src/services/user_service.py", message: "Büyük dosya (650 SLOC)", tags: ["large_file"], metrics: { sloc: 650 } },
        { id: "ev-4", analyzer: "import-analizörü", finding_type: "import", severity: "high", confidence: 1.0, category: "circular_import", message: "Döngüsel import: auth → user → auth", tags: ["circular_import"] },
        { id: "ev-5", analyzer: "mimari-inceleme-motoru", finding_type: "architecture", severity: "medium", confidence: 0.7, category: "high_coupling", file_path: "src/services/user_service.py", message: "Yüksek bağlılık (0.85)", tags: ["high_coupling"] },
        { id: "ev-6", analyzer: "import-analizörü", finding_type: "import", severity: "low", confidence: 0.9, category: "unused_import", file_path: "src/api/users.py", message: "Kullanılmayan import: os", tags: ["unused_import", "dead_code"] },
        { id: "ev-7", analyzer: "güvenlik-motoru", finding_type: "security", severity: "critical", confidence: 0.9, category: "hardcoded_password", file_path: "src/config.py", line: 10, message: "Sabit kodlanmış şifre", tags: ["hardcoded_password"] },
        { id: "ev-8", analyzer: "test-kapsamı-analizörü", finding_type: "test", severity: "medium", confidence: 0.9, category: "low_coverage", message: "Düşük test kapsamı: %35", tags: ["testing", "low_coverage"], metrics: { estimated_coverage: 35 } },
      ],
      relationships: [],
      statistics: { total_evidence: 8, by_type_counts: { complexity: 1, code_quality: 1, metric: 1, import: 2, architecture: 1, security: 1, test: 1 }, by_severity_counts: { critical: 1, high: 2, medium: 3, low: 2 }, by_analyzer_counts: { "karmaşılık-analizörü": 1, "kod-kalitesi-motoru": 1, "metrik-motoru": 1, "import-analizörü": 2, "mimari-inceleme-motoru": 1, "güvenlik-motoru": 1, "test-kapsamı-analizörü": 1 } },
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
            { target_step_id: "step-1", challenge_type: "too_aggressive", description: "Adım 1 çok agresif — 5 gün ve 2 geliştirici. Facade deseni ile kademeli geçiş daha güvenli olabilir.", alternative: "Önce Facade + Delegate uygula, ardından kademeli olarak parçala." },
            { target_step_id: "step-3", challenge_type: "insufficient_evidence", description: "Adım 3'ün adım 1'e bağımlılığı var ama her ikisi de yüksek riskli. Paralel değil sıralı yapılmalı.", alternative: "Adım 1 tamamlandıktan sonra adım 3'ü başlat." },
          ]
        : [],
      recommendations: useLLM
        ? [
            { title: "Hızlı kazançları öne al", description: "qw-1 ve qw-2'yi ilk sprint'e taşı — erken başarı motivasyon sağlar.", priority: "medium", confidence: "high", rationale: "Düşük risk, yüksek görünürlük.", linked_step_ids: ["step-4"], linked_root_cause_ids: ["rc-4"] },
            { title: "Test kapsamını artır", description: "Refactor öncesi test kapsamı %35'ten en az %60'a çıkarılmalı — güvenlik ağı sağlar.", priority: "high", confidence: "high", rationale: "Mevcut düşük kapsam refactor riskini artırıyor.", linked_step_ids: ["step-1"], linked_root_cause_ids: [] },
          ]
        : [],
      model_info: useLLM
        ? { provider: llmProvider, model: llmModel, temperature: 0.3 }
        : { provider: "offline", model: "deterministic-fallback" },
      prompt_tokens: useLLM ? 2847 : 0,
      completion_tokens: useLLM ? 1923 : 0,
      statistics: { total_sections: reviewSections.length, total_challenges: useLLM ? 2 : 0, offline: !useLLM },
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
