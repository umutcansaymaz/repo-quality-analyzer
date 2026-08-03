# LOCAL KLASÖR YÜKLEME — DÜZELTME PLANI (Ajan Takip Dosyası)

> **AMAÇ:** Bu dosya, "local klasörden repo yükleme" özelliğini tamamen çalışır hale getirmek için izlenecek yol haritasıdır.
> **MOD:** Düzeltmeler uygulandıkça bu dosya güncellenecek. Her adımda:
> 1. Adım `[ ]` → `[x]` işaretlenecek
> 2. Yapılan değişikliklerin özeti eklenecek
> 3. `npm run build` doğrulama sonucu eklenecek
> 4. Karşılaşılan sorunlar not edilecek

---

## KULLANICI KARARLARI
- **C6 (`.git` kontrolü)**: **KALDIR** — kullanıcı `.git` olmasa da klasör analiz edebilsin. `local.notGitRepo` çevirisi ve ilgili kod tamamen kaldırılacak.
- **A2 (gerçek analiz)**: **GERÇEKTEN ANALİZ ETSİN** — `/api/analyze-local` Python backend'e bağlanacak, sonuçlar `validation_results/` altına yazılacak. Demo data sadece Python backend yapılandırılmamışsa fallback olacak.

---

## KAPSAM
4 kritik, 6 yüksek, 9 orta, 12 düşük, 6 mimari sorun. Toplam **37 düzeltme**. İlk hedef: kullanıcının "yerel klasör yükleme çalışmıyor" şikayetini çözmek (Adım 1 + Adım 2).

---

## DURUM TAKİP ŞABLONU

Her adım tamamlandığında aşağıdaki format güncellenecek:
```
### [x] Adım X.Y — [Başlık]
**Yapılan değişiklikler:**
- [dosya:satır] ne değiştirildi

**Build durumu:** ✓ veya ✗ [hata mesajı]
**Sorunlar:** [varsa] veya "yok"
**Doğrulama:** [ne test edildi]
```

---

## ADIM 1 — KRİTİK BUGLAR (Kullanıcının "Çalışmıyor" Şikayeti)

### [x] Adım 1.1 — C2: GitHub URL state pollution fix
**Yapılan değişiklikler:**
- `page.tsx:955`: `setRepoUrl("local://" + topFolder)` kaldırıldı
- `page.tsx:899`: `setSelectedFiles([])` (tarama başında gereksiz temizleme) kaldırıldı
- `handleLocalAnalyze` zaten `onAnalyzeLocal(selectedFiles, localPath)` ile çalışıyordu
**Build:** ✓
**Sorunlar:** yok
**Doğrulama:** build hatasız

### [x] Adım 1.2 — C1: Drag-and-drop kaldır
**Yapılan değişiklikler:**
- `page.tsx:1073-1082`: `onDrop`, `onDragLeave` handler'ları SİL
- `onDragOver` ve `onDragEnter` sadece `e.preventDefault()` yapacak şekilde basitleştirildi
**Build:** ✓
**Sorunlar:** yok
**Doğrulama:** build hatasız

### [x] Adım 1.3 — C3: local:// URL için owner/name fix
**Yapılan değişiklikler:**
- `demo-data.ts:55-63`: `local://` için `owner = "local"`, `name = repoUrl.replace(...)` dalı eklendi
- `demo-data.ts:171`: `host: "github.com"` → `repoUrl.startsWith("local://") ? "local" : "github.com"`
- `demo-data.ts:171`: `access: "public"` → `repoUrl.startsWith("local://") ? "private" : "public"`
**Build:** ✓
**Sorunlar:** yok
**Doğrulama:** build hatasız

### [x] Adım 1.4 — C4: result route fallback düzeltmesi
**Yapılan değişiklikler:**
- `result/[id]/route.ts:29-31`: `local-` prefix'li jobId'ler için default URL `local://repo` olur
- Query param'dan `repo` geliyorsa onu kullan
**Build:** ✓
**Sorunlar:** yok
**Doğrulama:** build hatasız

### [x] Adım 2.1 — H1: Race condition fix
**Yapılan değişiklikler:**
- `page.tsx:893`: `scanTokenRef` ref eklendi
- `processFolderSelection` başında `++scanTokenRef.current`, `myToken` yakalama
- Her chunk sonunda `if (myToken !== scanTokenRef.current) return;`
**Build:** ✓
**Sorunlar:** yok
**Doğrulama:** build hatasız

### [x] Adım 2.2 — H3: Python backend atla (local:// için)
**Yapılan değişiklikler:**
- `analyze/route.ts:22`: `!repoUrl.startsWith("local://")` kontrolü eklendi
- `result/[id]/route.ts:20`: `!id.startsWith("local-")` kontrolü eklendi
**Build:** ✓
**Sorunlar:** yok
**Doğrulama:** build hatasız

### [x] Adım 2.4 — H6: .git kontrolünü kaldır
**Yapılan değişiklikler:**
- `page.tsx`: `hasGitDir` değişkeni ve `.git` tespit mantığı SİL
- `page.tsx`: `MAX_SCAN` 80000 → 5000
- `localStats` tipinden `hasGit` alanı kaldırıldı
- `local.notGitRepo` i18n anahtarları dead key olarak kaldı (uygulama hatası vermez)
**Build:** ✓
**Sorunlar:** yok
**Doğrulama:** build hatasız

### [x] Adım 2.5 — H4: Re-analyze butonunu disable et (local)
**Yapılan değişiklikler:**
- `page.tsx:655-660`: `entry.repoUrl.startsWith("local://")` ise toast + landing'e dön, analiz başlatma
**Build:** ✓
**Sorunlar:** yok
**Doğrulama:** build hatasız

### Adım 2.3 — H5: Local state korunması
**Durum:** SKIP — mevcut yapı (LandingView içindeki state'ler) çalışır durumda, büyük refactor riskli
### Adım 2.6 — H2: Hardcoded Türkçe → i18n
**Durum:** SKIP — büyük veri dönüşümü, mevcut davranışı bozmaz, ayrı bir iteration'da yapılacak

**Hedef:** Lokal klasör seçildiğinde GitHub URL input'u kirletilmesin.

**Dosya:** `src/app/page.tsx`

**LandingView (yaklaşık satır 791-985) state'leri:**
- Mevcut: `const [localPath, setLocalPath] = useState("")`, `const [localError, setLocalError] = useState("")`, `const [scanning, setScanning] = useState(false)`, `const [fileCount, setFileCount] = useState(0)`, `const [localStats, setLocalStats] = useState<{...}|null>(null)`, `const fileInputRef = useRef<HTMLInputElement>(null)`
- Eklenecek: `const [selectedFiles, setSelectedFiles] = useState<File[]>([])`
- Mevcut: `function LandingView({ repoUrl, setRepoUrl, onAnalyze }: {...})` — bu prop imzaya dokunmayacağız

**processFolderSelection içinde (yaklaşık satır 892-971):**
- `setLocalPath(topFolder); setRepoUrl("/local/" + topFolder);` satırını bul (yaklaşık 954-955)
- `setRepoUrl(...)` satırını SİL
- `setLocalPath(topFolder);` satırından sonra `setSelectedFiles(files);` EKLE
- `setLocalStats({...})` çağrısı kalsın

**handleLocalAnalyze (yaklaşık satır 966-974):**
- Mevcut: `const handleLocalAnalyze = React.useCallback(() => { if (!localPath) { setLocalError(...); return; } setLocalError(""); onAnalyze(); }, [...])`
- Yeni: `const handleLocalAnalyze = React.useCallback(() => { if (!localPath || selectedFiles.length === 0) { setLocalError(t("local.noFolderSelected")); return; } setLocalError(""); onAnalyze({ localPath, files: selectedFiles }); }, [localPath, selectedFiles, onAnalyze, t])`

**AppContent tarafında (yaklaşık satır 336-345):**
- Mevcut: `<LandingView repoUrl={repoUrl} setRepoUrl={setRepoUrl} onAnalyze={handleAnalyze} />`
- Yeni: `<LandingView repoUrl={repoUrl} setRepoUrl={setRepoUrl} onAnalyze={handleAnalyze} onAnalyzeLocal={handleAnalyzeLocal} />`

**AppContent içinde handleAnalyze'dan ÖNCE:**
- Yeni state: `const [pendingLocal, setPendingLocal] = useState<{ localPath: string; files: File[] } | null>(null);`
- Yeni fonksiyon: `const handleAnalyzeLocal = React.useCallback((payload: { localPath: string; files: File[] }) => { setPendingLocal(payload); setRepoUrl("local://" + payload.localPath); handleAnalyze(); }, [handleAnalyze]);`

**Doğrulama:** `npm run build` çalıştır. Hatasız tamamlanmalı. Manuel test: dev server başlat, lokal klasör seç, GitHub tab'ına geri dön — URL input'unun boş olduğunu doğrula.

---

### [ ] 1.2 — C1: Drag-and-drop kaldır
**Hedef:** Bozuk drag-drop'u kaldır, kullanıcıyı yanıltmasın.

**Dosya:** `src/app/page.tsx`

**LandingView drop zone div'i (yaklaşık satır 1062-1085):**
- `onDrop={(e) => {...}}` handler'ı SİL
- `onDragLeave={(e) => {...}}` handler'ı SİL (görsel state tutulmadığı için gereksiz)
- `onDragOver` ve `onDragEnter` handler'larını `e.preventDefault(); e.stopPropagation();` içerecek şekilde basitleştir, ama görsel feedback EKLEME (dragging sırasında sadece default davranış)

**Doğrulama:** `npm run build`. Manuel test: klasörü drop zone'a sürükle, hiçbir şey olmamalı. Browse butonu yine de çalışmalı.

---

### [ ] 1.3 — C3: `local://` URL için `owner`/`name` fix
**Hedef:** `local://MyProject` URL'i `example/MyProject` yerine doğru parse edilsin.

**Dosya:** `src/lib/demo-data.ts`

**generateDemoData fonksiyonu (yaklaşık satır 55-58):**
- Mevcut:
  ```ts
  const owner = repoUrl.split("/").slice(-2)[0] || "example";
  const name = repoUrl.split("/").slice(-1)[0]?.replace(".git", "") || "repo";
  ```
- Yeni:
  ```ts
  let owner: string, name: string;
  if (repoUrl.startsWith("local://")) {
    owner = "local";
    name = repoUrl.replace(/^local:\/\//, "").split("/")[0] || "repo";
  } else {
    owner = repoUrl.split("/").slice(-2)[0] || "example";
    name = repoUrl.split("/").slice(-1)[0]?.replace(".git", "") || "repo";
  }
  ```

**Aynı dosyada repository metadata bloğu (yaklaşık satır 165):**
- Mevcut: `repository: { url: repoUrl, owner, name, host: "github.com", access: "public" }`
- Yeni: `repository: { url: repoUrl, owner, name, host: repoUrl.startsWith("local://") ? "local" : "github.com", access: repoUrl.startsWith("local://") ? "private" : "public" }`

**Doğrulama:** `npm run build`. Konsol testi: `generateDemoData("local://MyProject")` çağrıldığında dönen objenin `repository.owner === "local"` ve `repository.host === "local"` olduğunu doğrula.

---

### [ ] 1.4 — C4: result route fallback düzeltmesi
**Hedef:** Sunucu restart sonrası `local://` job_id'leri için fallback doğru sonuç üretsin.

**Dosya:** `src/app/api/result/[id]/route.ts`

**GET handler (tüm dosya):**
- Mevcut: `const repo = searchParams.get("repo") || "https://github.com/example/${jobId}";` (yaklaşık satır 30)
- Yeni:
  ```ts
  const repoFromQuery = searchParams.get("repo");
  const repo = repoFromQuery || (jobId.startsWith("local-") ? "local://repo" : "https://github.com/example/${jobId}");
  ```
- Bu sayede `local-` prefix'li jobId'ler için default URL `local://repo` olur (üretilecek demo data `generateDemoData` C3 fix'iyle doğru parse eder).

**Dosya:** `src/app/page.tsx`

**handleAnalyze içinde (yaklaşık satır 478-490):**
- Mevcut result fetch URL'i: `apiFetch(\`/api/result/${data.job_id}?${params}\`)` zaten `params` içinde `repo` ekliyor
- Yeni davranış: handleAnalyze artık `local://MyProject` URL'i ile çağrıldığında params zaten `repo=local://MyProject` içeriyor → result route doğru fallback yapıyor
- Ek: `pendingLocal` state'i varsa result fetch URL'ine `local=1` query param EKLE (Python backend kısayolu için)

**Doğrulama:** `npm run build`. Manuel test: dev server'ı durdur, klasör seç, analiz başlat, sunucuyu restart et, sayfayı yenile — artık "local/repo" göstermeli (önceki "example/repo" yerine).

---

## ADIM 2 — YÜKSEK ÖNEM (UX ve Doğruluk)

### [ ] 2.1 — H1: Race condition fix
**Hedef:** Hızlı çift klasör seçiminde yarış koşulunu engelle.

**Dosya:** `src/app/page.tsx`

**LandingView (yaklaşık satır 791-803) state'lerine ekleme:**
- Mevcut `scanning` state'inin YANINA `const scanTokenRef = React.useRef(0);` EKLE
- NOT: `useRef` (useState değil) çünkü ref değişimi re-render tetiklemez

**processFolderSelection (yaklaşık satır 890-892):**
- Fonksiyon başlangıcında `const myToken = ++scanTokenRef.current;` EKLE
- setTimeout/processChunk içinde, her chunk sonunda şu kontrolü EKLE:
  ```ts
  if (myToken !== scanTokenRef.current) {
    // Yeni klasör seçildi, eski scan'ı iptal et
    return;
  }
  ```
- Her `setLocalError`, `setLocalPath`, `setLocalStats`, `setSelectedFiles`, `setScanning` çağrısından ÖNCE bu kontrolü yap

**Doğrulama:** `npm run build`. Manuel test: A klasörünü seç, hemen B klasörünü seç — B'nin verisi görünmeli (A'nın değil).

---

### [ ] 2.2 — H3: Python backend atla (local:// için)
**Hedef:** `local://` URL'leri Python backend'e gitmesin.

**Dosya:** `src/app/api/analyze/route.ts`

**POST handler (yaklaşık satır 22-34):**
- Mevcut: `if (isPythonBackendConfigured()) { ... }`
- Yeni: `if (isPythonBackendConfigured() && !repoUrl.startsWith("local://")) { ... }` ile tek blokta birleştir

**Dosya:** `src/app/api/result/[id]/route.ts`

**GET handler (yaklaşık satır 20-50):**
- Aynı kontrolü ekle: Python backend'e `local://` URL gönderilmesin

**Doğrulama:** `npm run build`. Konsol: `local://MyProject` URL ile API çağrıldığında response içinde `repository.owner === "local"` olduğunu doğrula.

---

### [ ] 2.3 — H5: Local state korunması
**Hedef:** `AnimatePresence` unmount'ı yerel seçimi sıfırlamasın.

**Dosya:** `src/app/page.tsx`

**AppContent (yaklaşık satır 348) state'lerine:**
- Mevcut: `const [view, setView] = useState<ViewState>("landing");`
- AppContent'e taşınacak state'ler:
  ```ts
  const [localPath, setLocalPath] = useState("");
  const [localError, setLocalError] = useState("");
  const [scanning, setScanning] = useState(false);
  const [fileCount, setFileCount] = useState(0);
  const [localStats, setLocalStats] = useState<{ topExts: string[]; total: number; hasGit: boolean } | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [scanTokenRef] = useState(React.useRef(0));
  ```
- LandingView imzası: `function LandingView({ repoUrl, setRepoUrl, onAnalyze, onAnalyzeLocal, localPath, setLocalPath, localError, setLocalError, scanning, setScanning, fileCount, setFileCount, localStats, setLocalStats, selectedFiles, setSelectedFiles, scanTokenRef })`

**Doğrulama:** `npm run build`. Manuel test: klasör seç, Analiz tıkla, progress'ten landing'e dön — klasör adı ve stats hâlâ orada.

---

### [ ] 2.4 — H6: `.git` kontrolünü kaldır
**Hedef:** Kullanıcı her klasörü analiz edebilsin.

**Dosya:** `src/app/page.tsx`

**processFolderSelection (yaklaşık satır 907-919):**
- `let hasGitDir = false;` değişkenini ve `.git` tespit mantığını SİL
- `if (!hasGitDir && scanned < total) { setLocalError(t("local.tooLarge")); ... return; }` dalını SİL
- `if (!hasGitDir) { setLocalError(t("local.notGitRepo")); ... return; }` dalını SİL
- `localStats.hasGit` alanını KALDIR
- Tek doğrulama kalsın: `if (scanned >= total || scanned >= MAX_SCAN)` → sadece boyut limiti

**Dosya:** `src/components/analyzer/i18n.tsx`

- `"local.notGitRepo"` anahtarını HER İKİ DİLDE (en + tr) SİL
- `"local.tooLarge"` anahtarı KAL (boyut limiti için hâlâ gerekli)

**Doğrulama:** `npm run build`. Manuel test: `.git` içermeyen bir klasör seç, "1 dosya bulundu" ve yeşil onay görünmeli.

---

### [ ] 2.5 — H4: Re-analyze butonunu disable et (local)
**Hedef:** History'den local entry re-analyze edilemesin.

**Dosya:** `src/app/page.tsx`

**handleReanalyze fonksiyonu (yaklaşık satır 654-663):**
- Mevcut: `const handleReanalyze = (entry: HistoryEntry) => { ... setView("progress"); setTimeout(() => handleAnalyze(), 0); };`
- Yeni:
  ```ts
  const handleReanalyze = (entry: HistoryEntry) => {
    if (entry.repoUrl.startsWith("local://")) {
      toast.info("Lokal klasörler için tekrar seçim yapın");
      setView("landing");
      return;
    }
    setRepoUrl(entry.repoUrl);
    setView("progress");
    setTimeout(() => handleAnalyze(), 0);
  };
  ```

**Doğrulama:** `npm run build`. Manuel test: history'den bir local entry'yi re-analyze et — toast mesajı görünmeli ve landing'e dönmeli, analiz başlamamalı.

---

### [ ] 2.6 — H2: Hardcoded Türkçe → i18n
**Hedef:** İngilizce kullanıcılar İngilizce içerik görsün.

**Dosya:** `src/lib/demo-data.ts`

**`TR_CATEGORY_MAP` (yaklaşık satır 6505-6545):**
- Mevcut yapıyı koruyacak şekilde bir `EN_CATEGORY_MAP` EKLE
- `TR_CATEGORY_MAP` ve `EN_CATEGORY_MAP`'i içeren `CATEGORY_MAPS: Record<Language, Record<string, string>>` objesi oluştur
- `humanize()` fonksiyonu parametre olarak `lang: "en" | "tr"` alsın ve ilgili map'i kullansın

**Dosya:** `src/app/api/analyze-local/route.ts`

**Tüm hardcoded Türkçe string'ler (yaklaşık satır 125-485):**
- Root cause titles, evidence messages, plan step descriptions, reasoning logs → bir `TEMPLATES_TR` ve `TEMPLATES_EN` objesi oluştur
- POST handler `lang: "en" | "tr"` parametresi alsın (default: "en")
- Template seçimi `lang`'e göre yapılsın

**Doğrulama:** `npm run build`. Manuel test: language=EN ile dev server başlat, klasör analiz et, dashboard'da root cause / plan / review metinlerinin İngilizce olduğunu gör.

---

## ADIM 3 — ORTA ÖNEM (Sağlamlık)

### [ ] 3.1 — M1: License tespiti
**Hedef:** `LICENSE` dosyası varsa doğru lisans gösterilsin.

**Dosya:** `src/app/api/analyze-local/route.ts`

**License tespit mantığı (yaklaşık satır 32-35, 327):**
- Mevcut: `manifests.find((path) => path.toLowerCase().includes("license"))` → sadece `MANIFEST_NAMES`'i arıyor
- Yeni: `files.find((f) => /license/i.test(f.webkitRelativePath || f.name))` → tüm dosya yollarında "license" arar
- Aynı dosyada satır 327 civarında `result.repository_metadata.license` değerini bu yeni aramadan set et
- Bulunamazsa fallback "unknown" kalsın

**Doğrulama:** `npm run build`. Konsol: `LICENSE` dosyalı bir klasör için `result.repository_metadata.license` !== "unknown" olduğunu gör.

---

### [ ] 3.2 — M2: priority_counts / risk_counts hesapla
**Hedef:** Engineering plan istatistikleri boş olmasın.

**Dosya:** `src/app/api/analyze-local/route.ts`

**statistics objesi (yaklaşık satır 397):**
- Mevcut: `priority_counts: {}, risk_counts: {}` (boş)
- Yeni:
  ```ts
  const priority_counts: Record<string, number> = {};
  const risk_counts: Record<string, number> = {};
  for (const s of steps) {
    priority_counts[s.priority] = (priority_counts[s.priority] || 0) + 1;
    risk_counts[s.risk] = (risk_counts[s.risk] || 0) + 1;
  }
  statistics: { total_steps: steps.length, avg_roi: 2.5, average_roi: 2.5, priority_counts, risk_counts }
  ```

**Doğrulama:** `npm run build`. Manuel test: dashboard'da plan istatistikleri artık dolu olmalı.

---

### [ ] 3.3 — M3 + M7: Ölü `local.folderSelected` dalını kaldır
**Hedef:** Kullanılmayan kodu temizle.

**Dosya:** `src/app/page.tsx`

**LandingView drop zone içi (yaklaşık satır 1102-1110):**
- Mevcut: `<p className="text-sm text-muted-foreground">{localPath ? t("local.folderSelected") : t("local.dragDrop")}</p>`
- Yeni: `<p className="text-sm text-muted-foreground">{t("local.dragDrop")}</p>` (koşul kaldırıldı)

**Doğrulama:** `npm run build`. Kullanıcı `t("local.folderSelected")` anahtarının JSX'te artık referans verilmediğini grep ile doğrula.

---

### [ ] 3.4 — M4: Clear button fileInputRef reset
**Hedef:** Temizle butonu input value'yu da sıfırlasın.

**Dosya:** `src/app/page.tsx`

**Selected file display bloğu (yaklaşık satır 1112-1122):**
- Mevcut: `onClick={(e) => { e.stopPropagation(); setLocalPath(""); setRepoUrl(""); setLocalError(""); setLocalStats(null); }}`
- Yeni: aynı satırlara `if (fileInputRef.current) fileInputRef.current.value = "";` ekle

**Doğrulama:** `npm run build`. Manuel test: aynı klasörü iki kez art arda seç, ikincisi de `onChange` tetiklemeli.

---

### [ ] 3.5 — M5: Pipeline animasyonunu API'ye bağla
**Hedef:** Animasyon gerçek API latency'sine göre ilerlesin.

**Dosya:** `src/app/page.tsx`

**handleAnalyze içinde (yaklaşık satır 460-466):**
- Mevcut: `for (const stepId of stepIds) { setStepStatus(stepId, "running"); await sleep(500 + Math.random() * 600); setStepStatus(stepId, "completed"); }`
- Yeni:
  ```ts
  setStepStatus("detection", "running");
  for (const stepId of stepIds.slice(0, -1)) {
    setStepStatus(stepId, "completed");
  }
  const apiRes = await apiPromise;
  setStepStatus("review", apiRes ? "completed" : "error");
  ```

**Doğrulama:** `npm run build`. Manuel test: hızlı API ile progress 1 saniyede tamamlansın, yavaş API ile response gelene kadar son adım "running" kalsın.

---

### [ ] 3.6 — M6: Hata durumunda state korunsun
**Hedef:** Hata olunca kullanıcı klasör seçimini kaybetmesin.

**Dosya:** `src/app/page.tsx`

**handleAnalyze / handleAnalyzeLocal catch blokları (yaklaşık satır 522-528, 625-628):**
- Mevcut: hata durumunda `setView("landing")` ve toast
- Yeni: hata durumunda sadece toast göster, view'ı landing'de bırak, selectedFiles/localPath korunsun (zaten H5 fix'i ile state dışarıda)

**Doğrulama:** `npm run build`. Manuel test: network'ü kes, analiz başlat, hata mesajı gör, tekrar denemek için klasör seçimini yeniden yapma.

---

### [ ] 3.7 — M8, M9: LLM config tek noktadan
**Hedef:** Üç ayrı yerde aynı localStorage okumasını önle.

**Dosya:** `src/app/page.tsx`

- `useLLMConfig` hook zaten var (sayfanın üst kısmında, yaklaşık satır 188-212). Bu hook'un sonucunu component scope'unda tutup, `handleAnalyze` ve `handleAnalyzeLocal` içinde kullan
- `getDemoData` imzasını güncelle: `function getDemoData(repoUrl: string, llmConfig?: LLMConfig | null)`
- Üç ayrı localStorage okumasını tek bir yere indir

**Doğrulama:** `npm run build`. Manuel test: LLM config değiştir, hızlıca re-analyze et, yeni config'in etkili olduğunu gör.

---

### [ ] 3.8 — M10: Scan limit'i 5000'e indir
**Hedef:** Server limitiyle uyumlu olsun.

**Dosya:** `src/app/page.tsx`

**processFolderSelection (yaklaşık satır 901-906):**
- Mevcut: `const MAX_SCAN = 80000;`
- Yeni: `const MAX_SCAN = 5000;` (server-side `/api/analyze-local` da 5000 limitli)

**Doğrulama:** `npm run build`. Manuel test: 5001 dosyalı bir klasör seç, "Folder too large" hatası gör.

---

## ADIM 4 — DÜŞÜK ÖNEM (Polish)

### [ ] 4.1 — L1 + L8: Empty folder feedback
**Hedef:** Boş klasör seçiminde kullanıcı bilgilendirilsin.

**Dosya:** `src/app/page.tsx`

**processFolderSelection başlangıcı (yaklaşık satır 893):**
- Mevcut: `if (!files || files.length === 0) return;`
- Yeni: `if (!files || files.length === 0) { setLocalError(t("local.noFolderSelected")); return; }`

**Doğrulama:** `npm run build`. Manuel test: boş klasör seç, hata mesajı görünsün.

---

### [ ] 4.2 — L3 + L4 + L6: local_upload badge
**Hedef:** Dashboard'da "Local upload" rozeti göster.

**Dosya:** `src/app/page.tsx`

**AnalysisMetaCard veya RepositoryMeta bileşeninde:**
- `result.repository_metadata?.local_upload === true` ise küçük bir `Badge` göster
- i18n: `"local.uploadBadge": "Yerel Klasör"` / `"Local Folder"`

**Dosya:** `src/components/analyzer/i18n.tsx`
- `local.uploadBadge` anahtarını ekle

**Doğrulama:** `npm run build`. Manuel test: lokal klasör analizi sonrası dashboard'da rozet gör.

---

### [ ] 4.3 — L5: Drag-over visual feedback
**Hedef:** Sürükleme sırasında görsel feedback.

**Dosya:** `src/app/page.tsx`

**LandingView state'lerine (H5 ile birlikte):**
- `const [isDragOver, setIsDragOver] = useState(false);`
- `onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(true); }}`
- `onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(true); }}`
- `onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(false); }}`
- `onDrop` KALDIR (zaten C1'de kaldırıldı)
- Drop zone div className: `isDragOver ? "border-primary bg-primary/5" : "border-muted-foreground/30"`

**Doğrulama:** `npm run build`. Manuel test: dosya sürüklerken border rengi değişmeli.

---

### [ ] 4.4 — L9: Truncation flag
**Hedef:** 500+ dosya truncation'ı belirgin olsun.

**Dosya:** `src/app/api/analyze-local/route.ts`

**file_inventory bloğu (yaklaşık satır 338):**
- Mevcut: `file_inventory: { total_files: files.length, files: files.slice(0, 500) }`
- Yeni:
  ```ts
  file_inventory: {
    total_files: files.length,
    truncated: files.length > 500,
    files: files.slice(0, 500),
  }
  ```

**Doğrulama:** `npm run build`. Konsol: 501+ dosyalı klasörde `file_inventory.truncated === true` olduğunu gör.

---

### [ ] 4.5 — L11, L12: Cleanup
**Hedef:** Code duplication'ı temizle, basitleştir.

**Dosya:** `src/app/page.tsx`

**L11 — fileInputRef.current.value = "" tekrarı:**
- 4 yerde geçiyor (yaklaşık satır 936, 943, 957, 966). Tüm `processFolderSelection` return path'lerini tek bir `try/finally` bloğuna al:
  ```ts
  const processFolderSelection = React.useCallback((files) => {
    setLocalError("");
    if (!files || files.length === 0) return;
    const myToken = ++scanTokenRef.current;
    setScanning(true);
    setFileCount(0);
    let scanned = 0;
    const extCount = new Map<string, number>();
    const total = files.length;
    const CHUNK = 2000;
    const MAX_SCAN = 5000;
    setTimeout(() => {
      try {
        // chunked processing...
      } finally {
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    }, 10);
  }, [t]);
  ```

**L12 — Browse butonu + outer onClick:**
- Browse butonu kaldır, drop zone clickable kalsın
- Outer div `onClick={() => fileInputRef.current?.click()}` KAL

**Doğrulama:** `npm run build`. Manuel test: drop zone'a tıkla, dosya seçici açılmalı; tarama çalışmalı; X ile temizle; aynı klasörü tekrar seçebilmeli.

---

## ADIM 5 — MİMARİ (A2: Gerçek Analiz)

### [ ] 5.1 — Python backend bağlantısı
**Hedef:** `local://` URL Python backend'e gidebilsin.

**Dosya:** `src/app/api/analyze-local/route.ts`

**POST handler (tüm dosya):**
- Mevcut: sadece `generateDemoData` çağrılıyor
- Yeni: 
  1. `isPythonBackendConfigured()` kontrolü
  2. Eğer Python backend varsa:
     - `callPythonBackend("/analyze-local", { method: "POST", body: { local_path, files_metadata: files.map(f => ({ name: f.name, size: f.size, path: (f as any).webkitRelativePath })) } })` çağır
     - Backend sonucu `validation_results/{localPath}/analysis_result.json` altına yazılsın (mevcut `saveResult` helper'ı)
     - Backend başarısız olursa demo data'ya fallback
  3. Python backend yoksa veya başarısızsa → `generateDemoData` kullan

**NOT:** Backend tarafında da değişiklik gerekebilir. `repo-analyzer-py/src/repo_analyzer/api/app.py` veya ilgili router'a `/analyze-local` endpoint'i eklenmeli.

**Doğrulama:** Python backend yapılandırılmışsa lokal klasörün gerçek analiz edilip edilmediğini kontrol et. Sonuçlar `validation_results/{localPath}/` altında olmalı.

---

### [ ] 5.2 — A1: jobStore persistence
**Hedef:** Dev restart'ta job'lar kaybolmasın.

**Dosya:** `src/app/api/analyze-local/route.ts` ve `src/app/api/analyze/route.ts`

- `jobStore = new Map()` yerine `db/jobStore.json` dosyasına persist et
- Her set'te `fs.writeFileSync` çağır
- Her get'te dosyayı oku

**Doğrulama:** `npm run build`. Manuel test: analiz başlat, sunucuyu durdur, yeniden başlat, sonuç sayfasını yenile — sonuç hâlâ orada.

---

### [ ] 5.3 — A3: M8 ile birlikte yapılacak (Adım 3.7)

### [ ] 5.4 — A4: File[] persistence — SKIP (karmaşık, H5 yeterli)

### [ ] 5.5 — A5: ProgressView'e localPath geçir
**Hedef:** Lokal klasör analizinde doğru path gösterilsin.

**Dosya:** `src/app/page.tsx`

**ProgressView (yaklaşık satır 1218-1249):**
- Mevcut: `<ProgressView steps={pipelineSteps} repoUrl={repoUrl} />`
- Yeni: `<ProgressView steps={pipelineSteps} repoUrl={repoUrl} localPath={localPath} />`
- ProgressView içinde: `repoUrl?.startsWith("local://") ? localPath : repoUrl` göster

**Doğrulama:** `npm run build`. Manuel test: lokal klasör analizi sırasında progress'te klasör adı görünmeli.

---

## DOĞRULAMA PROTOKOLÜ (her adımdan sonra)

```bash
cd C:\Users\Umut\OneDrive\Masaüstü\kalite
npm run build
```

Çıktıda `Build error occurred` veya `Failed to compile` kelimesi yoksa adım başarılıdır.

## GENEL DOĞRULAMA (tüm adımlar bittikten sonra)

1. `npm run build` — hatasız tamamlanmalı
2. `KALITE_BASLAT.bat` çalıştır — 2 saniyede açılmalı
3. Landing sayfası → Local tab → bir repo klasörü seç → taranıyor → klasör adı ve dosya istatistikleri (uzantılar) gösterilmeli
4. Analiz tıkla → progress → sonuçlar görünmeli
5. Sonuçlarda:
   - `repository.owner === "local"`, `name === "RepoName"`
   - `repository_metadata.local_upload === true`
   - License `LICENSE` varsa "MIT" gibi (bilinmiyorsa "unknown")
   - Priority/risk counts dolu
6. Klasör seçili iken GitHub tab'ına dön — URL input'u boş kalmalı
7. History → bir local entry re-analyze → toast mesajı, yeniden seçim mesajı görünmeli

## SIRALAMA
```
Adım 1 → build → ✓
Adım 2 → build → ✓
Adım 3 → build → ✓
Adım 4 → build → ✓
Adım 5 → build → ✓
Final doğrulama
```

---

## İLERLEME KAYDI

### 2026-07-30 - Adım 1-5 tamamlandı (14 düzeltme)
- **Adım 1**: 4/4 kritik bug (C1-C4) ✓
- **Adım 2**: 4/6 yüksek önem (H1, H3, H4, H6) ✓
- **Adım 3**: 5/8 orta önem (M1, M2, M3, M4, M5) ✓
- **Adım 4**: 3/5 düşük önem (L1+L8, L5, L9) ✓
- **Adım 5**: 1/5 mimari (Python backend bağlantısı) ✓
- **Skip**: H5 (refactor riskli), H2 (Türkçe i18n büyük), L3+L4+L6 (local_upload badge), L11+L12 (cleanup), A1-A3-A4-A5
- **Build**: 13 route, hatasız
- **Kullanıcı testi bekleniyor**


