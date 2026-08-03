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
  ai_review: { health_score: Record<string, number | string>; security_review: Record<string, unknown> };
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
  let owner: string, name: string;
  if (repoUrl.startsWith("local://")) {
    owner = "local";
    name = repoUrl.replace(/^local:\/\//, "").split("/")[0] || "repo";
  } else {
    owner = repoUrl.split("/").slice(-2)[0] || "example";
    name = repoUrl.split("/").slice(-1)[0]?.replace(".git", "") || "repo";
  }
  const h = hashString(repoUrl);
  const useLLM = options?.useLLM ?? false;
  const llmProvider = options?.llmProvider || "offline";
  const llmModel = options?.llmModel || "deterministic-fallback";

  // Vary scores deterministically by URL so different repos feel different.
  const overall = Number(seeded(h, 58, 88).toFixed(1));
  const grade = overall >= 85 ? "A" : overall >= 70 ? "B" : overall >= 55 ? "C" : overall >= 40 ? "D" : "F";
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

  // --- LLM review sections â€” written like a senior architect talking,
  // NOT restating metrics. Each section gives genuine insight, practical
  // advice, and context that the raw data alone doesn't provide.
  const reviewSections = useLLM
    ? [
        {
          section_type: "executive_summary",
          title: "Ã–zet",
          body: `Bu depoyu inceledim ve aÃ§Ä±kÃ§asÄ± temel mimari saÄŸlam gÃ¶rÃ¼nÃ¼yor ama birkaÃ§ noktada teknik borÃ§ biriktirmiÅŸsiniz. En belirgin sorun: UserService sÄ±nÄ±fÄ± her ÅŸeyi yapÄ±yor â€” kullanÄ±cÄ± oluÅŸturma, kimlik doÄŸrulama, bildirim gÃ¶nderme, veritabanÄ± sorgularÄ±... Bu sÄ±nÄ±f bÃ¼yÃ¼dÃ¼kÃ§e deÄŸiÅŸtirmek gittikÃ§e zorlaÅŸÄ±yor ve her dokunuÅŸ baÅŸka bir ÅŸeyi kÄ±rma riski taÅŸÄ±yor. Ä°yi haber: bu dÃ¼zeltilebilir ve Ã¶nÃ¼nÃ¼zde net bir yol haritasÄ± var. Ã–nemli olan paralel deÄŸil, sÄ±ralÄ± ilerlemek â€” Ã¶nce en kritik baÄŸÄ±mlÄ±lÄ±ÄŸÄ± (UserService) Ã§Ã¶zÃ¼n, gerisi daha kolay gelecek.`,
          confidence: "high",
        },
        {
          section_type: "top_root_causes",
          title: "AsÄ±l Sorunlar",
          body: `Åunu fark ettim: buradaki sorunlar birbirinden baÄŸÄ±msÄ±z deÄŸil, zincirleme etkiliyorlar. UserService'in Ã§ok bÃ¼yÃ¼mesi (TanrÄ± SÄ±nÄ±f anti-deseni) doÄŸal olarak sÄ±kÄ± baÄŸlÄ±lÄ±ÄŸa yol aÃ§Ä±yor â€” Ã§Ã¼nkÃ¼ her ÅŸey bu sÄ±nÄ±fa baÄŸÄ±mlÄ±. DÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±k (auth â†” user) ise muhtemelen "ÅŸunu da buradan Ã§aÄŸÄ±rayÄ±m" yaklaÅŸÄ±mÄ±nÄ±n sonucu. Yani kÃ¶k neden tek aslÄ±nda: sorumluluklarÄ±n iyi ayrÄ±lmamÄ±ÅŸ olmasÄ±. Bunu Ã§Ã¶zerseniz, diÄŸer sorunlar da bÃ¼yÃ¼k Ã¶lÃ§Ã¼de kendiliÄŸinden dÃ¼zelecek.`,
          confidence: "high",
        },
        {
          section_type: "highest_roi_refactoring",
          title: "En DeÄŸerli DÃ¼zeltme",
          body: "Ä°lginÃ§tir, en yÃ¼ksek getirili dÃ¼zeltme en kolayÄ±: loglama kodunu tek bir yere toplamak. Åu anda log formatÄ±nÄ± deÄŸiÅŸtirmek istediÄŸinizde 8 dosyayÄ± aÃ§manÄ±z gerekiyor â€” bu sadece zaman kaybÄ± deÄŸil, birini atladÄ±ÄŸÄ±nÄ±zda tutarsÄ±z loglar elde ediyorsunuz. 4 saatlik bir iÅŸ ve getirisi Ã§ok yÃ¼ksek. Bunu ilk sprint'e taÅŸÄ±yÄ±n â€” ekibin morali iÃ§in iyi bir baÅŸlangÄ±Ã§ olur ve gÃ¼ven oluÅŸturur.",
          confidence: "high",
        },
        {
          section_type: "architecture_review",
          title: "Mimari DeÄŸerlendirmem",
          body: `DÃ¼rÃ¼st olmak gerekirse, bu depo "Ã§alÄ±ÅŸÄ±yor ama bÃ¼yÃ¼rken acÄ± Ã§ekecek" kategorisinde. Katman ayrÄ±mÄ± kÄ±smen var ama UserService bir "kara delik" oluÅŸturmuÅŸ â€” her ÅŸey oraya Ã§ekiliyor. DÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±k (auth â†” user) Ã¶zellikle tehlikeli Ã§Ã¼nkÃ¼ test yazmayÄ± zorlaÅŸtÄ±rÄ±yor: auth'Ä± test etmek iÃ§in user'a, user'Ä± test etmek iÃ§in auth'a ihtiyaÃ§ var. Bu birim testleri imkÃ¢nsÄ±z deÄŸil ama Ã§ok kÄ±rÄ±lgan hale getiriyor. BaÄŸÄ±mlÄ±lÄ±k enjeksiyonu (DI) tamamen eksik â€” servisler doÄŸrudan veritabanÄ±na ulaÅŸÄ±yor. Bu, ilerde veritabanÄ±nÄ± deÄŸiÅŸtirmek istediÄŸinizde bÃ¼yÃ¼k acÄ± verecek. Tavsiyem: Facade deseniyle baÅŸlayÄ±n â€” UserService'i olduÄŸu gibi bÄ±rakÄ±n ama yeni kodlarÄ± ayrÄ± servislere yazÄ±n. Zamanla eski kod da gÃ¶Ã§ eder.`,
          confidence: "high",
        },
        {
          section_type: "risk_assessment",
          title: "Riskleri AÃ§Ä±kÃ§a PaylaÅŸÄ±yorum",
          body: "UserService'i parÃ§alamak riskli bir iÅŸ â€” 40 saat, 2 geliÅŸtirici ve kritik yollarÄ± etkiliyor. Bu yÃ¼zden 'big bang' yaklaÅŸÄ±mÄ± yerine kademeli geÃ§iÅŸ ÅŸart. Ã–nce bir Facade oluÅŸturun, yeni servisleri arka planda yazÄ±n, eski UserService'i facade'a yÃ¶nlendirin ve sonra kademeli olarak iÃ§ini boÅŸaltÄ±n. DÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±ÄŸÄ± kÄ±rmak da benzer ÅŸekilde riskli ama ÅŸaÅŸÄ±rtÄ±cÄ± derecede hÄ±zlÄ± sonuÃ§ veriyor â€” ortak mantÄ±ÄŸÄ± yeni bir modÃ¼le Ã§ekmek genelde bir gÃ¼n sÃ¼rÃ¼yor. Test kapsamÄ±nÄ±n %35 olmasÄ± beni endiÅŸelendiriyor: bu kadar dÃ¼ÅŸÃ¼k kapsamda bÃ¼yÃ¼k refactor yapmak yÃ¼rÃ¼rken uÃ§urumun kenarÄ±nda yÃ¼rÃ¼mek gibi. Ã–nce testleri yazÄ±n, sonra refactor yapÄ±n.",
          confidence: "medium",
        },
        {
          section_type: "long_term_vision",
          title: "Ä°leriye DÃ¶nÃ¼k DÃ¼ÅŸÃ¼ncelerim",
          body: `Bu depoyu 6 ay sonra 'bakmasÄ± keyifli bir kod tabanÄ±' haline getirebilirsiniz ama disiplinli olmanÄ±z gerek. Her sprint'te bir kÃ¶k nedeni ele alÄ±n â€” paralel deÄŸil, sÄ±ralÄ±. CI/CD'ye mimari kalite kapÄ±sÄ± ekleyin: dÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±k otomatik engellensin, karmaÅŸÄ±klÄ±k eÅŸiÄŸi aÅŸÄ±ldÄ±ÄŸÄ±nda uyarÄ± verilsin. Test kapsamÄ±nÄ± %35'ten en az %60'a Ã§Ä±karÄ±n â€” bu bir hedef deÄŸil, refactor iÃ§in gÃ¼venlik aÄŸÄ±. BaÄŸÄ±mlÄ±lÄ±k enjeksiyonu standart hale gelmeli. Ve en Ã¶nemlisi: yeni Ã¶zellikler eklerken 'UserService'e koyalÄ±m' demeyin â€” her yeni sorumluluk iÃ§in yeni bir servis oluÅŸturun. Bu disiplin 3-4 sprint sonra alÄ±ÅŸkanlÄ±k haline gelecek.`,
          confidence: "low",
        },
        {
          section_type: "challenge",
          title: "Plana ItirazlarÄ±m",
          body: `Plan genel olarak mantÄ±klÄ± ama birkaÃ§ noktada itirazÄ±m var. Birincisi: AdÄ±m 1 (UserService parÃ§alama) Ã§ok agresif. 5 gÃ¼nde 2 geliÅŸtirici ile 'split God Class' demek, o sÄ±rada baÅŸka hiÃ§bir Ã¶zellik geliÅŸtirilemeyecek demek. Bunun yerine Facade + Delegate ile baÅŸlayÄ±n â€” geriye dÃ¶nÃ¼k uyumlu, riski dÃ¼ÅŸÃ¼k. Ä°kincisi: hÄ±zlÄ± kazanÃ§lar neden 3. sprint'te? OnlarÄ± 1. sprint'e taÅŸÄ±yÄ±n â€” ekibin 'bir ÅŸeyi tamamladÄ±k' hissi yaÅŸamasÄ± motivasyon iÃ§in kritik. ÃœÃ§Ã¼ncÃ¼sÃ¼: test kapsamÄ± %35 iken bÃ¼yÃ¼k refactor yapmak Ã§ok riskli. Test yazmadan baÅŸlamayÄ±n.`,
          confidence: "medium",
        },
        {
          section_type: "recommendation",
          title: "Pratik Tavsiyelerim",
          body: "BunlarÄ± sÄ±rayla yapÄ±n:\n1. Ã–nce loglama yardÄ±mcÄ± fonksiyonunu Ã§Ä±karÄ±n (4 saat, dÃ¼ÅŸÃ¼k risk)\n2. KullanÄ±lmayan import'larÄ± temizleyin (15 dakika, anÄ±nda sonuÃ§)\n3. UserService iÃ§in test yazÄ±n â€” en azÄ±ndan process_user metodunu\n4. Facade deseni uygulayÄ±n, yeni servisleri arkadan yazÄ±n\n5. DÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±ÄŸÄ± kÄ±rÄ±n (ortak mantÄ±ÄŸÄ± Ã§Ä±kar)\n6. Repository arayÃ¼zÃ¼ tanÄ±mlayÄ±n (DI iÃ§in)\nBu sÄ±ra Ã¶nemli: dÃ¼ÅŸÃ¼k riskli iÅŸlerle baÅŸlayÄ±n, gÃ¼ven oluÅŸturun, sonra bÃ¼yÃ¼k refactor'a geÃ§in.",
          confidence: "high",
        },
      ]
    : [
        {
          section_type: "executive_summary",
          title: "YÃ¶netici Ã–zeti",
          body: `KÃ¶k neden analizi 4 mimari sorun tespit etti (ortalama gÃ¼ven %80). MÃ¼hendislik planÄ± 3 sprint'te 4 adÄ±m Ã¶neriyor, ~92 saat. 2 hÄ±zlÄ± kazanÃ§ mevcut. Genel saÄŸlÄ±k: ${overall.toFixed(1)}/100 (${grade}).`,
          confidence: "high",
        },
        {
          section_type: "top_root_causes",
          title: "En Ã–nemli KÃ¶k Nedenler",
          body: "- TanrÄ± SÄ±nÄ±f: UserService (yÃ¼ksek, %85)\n- DÃ¶ngÃ¼sel BaÄŸÄ±mlÄ±lÄ±k: auth â†” user (yÃ¼ksek, %92)\n- SÄ±kÄ± BaÄŸlÄ±lÄ±k: VeritabanÄ± katmanÄ± (orta, %75)\n- SaÃ§ma DeÄŸiÅŸiklik: Loglama (dÃ¼ÅŸÃ¼k, %68%)",
          confidence: "high",
        },
        {
          section_type: "highest_roi_refactoring",
          title: "En YÃ¼ksek Getirili Yeniden DÃ¼zenleme",
          body: "AdÄ±m 4: Ortak loglama yardÄ±mcÄ± fonksiyonu Ã§Ä±kar\nROI: 5.42\nÃ–ncelik: dÃ¼ÅŸÃ¼k\nTahmini sÃ¼re: 4 saat",
          confidence: "high",
        },
        {
          section_type: "long_term_vision",
          title: "Uzun Vadeli Vizyon",
          body: "Ã–nÃ¼mÃ¼zdeki 6 ayda bÃ¼yÃ¼k sÄ±nÄ±flarÄ± tek sorumluluklu bileÅŸenlere ayÄ±rÄ±n.",
          confidence: "low",
        },
      ];

  return {
    id: `demo-${h.toString(36)}`,
    status: "completed",
    repository: { url: repoUrl, owner, name, host: repoUrl.startsWith("local://") ? "local" : "github.com", access: repoUrl.startsWith("local://") ? "private" : "public" },
    repository_metadata: {
      name, owner,
      description: `${owner}/${name} â€” AI YazÄ±lÄ±m MimarÄ± tarafÄ±ndan analiz edildi`,
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
          title: `TanrÄ± SÄ±nÄ±f: ${pick(["UserService", "OrderManager", "ApiClient", "DataProcessor"], h)}`,
          severity: "high",
          confidence: 0.85,
          description: "Tek bir sÄ±nÄ±f Ã§ok sayÄ±da farklÄ± sorumluluÄŸu Ã¼stlenmiÅŸ â€” kullanÄ±cÄ± iÅŸ mantÄ±ÄŸÄ±, veri eriÅŸimi, bildirimler ve doÄŸrulama hepsi aynÄ± sÄ±nÄ±fta. Bu, sÄ±nÄ±fÄ±n anlaÅŸÄ±lmasÄ±nÄ±, test edilmesini ve bakÄ±mÄ±nÄ± zorlaÅŸtÄ±rÄ±r.",
          technical_rationale: "3 farklÄ± analizÃ¶rden 4 ayrÄ± belirti tespit edildi: yÃ¼ksek dÃ¶ngÃ¼sel karmaÅŸÄ±klÄ±k (CC=41), uzun metod (process_user), bÃ¼yÃ¼k dosya (650 SLOC) ve dÃ¼ÅŸÃ¼k kohesiyon.",
          root_cause_origin: "Zamanla organik bÃ¼yÃ¼me â€” yeni Ã¶zellikler eklendikÃ§e tek sÄ±nÄ±fa yÄ±ÄŸÄ±lmÄ±ÅŸ, refactor yapÄ±lmamÄ±ÅŸ.",
          affected_files: ["src/services/user_service.py", "src/api/user_routes.py"],
          affected_classes: ["UserService"],
          affected_modules: ["services.user"],
          evidence_count: 8,
          evidence_links: [
            { evidence_id: "ev-1", contribution: 0.9, reason: "YÃ¼ksek karmaÅŸÄ±klÄ±k" },
            { evidence_id: "ev-2", contribution: 0.8, reason: "Uzun metod" },
            { evidence_id: "ev-3", contribution: 0.7, reason: "BÃ¼yÃ¼k dosya" },
          ],
        },
        {
          id: "rc-2",
          category: "circular_dependency",
          title: "DÃ¶ngÃ¼sel BaÄŸÄ±mlÄ±lÄ±k: auth â†” user",
          severity: "high",
          confidence: 0.92,
          description: "auth modÃ¼lÃ¼ user modÃ¼lÃ¼nÃ¼, user modÃ¼lÃ¼ de auth modÃ¼lÃ¼nÃ¼ iÃ§e aktarÄ±yor. Bu dÃ¶ngÃ¼, modÃ¼llerin baÄŸÄ±msÄ±z test edilmesini engeller ve baÅŸlatma sÄ±rasÄ±nda hatalara yol aÃ§abilir.",
          technical_rationale: "Import grafiÄŸinde doÄŸrudan dÃ¶ngÃ¼ tespit edildi: auth â†’ user â†’ auth.",
          root_cause_origin: "ModÃ¼ller import yÃ¶nÃ¼ kontrol edilmeden eklenmiÅŸ. Ortak mantÄ±k alt seviye bir modÃ¼le Ã§Ä±karÄ±lmamÄ±ÅŸ.",
          affected_files: ["src/auth/service.py", "src/user/service.py"],
          affected_modules: ["auth", "user"],
          evidence_count: 3,
          evidence_links: [{ evidence_id: "ev-4", contribution: 1.0, reason: "DoÄŸrudan dÃ¶ngÃ¼" }],
        },
        {
          id: "rc-3",
          category: "tight_coupling",
          title: "SÄ±kÄ± BaÄŸlÄ±lÄ±k: VeritabanÄ± KatmanÄ±",
          severity: "medium",
          confidence: 0.75,
          description: "Birden fazla servis doÄŸrudan veritabanÄ± istemcisine baÄŸlÄ±. VeritabanÄ± uygulamasÄ± deÄŸiÅŸirse, tÃ¼m servislerin gÃ¼ncellenmesi gerekiyor. Test iÃ§in mock veritabanÄ± kullanmak zor.",
          technical_rationale: "Graf analizi aÅŸÄ±rÄ± baÄŸÄ±mlÄ±lÄ±k kenarlarÄ± gÃ¶steriyor â€” servisler arayÃ¼z (interface) yerine somut DB istemcisine baÄŸlÄ±.",
          root_cause_origin: "Soyutlama (abstraction) yerine doÄŸrudan baÄŸÄ±mlÄ±lÄ±k kullanÄ±lmÄ±ÅŸ. BaÄŸÄ±mlÄ±lÄ±k enjeksiyonu (DI) uygulanmamÄ±ÅŸ.",
          affected_files: ["src/services/user_service.py", "src/services/order_service.py"],
          affected_modules: ["services"],
          evidence_count: 5,
          evidence_links: [{ evidence_id: "ev-5", contribution: 0.8, reason: "YÃ¼ksek baÄŸlÄ±lÄ±k Ã¶lÃ§Ã¼mÃ¼" }],
        },
        {
          id: "rc-4",
          category: "shotgun_surgery",
          title: "SaÃ§ma DeÄŸiÅŸiklik: Loglama",
          severity: "low",
          confidence: 0.68,
          description: "Loglama formatÄ± deÄŸiÅŸtiÄŸinde 8 farklÄ± dosyada deÄŸiÅŸiklik yapmak gerekiyor. Bu, merkezi bir loglama yardÄ±mcÄ± fonksiyonu olmamasÄ±ndan kaynaklanÄ±yor.",
          technical_rationale: "AynÄ± belirti 8 farklÄ± dosyada tespit edildi â€” copy-paste ile yayÄ±lmÄ±ÅŸ.",
          root_cause_origin: "Ortak bir yardÄ±mcÄ± fonksiyon Ã§Ä±karÄ±lmadan copy-paste yapÄ±lmÄ±ÅŸ.",
          affected_files: ["src/api/users.py", "src/api/orders.py", "src/api/products.py", "src/api/payments.py", "src/services/user_service.py"],
          affected_modules: ["api", "services"],
          evidence_count: 8,
          evidence_links: [{ evidence_id: "ev-6", contribution: 0.7, reason: "Sistemik desen" }],
        },
      ],
      relationships: [{ source_root_cause_id: "rc-1", target_root_cause_id: "rc-3", relationship_type: "causes", detail: "TanrÄ± SÄ±nÄ±f, sÄ±kÄ± baÄŸlÄ±lÄ±ÄŸa neden oluyor" }],
      statistics: { total_root_causes: 4, average_confidence: 0.80, by_category_counts: { god_class: 1, circular_dependency: 1, tight_coupling: 1, shotgun_surgery: 1 }, by_severity_counts: { high: 2, medium: 1, low: 1 } },
      // Root Cause Validation: each RC has analyzer_consensus (how many independent
      // analyzers support it) and conflicting_evidence (if any analyzer disagrees).
      validation: {
        "rc-1": { analyzer_consensus: 3, supporting_analyzers: ["karmaÅŸÄ±lÄ±k-analizÃ¶rÃ¼", "kod-kalitesi-motoru", "metrik-motoru"], conflicting_evidence: [], validation_status: "verified", min_analyzers_required: 2 },
        "rc-2": { analyzer_consensus: 2, supporting_analyzers: ["import-analizÃ¶rÃ¼", "mimari-inceleme-motoru"], conflicting_evidence: [], validation_status: "verified", min_analyzers_required: 2 },
        "rc-3": { analyzer_consensus: 3, supporting_analyzers: ["mimari-inceleme-motoru", "karmaÅŸÄ±lÄ±k-analizÃ¶rÃ¼", "baÄŸÄ±mlÄ±lÄ±k-analizÃ¶rÃ¼"], conflicting_evidence: [], validation_status: "verified", min_analyzers_required: 2 },
        "rc-4": { analyzer_consensus: 2, supporting_analyzers: ["import-analizÃ¶rÃ¼", "loglama-tutarlÄ±lÄ±k-analizÃ¶rÃ¼"], conflicting_evidence: [], validation_status: "verified", min_analyzers_required: 2 },
      },
    },
    engineering_plan: {
      steps: [
        {
          id: "step-1",
          step_number: 1,
          title: "TanrÄ± SÄ±nÄ±f'Ä± parÃ§alara ayÄ±r",
          technical_description: "UserService'i auth, profile, notifications ve settings olmak Ã¼zere 4 ayrÄ± servise bÃ¶l. Her servis tek bir sorumluluÄŸa sahip olmalÄ±.",
          root_cause_id: "rc-1",
          root_cause_category: "god_class",
          priority: "high",
          roi: 2.25,
          estimate: { hours: 40, display: "5 gÃ¼n", developers: 2, confidence: 0.5 },
          risk: "high",
          risk_reason: "BÃ¼yÃ¼k Ã¶lÃ§ekli refactor â€” kritik yollarÄ± etkiliyor.",
          expected_outcomes: ["BakÄ±m yapÄ±labilirlik +%90", "Test edilebilirlik +%80"],
          prerequisites: [],
          alternatives: [
            { id: "alt-1", name: "SÄ±nÄ±f Ã‡Ä±karÄ±mÄ±", description: "OdaklÄ± sÄ±nÄ±flara bÃ¶l.", advantages: ["Net sorumluluklar", "Kolay test"], disadvantages: ["Daha fazla dosya"], risk: "medium", maintenance_cost: "low", performance_impact: "neutral", migration_difficulty: "medium" },
            { id: "alt-2", name: "Facade + Yetkilendir", description: "Facade olarak kal, iÃ§ten yetkilendir.", advantages: ["Geriye dÃ¶nÃ¼k uyumlu", "Kademeli geÃ§iÅŸ"], disadvantages: ["Facade hala var"], risk: "low", maintenance_cost: "medium", performance_impact: "neutral", migration_difficulty: "low" },
          ],
          affected_files: ["src/services/user_service.py"],
          verified_status: "verified",
          evidence_chain: ["ev-1", "ev-2", "ev-3", "ev-8"],
        },
        {
          id: "step-2",
          step_number: 2,
          title: "DÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±ÄŸÄ± kÄ±r: auth â†” user",
          technical_description: "Ortak mantÄ±ÄŸÄ± yeni bir alt seviye modÃ¼le taÅŸÄ± (Ã¶rn. shared/auth_utils). BÃ¶ylece auth ve user modÃ¼lleri bu modÃ¼le baÄŸÄ±mlÄ± olur ama birbirine deÄŸil.",
          root_cause_id: "rc-2",
          root_cause_category: "circular_dependency",
          priority: "high",
          roi: 3.54,
          estimate: { hours: 24, display: "3 gÃ¼n", developers: 1, confidence: 0.5 },
          risk: "high",
          risk_reason: "DeÄŸiÅŸiklikler kritik yollarÄ± etkiliyor.",
          expected_outcomes: ["BakÄ±m yapÄ±labilirlik +%85", "Test edilebilirlik +%80"],
          prerequisites: ["step-1"],
          alternatives: [],
          affected_files: ["src/auth/service.py", "src/user/service.py"],
          verified_status: "verified",
          evidence_chain: ["ev-4", "ev-5", "ev-8"],
        },
        {
          id: "step-3",
          step_number: 3,
          title: "VeritabanÄ± eriÅŸimi iÃ§in repository arayÃ¼zÃ¼ tanÄ±mla",
          technical_description: "Soyut bir repository arayÃ¼zÃ¼ (interface) oluÅŸtur ve baÄŸÄ±mlÄ±lÄ±k enjeksiyonu (DI) ile kullan. Servisler somut DB istemcisine deÄŸil arayÃ¼ze baÄŸÄ±mlÄ± olur.",
          root_cause_id: "rc-3",
          root_cause_category: "tight_coupling",
          priority: "medium",
          roi: 1.88,
          estimate: { hours: 24, display: "3 gÃ¼n", developers: 1, confidence: 0.5 },
          risk: "medium",
          risk_reason: "Orta Ã¶lÃ§ekli deÄŸiÅŸiklikler.",
          expected_outcomes: ["Test edilebilirlik +%70", "BakÄ±m yapÄ±labilirlik +%75"],
          prerequisites: ["step-1"],
          alternatives: [],
          affected_files: ["src/services/user_service.py", "src/services/order_service.py"],
          verified_status: "verified",
          evidence_chain: ["ev-5", "ev-1", "ev-10"],
        },
        {
          id: "step-4",
          step_number: 4,
          title: "Ortak loglama yardÄ±mcÄ± fonksiyonu Ã§Ä±kar",
          technical_description: "Merkezi bir loglama sarmalayÄ±cÄ± (wrapper) oluÅŸtur. TÃ¼m dosyalar bunu kullansÄ±n. Loglama formatÄ± tek yerden yÃ¶netilsin.",
          root_cause_id: "rc-4",
          root_cause_category: "shotgun_surgery",
          priority: "low",
          roi: 5.42,
          estimate: { hours: 4, display: "4 saat", developers: 1, confidence: 0.7 },
          risk: "low",
          risk_reason: "DÃ¼ÅŸÃ¼k risk â€” izole deÄŸiÅŸiklikler.",
          expected_outcomes: ["Teknik borÃ§ azaldÄ±", "TutarlÄ± loglama"],
          prerequisites: [],
          alternatives: [],
          affected_files: ["src/api/users.py", "src/api/orders.py"],
          verified_status: "verified",
          evidence_chain: ["ev-6", "ev-9"],
        },
      ],
      roadmap: {
        sprints: [
          { sprint_number: 1, title: "Sprint 1: Kritik Refactor", step_ids: ["step-1"], total_estimated_hours: 40, goals: ["TanrÄ± SÄ±nÄ±f'Ä± parÃ§ala"], steps: [] },
          { sprint_number: 2, title: "Sprint 2: Mimari DÃ¼zeltmeler", step_ids: ["step-2", "step-3"], total_estimated_hours: 48, goals: ["DÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±ÄŸÄ± kÄ±r", "Repository arayÃ¼zÃ¼ tanÄ±mla"], steps: [] },
          { sprint_number: 3, title: "Sprint 3: Temizlik ve BakÄ±m", step_ids: ["step-4"], total_estimated_hours: 4, goals: ["Ortak loglama Ã§Ä±kar"], steps: [] },
        ],
        total_estimated_hours: 92,
        total_steps: 4,
        summary: "3 sprint, 4 adÄ±m, ~92 saat toplam.",
      },
      quick_wins: [
        { id: "qw-1", title: "Ortak loglama yardÄ±mcÄ± fonksiyonu Ã§Ä±kar", description: "Merkezi loglama sarmalayÄ±cÄ± oluÅŸtur.", effort_minutes: 240, benefit: "Fayda skoru: 65/100", planning_step_id: "step-4", root_cause_id: "rc-4" },
        { id: "qw-2", title: "KullanÄ±lmayan import'larÄ± kaldÄ±r", description: "5 kullanÄ±lmayan import tespit edildi.", effort_minutes: 15, benefit: "HÄ±zlÄ± dÃ¼zeltme: Ã¶lÃ¼ kod", planning_step_id: null, root_cause_id: null },
      ],
      blockers: [{ id: "blk-1", blocker_root_cause_id: "rc-1", blocked_root_cause_ids: ["rc-3"], reason: "TanrÄ± SÄ±nÄ±f Ã¶nce ele alÄ±nmalÄ±.", planning_step_id: "step-1" }],
      statistics: { total_steps: 4, total_quick_wins: 2, total_blockers: 1, average_roi: 3.27, priority_counts: { high: 2, medium: 1, low: 1 }, risk_counts: { high: 2, medium: 1, low: 1 } },
    },
    evidence: {
      evidence: [
        { id: "ev-1", analyzer: "karmaÅŸÄ±lÄ±k-analizÃ¶rÃ¼", finding_type: "complexity", severity: "high", confidence: 1.0, category: "cyclomatic_complexity", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "YÃ¼ksek karmaÅŸÄ±klÄ±k: process_user (DÃ¶ngÃ¼sel KarmaÅŸÄ±klÄ±k=41)", tags: ["complexity", "E"], metrics: { complexity: 41, rank: "E" }, validation_status: "pass", validated_by: ["karmaÅŸÄ±lÄ±k-analizÃ¶rÃ¼", "metrik-motoru"] },
        { id: "ev-2", analyzer: "kod-kalitesi-motoru", finding_type: "code_quality", severity: "medium", confidence: 0.8, category: "long_method", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "Uzun metod: process_user", tags: ["long_method", "high"], validation_status: "pass", validated_by: ["kod-kalitesi-motoru", "karmaÅŸÄ±lÄ±k-analizÃ¶rÃ¼"] },
        { id: "ev-3", analyzer: "metrik-motoru", finding_type: "metric", severity: "medium", confidence: 1.0, category: "large_file", file_path: "src/services/user_service.py", message: "BÃ¼yÃ¼k dosya (650 SLOC)", tags: ["large_file"], metrics: { sloc: 650 }, validation_status: "pass", validated_by: ["metrik-motoru"] },
        { id: "ev-4", analyzer: "import-analizÃ¶rÃ¼", finding_type: "import", severity: "high", confidence: 1.0, category: "circular_import", file_path: "src/auth/service.py", related_files: ["src/auth/service.py", "src/user/service.py"], message: "DÃ¶ngÃ¼sel import: auth â†’ user â†’ auth", tags: ["circular_import"], validation_status: "pass", validated_by: ["import-analizÃ¶rÃ¼", "mimari-inceleme-motoru"] },
        { id: "ev-5", analyzer: "mimari-inceleme-motoru", finding_type: "architecture", severity: "medium", confidence: 0.85, category: "high_coupling", file_path: "src/services/user_service.py", message: "YÃ¼ksek baÄŸlÄ±lÄ±k (0.85)", tags: ["high_coupling"], validation_status: "pass", validated_by: ["mimari-inceleme-motoru", "karmaÅŸÄ±lÄ±k-analizÃ¶rÃ¼"] },
        { id: "ev-6", analyzer: "import-analizÃ¶rÃ¼", finding_type: "import", severity: "low", confidence: 0.9, category: "unused_import", file_path: "src/api/users.py", message: "KullanÄ±lmayan import: os", tags: ["unused_import", "dead_code"], validation_status: "pass", validated_by: ["import-analizÃ¶rÃ¼"] },
        { id: "ev-7", analyzer: "gÃ¼venlik-motoru", finding_type: "security", severity: "critical", confidence: 0.9, category: "hardcoded_password", file_path: "src/config.py", line: 10, message: "Sabit kodlanmÄ±ÅŸ ÅŸifre", tags: ["hardcoded_password"], validation_status: "pass", validated_by: ["gÃ¼venlik-motoru", "kod-kalitesi-motoru"] },
        { id: "ev-8", analyzer: "test-kapsamÄ±-analizÃ¶rÃ¼", finding_type: "test", severity: "medium", confidence: 0.9, category: "low_coverage", file_path: "tests/test_user_service.py", message: "DÃ¼ÅŸÃ¼k test kapsamÄ±: %35", tags: ["testing", "low_coverage"], metrics: { estimated_coverage: 35 }, validation_status: "pass", validated_by: ["test-kapsamÄ±-analizÃ¶rÃ¼", "kod-kalitesi-motoru"] },
        { id: "ev-9", analyzer: "loglama-tutarlÄ±lÄ±k-analizÃ¶rÃ¼", finding_type: "duplication", severity: "low", confidence: 0.95, category: "logging_spread", file_path: "src/api/orders.py", related_files: ["src/api/users.py", "src/api/orders.py", "src/api/products.py", "src/api/payments.py"], message: "Loglama formatÄ± 8 dosyada tekrar ediyor", tags: ["logging", "duplication"], metrics: { affected_files: 8 }, validation_status: "pass", validated_by: ["loglama-tutarlÄ±lÄ±k-analizÃ¶rÃ¼", "import-analizÃ¶rÃ¼"] },
        { id: "ev-10", analyzer: "baÄŸÄ±mlÄ±lÄ±k-analizÃ¶rÃ¼", finding_type: "architecture", severity: "medium", confidence: 0.9, category: "concrete_db_dependency", file_path: "src/services/order_service.py", related_files: ["src/services/user_service.py", "src/services/order_service.py"], message: "Servisler repository arayÃ¼zÃ¼ yerine somut DB client kullanÄ±yor", tags: ["dependency_inversion", "high_coupling"], metrics: { concrete_db_clients: 2 }, validation_status: "pass", validated_by: ["baÄŸÄ±mlÄ±lÄ±k-analizÃ¶rÃ¼", "mimari-inceleme-motoru"] },
      ],
      relationships: [],
      statistics: { total_evidence: 10, passed: 10, warning: 0, failed: 0, by_type_counts: { complexity: 1, code_quality: 1, metric: 1, import: 2, architecture: 2, duplication: 1, security: 1, test: 1 }, by_severity_counts: { critical: 1, high: 2, medium: 4, low: 3 }, by_analyzer_counts: { "karmaÅŸÄ±lÄ±k-analizÃ¶rÃ¼": 1, "kod-kalitesi-motoru": 1, "metrik-motoru": 1, "import-analizÃ¶rÃ¼": 2, "mimari-inceleme-motoru": 1, "gÃ¼venlik-motoru": 1, "test-kapsamÄ±-analizÃ¶rÃ¼": 1, "loglama-tutarlÄ±lÄ±k-analizÃ¶rÃ¼": 1, "baÄŸÄ±mlÄ±lÄ±k-analizÃ¶rÃ¼": 1 } },
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
        { id: "n8", node_type: "security_finding", label: "Sabit kodlanmÄ±ÅŸ ÅŸifre", key: "ev:7", file_path: "src/config.py", severity: "critical", evidence_id: "ev-7", metadata: { analyzer: "gÃ¼venlik-motoru" } },
        { id: "n9", node_type: "metric_finding", label: "YÃ¼ksek karmaÅŸÄ±klÄ±k: process_user", key: "ev:1", file_path: "src/services/user_service.py", severity: "high", evidence_id: "ev-1", metadata: { analyzer: "karmaÅŸÄ±lÄ±k-analizÃ¶rÃ¼" } },
        { id: "n10", node_type: "dependency", label: "requests", key: "dep:1", metadata: {} },
        { id: "n11", node_type: "evidence", label: "Loglama yayÄ±lÄ±mÄ±", key: "ev:9", file_path: "src/api/orders.py", evidence_id: "ev-9", metadata: { analyzer: "loglama-tutarlÄ±lÄ±k-analizÃ¶rÃ¼" } },
        { id: "n12", node_type: "evidence", label: "Somut DB client baÄŸÄ±mlÄ±lÄ±ÄŸÄ±", key: "ev:10", file_path: "src/services/order_service.py", evidence_id: "ev-10", metadata: { analyzer: "baÄŸÄ±mlÄ±lÄ±k-analizÃ¶rÃ¼" } },
      ],
      edges: [
        { id: "e1", source_id: "n2", target_id: "n1", edge_type: "belongs_to" },
        { id: "e2", source_id: "n3", target_id: "n1", edge_type: "belongs_to" },
        { id: "e3", source_id: "n4", target_id: "n2", edge_type: "belongs_to" },
        { id: "e4", source_id: "n5", target_id: "n2", edge_type: "belongs_to" },
        { id: "e5", source_id: "n9", target_id: "n5", edge_type: "affects" },
        { id: "e6", source_id: "n8", target_id: "n2", edge_type: "affects" },
        { id: "e7", source_id: "n11", target_id: "n3", edge_type: "affects" },
        { id: "e8", source_id: "n12", target_id: "n2", edge_type: "affects" },
      ],
      total_nodes: 12, total_edges: 8,
    },
    file_inventory: { total_files: 24, total_directories: 8, total_bytes: sizeBytes, files: ["src/services/user_service.py", "src/api/users.py", "src/api/orders.py", "src/auth/service.py", "src/user/service.py", "src/config.py", "src/models/user.py", "src/utils/helpers.py", "src/api/products.py", "src/api/payments.py", "src/services/order_service.py", "tests/test_user_service.py", "README.md"] },
    engineering_review: {
      offline: !useLLM,
      sections: reviewSections,
      challenges: useLLM
        ? [
            { target_step_id: "step-1", challenge_type: "too_aggressive", description: "UserService'i 5 gÃ¼nde parÃ§alamaya Ã§alÄ±ÅŸmak Ã§ok agresif. Bu sÃ¼re zarfÄ±nda baÅŸka Ã¶zellik geliÅŸtiremeyeceksiniz ve kritik yollarÄ± etkileyecek. Daha gÃ¼venli yol: Ã¶nce bir Facade oluÅŸturun, yeni servisleri arka planda yazÄ±n, eski kodu kademeli olarak taÅŸÄ±yÄ±n.", alternative: "Facade + Delegate deseni ile kademeli geÃ§iÅŸ. Ä°lk sprint'te sadece yapÄ±sÄ±nÄ± kurun, ikinci sprint'te tek bir sorumluluÄŸu taÅŸÄ±yÄ±n." },
            { target_step_id: "step-3", challenge_type: "insufficient_evidence", description: "AdÄ±m 3'Ã¼ adÄ±m 1'den Ã¶nce yapmaya Ã§alÄ±ÅŸmak tehlikeli â€” her ikisi de UserService'i deÄŸiÅŸtiriyor. Paralel Ã§alÄ±ÅŸÄ±rsanÄ±z merge conflict'ler kaosa dÃ¶ner.", alternative: "AdÄ±m 1 tamamen bittikten sonra adÄ±m 3'Ã¼ baÅŸlatÄ±n. Arada en az bir sprint olsun." },
          ]
        : [],
      recommendations: useLLM
        ? [
            { title: "HÄ±zlÄ± kazanÃ§larÄ± ilk sprint'e taÅŸÄ±yÄ±n", description: "Loglama yardÄ±mcÄ± fonksiyonu ve kullanÄ±lmayan import temizliÄŸi Ã§ok hÄ±zlÄ± ve dÃ¼ÅŸÃ¼k riskli. Ekibin 'bir ÅŸeyi tamamladÄ±k' hissi yaÅŸamasÄ± motivasyon iÃ§in kritik.", priority: "medium", confidence: "high", rationale: "DÃ¼ÅŸÃ¼k risk, yÃ¼ksek gÃ¶rÃ¼nÃ¼rlÃ¼k, anÄ±nda sonuÃ§.", linked_step_ids: ["step-4"], linked_root_cause_ids: ["rc-4"] },
            { title: "Refactor Ã¶ncesi test yazÄ±n", description: "Test kapsamÄ± %35 â€” bu, bÃ¼yÃ¼k refactor yaparken 'ne yaptÄ±ÄŸÄ±mÄ± bilmiyorum' demek. Ã–nce UserService iÃ§in en azÄ±ndan process_user metodunu test edin.", priority: "high", confidence: "high", rationale: "Mevcut dÃ¼ÅŸÃ¼k kapsam, refactor sÄ±rasÄ±nda regresyon riskini Ã§ok artÄ±rÄ±yor.", linked_step_ids: ["step-1"], linked_root_cause_ids: [] },
            { title: "Yeni kod iÃ§in DI kullanÄ±n", description: "Mevcut servisleri deÄŸiÅŸtirmesen bile, yeni yazdÄ±ÄŸÄ±nÄ±z her servis baÄŸÄ±mlÄ±lÄ±k enjeksiyonu kullansÄ±n. Bu, gelecekteki refactor'larÄ± Ã§ok kolaylaÅŸtÄ±racak.", priority: "low", confidence: "medium", rationale: "Kademeli geÃ§iÅŸ â€” yeni kod kaliteli olsun, eski kod zamanla gÃ¶Ã§ etsin.", linked_step_ids: ["step-3"], linked_root_cause_ids: ["rc-3"] },
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
        total_claims: 8,
        verified: 8,
        opinion: 0,
        rejected: 0,
        verification_rate: 1,
        claims: [
          { id: "claim-1", text: "UserService sÄ±nÄ±fÄ± her ÅŸeyi yapÄ±yor", evidence_ids: ["ev-1", "ev-2", "ev-3"], status: "verified", reason: "3 kanÄ±t bulgusu doÄŸruladÄ±" },
          { id: "claim-2", text: "DÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±k test yazmayÄ± zorlaÅŸtÄ±rÄ±yor", evidence_ids: ["ev-4"], status: "verified", reason: "Import analizÃ¶rÃ¼ doÄŸruladÄ±" },
          { id: "claim-3", text: "Servisler repository arayÃ¼zÃ¼ yerine somut DB client kullanÄ±yor", evidence_ids: ["ev-10", "ev-5"], status: "verified", reason: "BaÄŸÄ±mlÄ±lÄ±k ve mimari analizÃ¶rleri doÄŸruladÄ±" },
          { id: "claim-4", text: "Loglama 8 dosyada daÄŸÄ±nÄ±k", evidence_ids: ["ev-6", "ev-9"], status: "verified", reason: "Import ve loglama tutarlÄ±lÄ±k analizÃ¶rleri doÄŸruladÄ±" },
          { id: "claim-5", text: "Test kapsamÄ± %35", evidence_ids: ["ev-8"], status: "verified", reason: "Test kapsamÄ± analizÃ¶rÃ¼ doÄŸruladÄ±" },
          { id: "claim-6", text: "Sabit kodlanmÄ±ÅŸ ÅŸifre tespit edildi", evidence_ids: ["ev-7"], status: "verified", reason: "GÃ¼venlik motoru doÄŸruladÄ±" },
          { id: "claim-7", text: "Refactor yol haritasÄ± 4 doÄŸrulanmÄ±ÅŸ adÄ±ma baÄŸlÄ±", evidence_ids: ["ev-1", "ev-4", "ev-9", "ev-10"], status: "verified", reason: "Plan adÄ±mlarÄ±nÄ±n tamamÄ± kanÄ±t zincirine baÄŸlÄ±" },
          { id: "claim-8", text: "Facade alternatifi dÃ¼ÅŸÃ¼k riskli geÃ§iÅŸ olarak belgelenmiÅŸ", evidence_ids: ["ev-1", "ev-2", "ev-8"], status: "verified", reason: "God Class ve test kapsamÄ± kanÄ±tlarÄ± kademeli geÃ§iÅŸ ihtiyacÄ±nÄ± destekliyor" },
        ],
      } : null,
      // Confidence Model: multi-component confidence calculation.
      // NOT a single number â€” broken down by component so users can see WHY.
      confidence_model: {
        deterministic_confidence: 100, // all evidence passes + all RCs have analyzer consensus
        evidence_coverage: 100, // every evidence item is traceable to a file or artifact
        claim_verification_rate: 100, // every verifiable claim is backed by evidence
        analyzer_consensus: 100, // all root causes have >=2 supporting analyzers
        hallucination_risk: 0, // opinions are excluded from deterministic scoring
        verified_findings: 4, // all 4 recommendations are verified
        ai_opinions: 0,
        rejected_claims: 0,
        conflict_penalty: 0,
        missing_evidence_penalty: 0,
        // Sprint 11: new confidence sub-components
        coverage_score: 100,
        evidence_density: 100,
        graph_validation: 100,
        planning_validation: 100,
        claim_validation: 100,
      },
      // Sprint 11: Verified Claims â€” generated deterministically by Planning Engine,
      // NOT by LLM. LLM only explains these claims.
      verified_claims: [
        {
          claim_id: "vc-1",
          claim_text: "UserService sÄ±nÄ±fÄ± Ã§ok fazla sorumluluÄŸu Ã¼stleniyor",
          claim_type: "architecture",
          severity: "high",
          confidence: 0.85,
          status: "verified",
          supporting_evidence_ids: ["ev-1", "ev-2", "ev-3"],
          supporting_root_causes: ["rc-1"],
          supporting_metrics: { complexity: 41, sloc: 650 },
          supporting_files: ["src/services/user_service.py"],
          knowledge_graph_nodes: ["n4", "n5", "n9"],
          planning_reference: "step-1",
          validation_reason: "3 baÄŸÄ±msÄ±z analizÃ¶r (karmaÅŸÄ±klÄ±k, kod kalitesi, metrik) doÄŸruladÄ±",
        },
        {
          claim_id: "vc-2",
          claim_text: "auth ve user modÃ¼lleri arasÄ±nda dÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±k var",
          claim_type: "dependency",
          severity: "high",
          confidence: 0.92,
          status: "verified",
          supporting_evidence_ids: ["ev-4"],
          supporting_root_causes: ["rc-2"],
          supporting_metrics: {},
          supporting_files: ["src/auth/service.py", "src/user/service.py"],
          knowledge_graph_nodes: ["n7", "n6"],
          planning_reference: "step-2",
          validation_reason: "Import analizÃ¶rÃ¼ ve mimari inceleme motoru doÄŸruladÄ±",
        },
        {
          claim_id: "vc-3",
          claim_text: "Servisler veritabanÄ±na sÄ±kÄ± baÄŸlÄ±",
          claim_type: "architecture",
          severity: "medium",
          confidence: 0.75,
          status: "verified",
          supporting_evidence_ids: ["ev-5", "ev-1", "ev-10"],
          supporting_root_causes: ["rc-3"],
          supporting_metrics: { coupling: 0.85 },
          supporting_files: ["src/services/user_service.py"],
          knowledge_graph_nodes: ["n4", "n2", "n12"],
          planning_reference: "step-3",
          validation_reason: "Mimari inceleme motoru ve karmaÅŸÄ±klÄ±k analizÃ¶rÃ¼ doÄŸruladÄ±",
        },
        {
          claim_id: "vc-4",
          claim_text: "Loglama kodu 8 dosyaya yayÄ±lmÄ±ÅŸ",
          claim_type: "maintainability",
          severity: "low",
          confidence: 0.95,
          status: "verified",
          supporting_evidence_ids: ["ev-6", "ev-9"],
          supporting_root_causes: ["rc-4"],
          supporting_metrics: { affected_files: 8 },
          supporting_files: ["src/api/users.py", "src/api/orders.py"],
          knowledge_graph_nodes: ["n3", "n11"],
          planning_reference: "step-4",
          validation_reason: "Import ve loglama tutarlÄ±lÄ±k analizÃ¶rleri birlikte doÄŸruladÄ±",
        },
        {
          claim_id: "vc-5",
          claim_text: "Sabit kodlanmÄ±ÅŸ ÅŸifre tespit edildi",
          claim_type: "security",
          severity: "critical",
          confidence: 0.90,
          status: "verified",
          supporting_evidence_ids: ["ev-7"],
          supporting_root_causes: [],
          supporting_metrics: {},
          supporting_files: ["src/config.py"],
          knowledge_graph_nodes: ["n8"],
          planning_reference: null,
          validation_reason: "GÃ¼venlik motoru ve kod kalitesi motoru doÄŸruladÄ±",
        },
      ],
      // Sprint 11: Coverage Engine â€” per-recommendation coverage scores.
      // Coverage = (has evidence / needs evidence) * 100
      coverage_engine: {
        "step-1": { needs_evidence: 4, has_evidence: 4, coverage: 100, status: "pass" },
        "step-2": { needs_evidence: 3, has_evidence: 3, coverage: 100, status: "pass" },
        "step-3": { needs_evidence: 3, has_evidence: 3, coverage: 100, status: "pass" },
        "step-4": { needs_evidence: 2, has_evidence: 2, coverage: 100, status: "pass" },
        overall: 100,
      },
      // Sprint 11: Quality Gates â€” each recommendation must pass all gates
      // before it can be marked "Verified" in the report.
      quality_gates: {
        "step-1": { evidence_validation: "pass", analyzer_consensus: 3, coverage: 100, claim_validation: "pass", graph_validation: "pass", overall: "verified" },
        "step-2": { evidence_validation: "pass", analyzer_consensus: 2, coverage: 100, claim_validation: "pass", graph_validation: "pass", overall: "verified" },
        "step-3": { evidence_validation: "pass", analyzer_consensus: 3, coverage: 100, claim_validation: "pass", graph_validation: "pass", overall: "verified" },
        "step-4": { evidence_validation: "pass", analyzer_consensus: 2, coverage: 100, claim_validation: "pass", graph_validation: "pass", overall: "verified" },
      },
      // Sprint 11: Graph Reasoning â€” traversal paths that verify root causes
      // through the knowledge graph (File â†’ Class â†’ Method â†’ Evidence â†’ RootCause).
      graph_reasoning: {
        "rc-1": {
          path: ["file:src/services/user_service.py", "class:UserService", "function:process_user", "evidence:ev-1", "root_cause:rc-1"],
          path_type: "File â†’ Class â†’ Function â†’ Evidence â†’ RootCause",
          verified: true,
          traversal_depth: 4,
        },
        "rc-2": {
          path: ["module:auth", "module:services.user", "evidence:ev-4", "root_cause:rc-2"],
          path_type: "Module â†’ Module â†’ Evidence â†’ RootCause",
          verified: true,
          traversal_depth: 3,
        },
        "rc-3": {
          path: ["file:src/services/user_service.py", "class:UserService", "evidence:ev-5", "root_cause:rc-3"],
          path_type: "File â†’ Class â†’ Evidence â†’ RootCause",
          verified: true,
          traversal_depth: 3,
        },
        "rc-4": {
          path: ["file:src/api/users.py", "file:src/api/orders.py", "evidence:ev-6", "evidence:ev-9", "root_cause:rc-4"],
          path_type: "File â†’ File â†’ Evidence â†’ Evidence â†’ RootCause",
          verified: true,
          traversal_depth: 4,
        },
      },
      // Sprint 11: Reasoning Log â€” full traceability for each recommendation.
      // This is the `reasoning.json` the user requested â€” debug-grade audit trail.
      reasoning_log: [
        {
          recommendation_id: "step-1",
          root_cause: "TanrÄ± SÄ±nÄ±f: UserService",
          evidence: ["ev-1", "ev-2", "ev-3", "ev-8"],
          graph_path: ["File", "Class", "Method", "Evidence", "RootCause"],
          validation: { coverage: 100, consensus: 3, verified: true, quality_gates_passed: 5, quality_gates_total: 5 },
          source_traceability: { file: "src/services/user_service.py", line: 45, analyzer: "karmaÅŸÄ±lÄ±k-analizÃ¶rÃ¼", ast_node: "FunctionDef:process_user" },
        },
        {
          recommendation_id: "step-2",
          root_cause: "DÃ¶ngÃ¼sel BaÄŸÄ±mlÄ±lÄ±k: auth â†” user",
          evidence: ["ev-4", "ev-5"],
          graph_path: ["Module", "Module", "Evidence", "RootCause"],
          validation: { coverage: 100, consensus: 2, verified: true, quality_gates_passed: 5, quality_gates_total: 5 },
          source_traceability: { file: "src/auth/service.py", line: null, analyzer: "import-analizÃ¶rÃ¼", ast_node: null },
        },
        {
          recommendation_id: "step-3",
          root_cause: "SÄ±kÄ± BaÄŸlÄ±lÄ±k: VeritabanÄ± KatmanÄ±",
          evidence: ["ev-5", "ev-1", "ev-10"],
          graph_path: ["File", "Class", "Evidence", "RootCause"],
          validation: { coverage: 100, consensus: 3, verified: true, quality_gates_passed: 5, quality_gates_total: 5 },
          source_traceability: { file: "src/services/user_service.py", line: null, analyzer: "mimari-inceleme-motoru", ast_node: null },
        },
        {
          recommendation_id: "step-4",
          root_cause: "SaÃ§ma DeÄŸiÅŸiklik: Loglama",
          evidence: ["ev-6", "ev-9"],
          graph_path: ["File", "Evidence", "RootCause"],
          validation: { coverage: 100, consensus: 2, verified: true, quality_gates_passed: 5, quality_gates_total: 5 },
          source_traceability: { file: "src/api/users.py", line: null, analyzer: "import-analizÃ¶rÃ¼", ast_node: null },
        },
      ],

      // ======== Sprint 12: Architect Intelligence Engine ========

      // Evidence Cluster Engine â€” groups related evidence into clusters.
      evidence_clusters: [
        {
          cluster_id: "ec-1",
          cluster_name: "UserService KarmaÅŸÄ±klÄ±k KÃ¼mesi",
          cluster_type: "complexity",
          strength: 0.88,
          confidence: 0.85,
          supporting_evidence: ["ev-1", "ev-2", "ev-3", "ev-5"],
          conflicting_evidence: [],
          coverage: 100,
          affected_files: ["src/services/user_service.py"],
          affected_classes: ["UserService"],
          graph_nodes: ["n4", "n5", "n9"],
          validation_status: "pass",
        },
        {
          cluster_id: "ec-2",
          cluster_name: "DÃ¶ngÃ¼sel BaÄŸÄ±mlÄ±lÄ±k KÃ¼mesi",
          cluster_type: "dependency",
          strength: 0.92,
          confidence: 0.92,
          supporting_evidence: ["ev-4", "ev-5"],
          conflicting_evidence: [],
          coverage: 100,
          affected_files: ["src/auth/service.py", "src/user/service.py"],
          affected_classes: [],
          graph_nodes: ["n7", "n6"],
          validation_status: "pass",
        },
        {
          cluster_id: "ec-3",
          cluster_name: "GÃ¼venlik Zafiyeti KÃ¼mesi",
          cluster_type: "security",
          strength: 0.90,
          confidence: 0.90,
          supporting_evidence: ["ev-7"],
          conflicting_evidence: [],
          coverage: 100,
          affected_files: ["src/config.py"],
          affected_classes: [],
          graph_nodes: ["n8"],
          validation_status: "pass",
        },
      ],

      // Hypothesis Engine â€” hypotheses are generated from evidence clusters,
      // validated through multi-stage process, and only PASS hypotheses
      // become Root Causes.
      hypotheses: [
        {
          hypothesis_id: "h-1",
          hypothesis_name: "UserService God Object",
          hypothesis_type: "god_class",
          evidence_cluster_ids: ["ec-1"],
          supporting_evidence: ["ev-1", "ev-2", "ev-3", "ev-5"],
          validation_stages: {
            evidence_cluster: "pass",
            graph_traversal: "pass",
            analyzer_consensus: 3,
            coverage: 100,
            conflict_detection: "pass",
            confidence: 0.85,
          },
          status: "pass",
          root_cause_id: "rc-1",
          confidence_breakdown: { graph_support: 15, coverage: 20, consensus: 18, conflict: 0, missing: 0, total: 82 },
        },
        {
          hypothesis_id: "h-2",
          hypothesis_name: "DÃ¶ngÃ¼sel BaÄŸÄ±mlÄ±lÄ±k",
          hypothesis_type: "circular_dependency",
          evidence_cluster_ids: ["ec-2"],
          supporting_evidence: ["ev-4", "ev-5"],
          validation_stages: {
            evidence_cluster: "pass",
            graph_traversal: "pass",
            analyzer_consensus: 2,
            coverage: 100,
            conflict_detection: "pass",
            confidence: 0.92,
          },
          status: "pass",
          root_cause_id: "rc-2",
          confidence_breakdown: { graph_support: 15, coverage: 20, consensus: 12, conflict: 0, missing: 0, total: 92 },
        },
        {
          hypothesis_id: "h-3",
          hypothesis_name: "SÄ±kÄ± BaÄŸlÄ±lÄ±k â€” VeritabanÄ± KatmanÄ±",
          hypothesis_type: "tight_coupling",
          evidence_cluster_ids: ["ec-1"],
          supporting_evidence: ["ev-5", "ev-1", "ev-10"],
          validation_stages: {
            evidence_cluster: "pass",
            graph_traversal: "pass",
            analyzer_consensus: 3,
            coverage: 100,
            conflict_detection: "pass",
            confidence: 0.9,
          },
          status: "pass",
          root_cause_id: "rc-3",
          confidence_breakdown: { graph_support: 15, coverage: 20, consensus: 18, conflict: 0, missing: 0, total: 90 },
        },
        {
          hypothesis_id: "h-4",
          hypothesis_name: "Anemic Domain Model",
          hypothesis_type: "anemic_domain",
          evidence_cluster_ids: [],
          supporting_evidence: [],
          validation_stages: {
            evidence_cluster: "fail",
            graph_traversal: "skip",
            analyzer_consensus: 0,
            coverage: 0,
            conflict_detection: "skip",
            confidence: 0,
          },
          status: "fail",
          root_cause_id: null,
          confidence_breakdown: { graph_support: 0, coverage: 0, consensus: 0, conflict: 0, missing: -20, total: 0 },
        },
      ],

      // Alternative Recommendation Engine â€” each root cause generates
      // multiple solution alternatives with full tradeoff analysis.
      alternatives: {
        "rc-1": [
          {
            alt_id: "alt-rc1-a",
            name: "Servis ParÃ§alama (Split Service)",
            approach: "UserService'i auth, profile, notification, settings olmak Ã¼zere 4 ayrÄ± servise bÃ¶l.",
            impact: 90, risk: 70, implementation_effort: 80, estimated_time: "5 gÃ¼n", technical_debt_reduction: 85,
            confidence: 0.80, required_preconditions: ["test coverage >= 60%"],
            tradeoffs: {
              advantages: ["Net sorumluluk ayrÄ±mÄ±", "BaÄŸÄ±msÄ±z test edilebilirlik", "Paralel geliÅŸtirme"],
              disadvantages: ["Daha fazla dosya", "Servisler arasÄ± iletiÅŸim overhead'i", "GeÃ§iÅŸ sÃ¼reci uzun"],
              risks: ["Kritik yollarÄ± etkiler", "Merge conflict riski"],
              when_preferred: "Ekip bÃ¼yÃ¼kse ve uzun vadeli bakÄ±m Ã¶ncelikliyse",
              when_not_preferred: "KÃ¼Ã§Ã¼k ekip ve hÄ±zlÄ± teslimat gerekiyorsa",
            },
            decision_score: { impact: 90, risk: 30, coverage: 75, confidence: 80, complexity_reduction: 85, maintainability_gain: 90, implementation_cost: 20, total: 68 },
          },
          {
            alt_id: "alt-rc1-b",
            name: "Facade Pattern",
            approach: "UserService'i Facade olarak koru, iÃ§ mantÄ±ÄŸÄ± alt servislere delegate et.",
            impact: 60, risk: 25, implementation_effort: 40, estimated_time: "2 gÃ¼n", technical_debt_reduction: 50,
            confidence: 0.85, required_preconditions: [],
            tradeoffs: {
              advantages: ["Geriye dÃ¶nÃ¼k uyumlu", "HÄ±zlÄ± geÃ§iÅŸ", "DÃ¼ÅŸÃ¼k risk"],
              disadvantages: ["Facade hatta karmaÅŸÄ±k", "Sorun yÃ¼zeysel Ã§Ã¶zÃ¼lÃ¼r"],
              risks: ["GeliÅŸtiriciler Facade'i kullanmaya devam edebilir"],
              when_preferred: "HÄ±zlÄ± dÃ¼zeltme gerekiyorsa",
              when_not_preferred: "KÃ¶klÃ¼ Ã§Ã¶zÃ¼m isteniyorsa",
            },
            decision_score: { impact: 60, risk: 75, coverage: 75, confidence: 85, complexity_reduction: 40, maintainability_gain: 55, implementation_cost: 60, total: 64 },
          },
          {
            alt_id: "alt-rc1-c",
            name: "Domain Layer Ã‡Ä±karÄ±mÄ±",
            approach: "Ä°ÅŸ mantÄ±ÄŸÄ±nÄ± ayrÄ± bir Domain Layer'a taÅŸÄ±, UserService'i uygulama servisine indir.",
            impact: 75, risk: 50, implementation_effort: 60, estimated_time: "3 gÃ¼n", technical_debt_reduction: 70,
            confidence: 0.75, required_preconditions: ["domain model tanÄ±mlÄ± olmalÄ±"],
            tradeoffs: {
              advantages: ["DDD uyumlu", "Ä°ÅŸ mantÄ±ÄŸÄ± merkezi", "Test edilebilir"],
              disadvantages: ["Learning curve", "Mimari deÄŸiÅŸiklik"],
              risks: ["AÅŸÄ±rÄ± mÃ¼hendislik"],
              when_preferred: "KarmaÅŸÄ±k iÅŸ kurallarÄ± varsa",
              when_not_preferred: "Basit CRUD uygulamasÄ±ysa",
            },
            decision_score: { impact: 75, risk: 50, coverage: 75, confidence: 75, complexity_reduction: 70, maintainability_gain: 80, implementation_cost: 40, total: 66 },
          },
        ],
        "rc-2": [
          {
            alt_id: "alt-rc2-a",
            name: "Ortak ModÃ¼l Ã‡Ä±karÄ±mÄ±",
            approach: "Ortak mantÄ±ÄŸÄ± yeni bir alt seviye modÃ¼le taÅŸÄ±.",
            impact: 85, risk: 45, implementation_effort: 50, estimated_time: "3 gÃ¼n", technical_debt_reduction: 80,
            confidence: 0.90, required_preconditions: [],
            tradeoffs: {
              advantages: ["DÃ¶ngÃ¼ tamamen kÄ±rÄ±lÄ±r", "Test edilebilirlik artar"],
              disadvantages: ["Yeni modÃ¼l ekleme"],
              risks: ["DÃ¼ÅŸÃ¼k â€” izole deÄŸiÅŸiklik"],
              when_preferred: "Daima tercih edilir",
              when_not_preferred: "â€”",
            },
            decision_score: { impact: 85, risk: 55, coverage: 100, confidence: 90, complexity_reduction: 80, maintainability_gain: 85, implementation_cost: 50, total: 78 },
          },
        ],
      },

      // Decision Engine â€” scores alternatives and selects best recommendation.
      decision_engine: {
        "rc-1": { best_alternative_id: "alt-rc1-a", decision_score: 68, runner_up_id: "alt-rc1-c", runner_up_score: 66, rationale: "En yÃ¼ksek etki ve teknik borÃ§ azaltma" },
        "rc-2": { best_alternative_id: "alt-rc2-a", decision_score: 78, runner_up_id: null, runner_up_score: 0, rationale: "Tek gÃ¼venilir Ã§Ã¶zÃ¼m" },
      },

      // Architectural Pattern Matcher â€” detects which patterns the repo follows.
      architectural_patterns: [
        { pattern: "Layered", compatibility: 65, matched_layers: ["api", "services", "models"], missing_layers: ["repository", "domain"], description: "KÄ±smen katmanlÄ± â€” repository ve domain katmanlarÄ± eksik" },
        { pattern: "MVC", compatibility: 40, matched_layers: ["api (Controller)", "models (Model)"], missing_layers: ["views"], description: "MVC yapÄ±sÄ± zayÄ±f â€” views katmanÄ± yok" },
        { pattern: "Modular Monolith", compatibility: 55, matched_layers: ["services", "auth", "user"], missing_layers: [], description: "ModÃ¼ler monolith yaklaÅŸÄ±mÄ± var ama modÃ¼l sÄ±nÄ±rlarÄ± belirsiz" },
        { pattern: "DDD", compatibility: 25, matched_layers: ["models"], missing_layers: ["domain", "application", "infrastructure"], description: "DDD uyumu dÃ¼ÅŸÃ¼k â€” anemic domain model" },
        { pattern: "Hexagonal", compatibility: 15, matched_layers: [], missing_layers: ["ports", "adapters"], description: "Hexagonal mimari yok" },
      ],

      // Architectural Smell Engine â€” detects architectural-level smells
      // (not code smells, architecture-level patterns).
      architectural_smells: [
        { smell_id: "as-1", smell_type: "God Component", severity: "high", confidence: 0.85, affected: "UserService", evidence_ids: ["ev-1", "ev-2", "ev-3"], description: "UserService 4+ sorumluluÄŸu Ã¼stlenmiÅŸ â€” God Component anti-deseni" },
        { smell_id: "as-2", smell_type: "Cyclic Dependency", severity: "high", confidence: 0.92, affected: "auth â†” user", evidence_ids: ["ev-4"], description: "DÃ¶ngÃ¼sel modÃ¼l baÄŸÄ±mlÄ±lÄ±ÄŸÄ± â€” test edilebilirliÄŸi engelliyor" },
        { smell_id: "as-3", smell_type: "Architecture Sink", severity: "medium", confidence: 0.75, affected: "user_service.py", evidence_ids: ["ev-5", "ev-1"], description: "Her ÅŸey user_service.py'a akÄ±yor â€” darboÄŸaz oluÅŸturuyor" },
        { smell_id: "as-4", smell_type: "Logging Spread", severity: "low", confidence: 0.95, affected: "api logging", evidence_ids: ["ev-6", "ev-9"], description: "Loglama davranÄ±ÅŸÄ± birden fazla dosyada tekrar ediyor" },
      ],

      // Impact Simulator â€” simulates what happens if a recommendation is applied.
      impact_simulations: [
        {
          recommendation_id: "step-1",
          scenario: "UserService parÃ§alandÄ±ktan sonra",
          current_metrics: { complexity: 41, coupling: 0.85, maintainability: 55, technical_debt: 70 },
          projected_metrics: { complexity: 12, coupling: 0.45, maintainability: 85, technical_debt: 30 },
          delta: { complexity: -29, coupling: -0.40, maintainability: +30, technical_debt: -40 },
          confidence: 0.80,
        },
        {
          recommendation_id: "step-2",
          scenario: "DÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±k kÄ±rÄ±ldÄ±ktan sonra",
          current_metrics: { complexity: 15, coupling: 0.70, maintainability: 60, technical_debt: 50 },
          projected_metrics: { complexity: 12, coupling: 0.40, maintainability: 80, technical_debt: 25 },
          delta: { complexity: -3, coupling: -0.30, maintainability: +20, technical_debt: -25 },
          confidence: 0.90,
        },
      ],

      // Refactor Roadmap Engine â€” dependency graph instead of flat list.
      roadmap_graph: {
        nodes: [
          { id: "step-1", title: "UserService'i parÃ§ala", dependencies: [], blocks: ["step-2", "step-3"], phase: 1 },
          { id: "step-2", title: "DÃ¶ngÃ¼sel baÄŸÄ±mlÄ±lÄ±ÄŸÄ± kÄ±r", dependencies: ["step-1"], blocks: [], phase: 2 },
          { id: "step-3", title: "Repository arayÃ¼zÃ¼ tanÄ±mla", dependencies: ["step-1"], blocks: [], phase: 2 },
          { id: "step-4", title: "Ortak loglama Ã§Ä±kar", dependencies: [], blocks: [], phase: 1 },
        ],
        edges: [
          { from: "step-4", to: null, type: "parallel" },
          { from: "step-1", to: "step-2", type: "blocking" },
          { from: "step-1", to: "step-3", type: "blocking" },
        ],
        phases: [
          { phase: 1, title: "HÄ±zlÄ± KazanÃ§lar + Temel", step_ids: ["step-1", "step-4"], can_parallel: true },
          { phase: 2, title: "Mimari DÃ¼zeltmeler", step_ids: ["step-2", "step-3"], can_parallel: true },
        ],
      },

      // Confidence Explanation â€” shows WHY a confidence score is what it is.
      confidence_explanations: {
        "rc-1": {
          score: 82,
          components: [
            { name: "Graph Support", contribution: +15, reason: "4 dÃ¼ÄŸÃ¼mlÃ¼ geÃ§iÅŸ yolu doÄŸrulandÄ±" },
            { name: "Coverage", contribution: +20, reason: "4/4 kanÄ±t kapsamÄ± %100" },
            { name: "Analyzer Consensus", contribution: +18, reason: "3 baÄŸÄ±msÄ±z analizÃ¶r doÄŸruladÄ±" },
            { name: "Conflict", contribution: 0, reason: "Ã‡akÄ±ÅŸan kanÄ±t yok" },
            { name: "Missing Evidence", contribution: 0, reason: "Eksik kanÄ±t yok" },
          ],
        },
        "rc-2": {
          score: 92,
          components: [
            { name: "Graph Support", contribution: +15, reason: "3 dÃ¼ÄŸÃ¼mlÃ¼ geÃ§iÅŸ yolu doÄŸrulandÄ±" },
            { name: "Coverage", contribution: +20, reason: "2/2 kanÄ±t kapsamÄ± %100" },
            { name: "Analyzer Consensus", contribution: +12, reason: "2 baÄŸÄ±msÄ±z analizÃ¶r doÄŸruladÄ±" },
            { name: "Conflict", contribution: 0, reason: "Ã‡akÄ±ÅŸan kanÄ±t yok" },
            { name: "Missing Evidence", contribution: 0, reason: "Eksik kanÄ±t yok" },
          ],
        },
        "rc-4": {
          score: 100,
          components: [
            { name: "Graph Support", contribution: +20, reason: "4 dÃ¼ÄŸÃ¼mlÃ¼ geÃ§iÅŸ yolu doÄŸrulandÄ±" },
            { name: "Coverage", contribution: +20, reason: "2/2 kanÄ±t kapsamÄ± %100" },
            { name: "Analyzer Consensus", contribution: +20, reason: "2 baÄŸÄ±msÄ±z analizÃ¶r doÄŸruladÄ±" },
            { name: "Conflict", contribution: 0, reason: "Ã‡akÄ±ÅŸan kanÄ±t yok" },
            { name: "Missing Evidence", contribution: 0, reason: "Eksik kanÄ±t yok" },
            { name: "Quality Gate", contribution: +40, reason: "TÃ¼m kalite kapÄ±larÄ± geÃ§ti" },
          ],
        },
      },
    },
    analyzed_at: new Date().toISOString(),
  };
}

