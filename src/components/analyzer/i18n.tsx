"use client";

import * as React from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Language = "tr" | "en";

export interface TranslationDict {
  [key: string]: string;
}

// ---------------------------------------------------------------------------
// Translations
// ---------------------------------------------------------------------------

const translations: Record<Language, TranslationDict> = {
  en: {
    // App
    "app.title": "AI Software Architect",
    "app.subtitle": "Analyze repositories.\nUnderstand architecture.\nDiscover root causes.\nGenerate engineering roadmaps.",
    "app.analyze": "Analyze Repository",
    "app.uploadLocal": "Upload Local Repository",
    "app.comingSoon": "Coming Soon",
    "app.newAnalysis": "New Analysis",

    // Nav
    "nav.settings": "Settings",
    "nav.language": "Language",

    // Landing
    "landing.placeholder": "https://github.com/owner/repository",
    "landing.enterUrl": "Please enter a repository URL",

    // Pipeline
    "pipeline.analyzing": "Analyzing Repository",
    "pipeline.detection": "Repository Detection",
    "pipeline.language": "Language Analysis",
    "pipeline.dependency": "Dependency Analysis",
    "pipeline.metrics": "Metrics & Complexity",
    "pipeline.evidence": "Evidence Collection",
    "pipeline.graph": "Knowledge Graph",
    "pipeline.rootcause": "Root Cause Detection",
    "pipeline.planning": "Planning Engine",
    "pipeline.review": "Engineering Review",

    // Dashboard
    "dashboard.health": "Repository Health",
    "dashboard.overview": "Overview",
    "dashboard.rootCauses": "Root Causes",
    "dashboard.roadmap": "Roadmap",
    "dashboard.evidence": "Evidence",
    "dashboard.graph": "Graph",
    "dashboard.files": "Files",
    "dashboard.aiReview": "AI Review",

    // Stats
    "stats.rootCauses": "Root Causes",
    "stats.evidenceItems": "Evidence Items",
    "stats.quickWins": "Quick Wins",
    "stats.planSteps": "Plan Steps",
    "stats.avgRoi": "Avg ROI",
    "stats.aiReview": "AI Review",
    "stats.architecturalIssues": "architectural issues",
    "stats.totalFindings": "total findings",
    "stats.lowEffortFixes": "low-effort fixes",
    "stats.refactoringSteps": "refactoring steps",
    "stats.returnOnInvestment": "return on investment",
    "stats.noReview": "no review",

    // Health
    "health.security": "Security",
    "health.architecture": "Architecture",
    "health.quality": "Quality",
    "health.testing": "Testing",
    "health.docs": "Docs",
    "health.commits": "commits",
    "health.contributors": "contributors",

    // Root Causes
    "rootCause.confidence": "Confidence",
    "rootCause.evidence": "evidence",
    "rootCause.files": "files",
    "rootCause.technicalRationale": "Technical Rationale",
    "rootCause.likelyOrigin": "Likely Origin",
    "rootCause.affectedFiles": "Affected Files",
    "rootCause.viewDetails": "View Details",
    "rootCause.noRootCauses": "No root causes detected",
    "rootCause.structurallySound": "The repository appears structurally sound.",

    // Roadmap
    "roadmap.sprintRoadmap": "Sprint Roadmap",
    "roadmap.quickWins": "Quick Wins",
    "roadmap.critical": "Critical",
    "roadmap.highPriority": "High Priority",
    "roadmap.mediumPriority": "Medium Priority",
    "roadmap.lowPriority": "Low Priority",
    "roadmap.noPlan": "No engineering plan available",
    "roadmap.roi": "Return",
    "roadmap.effort": "Effort",
    "roadmap.estimated": "estimated",

    // Evidence
    "evidence.search": "Search evidence...",
    "evidence.allSeverities": "All Severities",
    "evidence.severity": "Severity",
    "evidence.analyzer": "Analyzer",
    "evidence.category": "Category",
    "evidence.message": "Message",
    "evidence.file": "File",
    "evidence.confidence": "Conf.",
    "evidence.type": "Type",
    "evidence.noEvidence": "No evidence collected",
    "evidence.ofItems": "of",
    "evidence.evidenceItems": "evidence items",

    // Graph
    "graph.title": "Engineering Knowledge Graph",
    "graph.nodes": "nodes",
    "graph.edges": "edges",
    "graph.nodeDetails": "Node Details",
    "graph.clickNode": "Click a node to see details.",
    "graph.noGraph": "No graph data available",

    // Files
    "files.title": "Files",
    "files.selectFile": "Select a file",
    "files.selectPrompt": "Select a file to see its evidence and root causes.",
    "files.evidence": "Evidence",
    "files.rootCauses": "Root Causes",
    "files.noEvidence": "No evidence for this file.",
    "files.noRootCauses": "No root causes for this file.",
    "files.noInventory": "No file inventory available",

    // AI Review
    "ai.offlineMode": "Offline mode — this review was produced without an LLM. Enable a provider for richer analysis.",
    "ai.keySavedMode": "Your API key is saved. Run a new analysis to generate an LLM-powered review.",
    "ai.supportedByEvidence": "Supported by Evidence",
    "ai.aiOpinion": "AI Opinion",
    "ai.challenges": "Planning Engine Challenges",
    "ai.noReview": "No AI review available",
    "ai.enableProvider": "Enable an LLM provider for AI-generated review.",

    // Explainability
    "explainability.chain": "EXPLAINABILITY CHAIN",
    "explainability.why": "WHY?",
    "explainability.recommendation": "Recommendation",
    "explainability.rootCause": "Root Cause",
    "explainability.evidence": "Evidence",
    "explainability.analyzer": "Analyzer",
    "explainability.affectedFile": "Affected File",
    "explainability.metric": "Metric",
    "explainability.estimatedEffort": "Estimated Effort",
    "explainability.riskLevel": "Risk Level",
    "explainability.category": "Category",
    "explainability.evidenceCount": "Evidence Count",

    // Trust Panel
    "trust.title": "Trust Panel",
    "trust.trustScore": "Trust Score",
    "trust.confidence": "Confidence",
    "trust.evidenceCount": "Evidence Count",
    "trust.analyzerCount": "Analyzer Count",
    "trust.reasoningDepth": "Reasoning Depth",
    "trust.hallucinationRisk": "Hallucination Risk",
    "trust.llmStatus": "LLM Status",
    "trust.active": "Active",
    "trust.ready": "Ready",
    "trust.offline": "Offline",
    "trust.low": "Low",
    "trust.medium": "Medium",
    "trust.high": "High",

    // LLM Status
    "llm.provider": "Provider",
    "llm.model": "Model",
    "llm.temperature": "Temperature",
    "llm.status": "LLM Status",
    "llm.estimatedTokens": "Estimated Tokens",
    "llm.analysisTime": "Analysis Time",
    "llm.ready": "Ready",
    "llm.readyHint": "API key saved — will be used on the next analysis",
    "llm.noKey": "No API key configured",
    "llm.configureInSettings": "Configure in Settings",
    "llm.usingSavedProvider": "Using saved provider",
    "llm.lastUsed": "Last used",

    // Settings
    "settings.title": "Settings",
    "settings.general": "General",
    "settings.llm": "LLM",
    "settings.appearance": "Appearance",
    "settings.language": "Language",
    "settings.about": "About",

    // Settings - LLM
    "settings.llm.provider": "Provider",
    "settings.llm.apiKey": "API Key",
    "settings.llm.model": "Model",
    "settings.llm.temperature": "Temperature",
    "settings.llm.maxTokens": "Max Tokens",
    "settings.llm.baseUrl": "Base URL",
    "settings.llm.endpoint": "Endpoint",
    "settings.llm.deployment": "Deployment",
    "settings.llm.apiVersion": "API Version",
    "settings.llm.host": "Host",
    "settings.llm.port": "Port",
    "settings.llm.testConnection": "Test Connection",
    "settings.llm.connected": "✓ Connected",
    "settings.llm.connectionFailed": "Connection failed",
    "settings.llm.save": "Save",
    "settings.llm.saved": "✓ Configuration saved",
    "settings.llm.deleted": "Configuration deleted",
    "settings.llm.emptyKey": "Please enter an API key before saving",
    "settings.llm.emptyProvider": "Please select a provider first",
    "settings.llm.delete": "Delete",
    "settings.llm.copy": "Copy",
    "settings.llm.reveal": "Reveal",
    "settings.llm.hide": "Hide",
    "settings.llm.defaultProvider": "Default Provider",
    "settings.llm.defaultModel": "Default Model",
    "settings.llm.defaultTemp": "Default Temperature",
    "settings.llm.noProviderSelected": "Select a provider to configure",

    // Settings - Appearance
    "settings.appearance.theme": "Theme",
    "settings.appearance.darkMode": "Dark Mode",
    "settings.appearance.lightMode": "Light Mode",
    "settings.appearance.system": "System",

    // Settings - About
    "settings.about.version": "Version",
    "settings.about.description": "AI Software Architect — Professional repository analyzer with evidence-based root cause detection and engineering roadmap generation.",

    // Report
    "report.export": "Export Report",
    "report.exported": "Report exported as",
    "report.exportFailed": "Export failed",

    // Tabs
    "tabs.github": "GitHub Repository",
    "tabs.local": "Local Folder",

    // Common
    "common.search": "Search...",
    "common.close": "Close",
    "common.save": "Save",
    "common.cancel": "Cancel",
    "common.delete": "Delete",
    "common.copy": "Copy",
    "common.copied": "Copied!",
    "common.copyMarkdown": "Copy as Markdown",
    "common.loading": "Loading...",
    "common.noData": "No data available",
    "common.error": "Something went wrong",
    "common.retry": "Retry",

    // Analysis
    "analysis.complete": "Analysis complete!",
    "analysis.demoMode": "Showing demo results (API unavailable)",
    "analysis.failed": "Analysis failed",

    // Charts
    "charts.severityDistribution": "Severity Distribution",
    "charts.confidenceByRootCause": "Confidence by Root Cause",
    "charts.categoryBreakdown": "Category Breakdown",
    "charts.critical": "Critical",
    "charts.count": "count",

    // Filters (Root Causes)
    "filter.title": "Filters",
    "filter.allSeverities": "All Severities",
    "filter.allCategories": "All Categories",
    "filter.sortBy": "Sort by",
    "filter.sort.confidence": "Confidence (high → low)",
    "filter.sort.severity": "Severity (critical → low)",
    "filter.sort.evidence": "Evidence count (most → least)",
    "filter.searchPlaceholder": "Search root causes...",
    "filter.results": "{count} of {total} root causes",
    "filter.noMatch": "No root causes match the current filters",
    "filter.clear": "Clear filters",

    // Analysis Meta
    "meta.title": "Analysis Meta",
    "meta.repository": "Repository",
    "meta.jobId": "Job ID",
    "meta.analyzedAt": "Analyzed at",
    "meta.phases": "Phases",
    "meta.files": "Files",
    "meta.languages": "Languages",

    // Keyboard Shortcuts
    "shortcuts.title": "Keyboard Shortcuts",
    "shortcuts.openHelp": "Open this help",
    "shortcuts.switchTab": "Switch tab (1-7)",
    "shortcuts.focusSearch": "Focus search",
    "shortcuts.closeDialog": "Close dialog",
    "shortcuts.toggleTheme": "Toggle theme",
  },

  tr: {
    // App
    "app.title": "AI Yazılım Mimarı",
    "app.subtitle": "Depoları analiz et.\nMimariyi anla.\nKök nedenleri keşfet.\nMühendislik yol haritaları üret.",
    "app.analyze": "Depoyu Analiz Et",
    "app.uploadLocal": "Yerel Depo Yükle",
    "app.comingSoon": "Yakında",
    "app.newAnalysis": "Yeni Analiz",

    // Nav
    "nav.settings": "Ayarlar",
    "nav.language": "Dil",

    // Landing
    "landing.placeholder": "https://github.com/kullanici/depo",
    "landing.enterUrl": "Lütfen bir depo URL'i girin",

    // Pipeline
    "pipeline.analyzing": "Depo Analiz Ediliyor",
    "pipeline.detection": "Depo Tespiti",
    "pipeline.language": "Dil Analizi",
    "pipeline.dependency": "Bağımlılık Analizi",
    "pipeline.metrics": "Metrikler & Karmaşıklık",
    "pipeline.evidence": "Kanıt Toplama",
    "pipeline.graph": "Bilgi Grafiği",
    "pipeline.rootcause": "Kök Neden Tespiti",
    "pipeline.planning": "Planlama Motoru",
    "pipeline.review": "Mühendislik İncelemesi",

    // Dashboard
    "dashboard.health": "Depo Sağlığı",
    "dashboard.overview": "Genel Bakış",
    "dashboard.rootCauses": "Kök Nedenler",
    "dashboard.roadmap": "Yol Haritası",
    "dashboard.evidence": "Kanıtlar",
    "dashboard.graph": "Graf",
    "dashboard.files": "Dosyalar",
    "dashboard.aiReview": "AI İncelemesi",

    // Stats
    "stats.rootCauses": "Kök Nedenler",
    "stats.evidenceItems": "Kanıt Öğeleri",
    "stats.quickWins": "Hızlı Kazanımlar",
    "stats.planSteps": "Plan Adımları",
    "stats.avgRoi": "Ort. ROI",
    "stats.aiReview": "AI İncelemesi",
    "stats.architecturalIssues": "mimari sorun",
    "stats.totalFindings": "toplam bulgu",
    "stats.lowEffortFixes": "düşük eforlu düzeltme",
    "stats.refactoringSteps": "yeniden düzenleme adımı",
    "stats.returnOnInvestment": "yatırım getirisi",
    "stats.noReview": "inceleme yok",

    // Health
    "health.security": "Güvenlik",
    "health.architecture": "Mimari",
    "health.quality": "Kalite",
    "health.testing": "Test",
    "health.docs": "Doküman",
    "health.commits": "commit",
    "health.contributors": "katkıda bulunan",

    // Root Causes
    "rootCause.confidence": "Güven",
    "rootCause.evidence": "kanıt",
    "rootCause.files": "dosya",
    "rootCause.technicalRationale": "Teknik Gerekçe",
    "rootCause.likelyOrigin": "Olası Köken",
    "rootCause.affectedFiles": "Etkilenen Dosyalar",
    "rootCause.viewDetails": "Detayları Gör",
    "rootCause.noRootCauses": "Kök neden tespit edilmedi",
    "rootCause.structurallySound": "Depo yapısal olarak sağlıklı görünüyor.",

    // Roadmap
    "roadmap.sprintRoadmap": "Sprint Yol Haritası",
    "roadmap.quickWins": "Hızlı Kazanımlar",
    "roadmap.critical": "Kritik",
    "roadmap.highPriority": "Yüksek Öncelik",
    "roadmap.mediumPriority": "Orta Öncelik",
    "roadmap.lowPriority": "Düşük Öncelik",
    "roadmap.noPlan": "Mühendislik planı mevcut değil",
    "roadmap.roi": "Getiri",
    "roadmap.effort": "Efor",
    "roadmap.estimated": "tahmini",

    // Evidence
    "evidence.search": "Kanıt ara...",
    "evidence.allSeverities": "Tüm Önem Seviyeleri",
    "evidence.severity": "Önem",
    "evidence.analyzer": "Analizör",
    "evidence.category": "Kategori",
    "evidence.message": "Mesaj",
    "evidence.file": "Dosya",
    "evidence.confidence": "Güven",
    "evidence.type": "Tip",
    "evidence.noEvidence": "Kanıt toplanmadı",
    "evidence.ofItems": "/",
    "evidence.evidenceItems": "kanıt öğesi",

    // Graph
    "graph.title": "Mühendislik Bilgi Grafiği",
    "graph.nodes": "düğüm",
    "graph.edges": "kenar",
    "graph.nodeDetails": "Düğüm Detayları",
    "graph.clickNode": "Detayları görmek için bir düğüme tıklayın.",
    "graph.noGraph": "Graf verisi mevcut değil",

    // Files
    "files.title": "Dosyalar",
    "files.selectFile": "Dosya seçin",
    "files.selectPrompt": "Kanıt ve kök nedenleri görmek için bir dosya seçin.",
    "files.evidence": "Kanıtlar",
    "files.rootCauses": "Kök Nedenler",
    "files.noEvidence": "Bu dosya için kanıt yok.",
    "files.noRootCauses": "Bu dosya için kök neden yok.",
    "files.noInventory": "Dosya envanteri mevcut değil",

    // AI Review
    "ai.offlineMode": "Çevrimdışı mod — bu inceleme LLM olmadan üretildi. Daha zengin analiz için bir sağlayıcı etkinleştirin.",
    "ai.keySavedMode": "API anahtarınız kaydedildi. LLM destekli inceleme üretmek için yeni bir analiz çalıştırın.",
    "ai.supportedByEvidence": "Kanıt Destekli",
    "ai.aiOpinion": "AI Görüşü",
    "ai.challenges": "Planlama Motoru Eleştirileri",
    "ai.noReview": "AI incelemesi mevcut değil",
    "ai.enableProvider": "AI tarafından oluşturulan inceleme için bir LLM sağlayıcı etkinleştirin.",

    // Explainability
    "explainability.chain": "AÇIKLANABİLİRLİK ZİNCİRİ",
    "explainability.why": "NEDEN?",
    "explainability.recommendation": "Öneri",
    "explainability.rootCause": "Kök Neden",
    "explainability.evidence": "Kanıt",
    "explainability.analyzer": "Analizör",
    "explainability.affectedFile": "Etkilenen Dosya",
    "explainability.metric": "Metrik",
    "explainability.estimatedEffort": "Tahmini Efor",
    "explainability.riskLevel": "Risk Seviyesi",
    "explainability.category": "Kategori",
    "explainability.evidenceCount": "Kanıt Sayısı",

    // Trust Panel
    "trust.title": "Güven Paneli",
    "trust.trustScore": "Güven Skoru",
    "trust.confidence": "Güven",
    "trust.evidenceCount": "Kanıt Sayısı",
    "trust.analyzerCount": "Analizör Sayısı",
    "trust.reasoningDepth": "Akıl Yürütme Derinliği",
    "trust.hallucinationRisk": "Halüsinasyon Riski",
    "trust.llmStatus": "LLM Durumu",
    "trust.active": "Aktif",
    "trust.ready": "Hazır",
    "trust.offline": "Çevrimdışı",
    "trust.low": "Düşük",
    "trust.medium": "Orta",
    "trust.high": "Yüksek",

    // LLM Status
    "llm.provider": "Sağlayıcı",
    "llm.model": "Model",
    "llm.temperature": "Sıcaklık",
    "llm.status": "LLM Durumu",
    "llm.estimatedTokens": "Tahmini Token",
    "llm.analysisTime": "Analiz Süresi",
    "llm.ready": "Hazır",
    "llm.readyHint": "API anahtarı kaydedildi — bir sonraki analizde kullanılacak",
    "llm.noKey": "API anahtarı yapılandırılmadı",
    "llm.configureInSettings": "Ayarlar'dan yapılandır",
    "llm.usingSavedProvider": "Kayıtlı sağlayıcı kullanılıyor",
    "llm.lastUsed": "Son kullanım",

    // Settings
    "settings.title": "Ayarlar",
    "settings.general": "Genel",
    "settings.llm": "LLM",
    "settings.appearance": "Görünüm",
    "settings.language": "Dil",
    "settings.about": "Hakkında",

    // Settings - LLM
    "settings.llm.provider": "Sağlayıcı",
    "settings.llm.apiKey": "API Anahtarı",
    "settings.llm.model": "Model",
    "settings.llm.temperature": "Sıcaklık",
    "settings.llm.maxTokens": "Maks. Token",
    "settings.llm.baseUrl": "Temel URL",
    "settings.llm.endpoint": "Endpoint",
    "settings.llm.deployment": "Deployment",
    "settings.llm.apiVersion": "API Sürümü",
    "settings.llm.host": "Host",
    "settings.llm.port": "Port",
    "settings.llm.testConnection": "Bağlantıyı Test Et",
    "settings.llm.connected": "✓ Bağlandı",
    "settings.llm.connectionFailed": "Bağlantı başarısız",
    "settings.llm.save": "Kaydet",
    "settings.llm.saved": "✓ Yapılandırma kaydedildi",
    "settings.llm.deleted": "Yapılandırma silindi",
    "settings.llm.emptyKey": "Kaydetmeden önce lütfen bir API anahtarı girin",
    "settings.llm.emptyProvider": "Lütfen önce bir sağlayıcı seçin",
    "settings.llm.delete": "Sil",
    "settings.llm.copy": "Kopyala",
    "settings.llm.reveal": "Göster",
    "settings.llm.hide": "Gizle",
    "settings.llm.defaultProvider": "Varsayılan Sağlayıcı",
    "settings.llm.defaultModel": "Varsayılan Model",
    "settings.llm.defaultTemp": "Varsayılan Sıcaklık",
    "settings.llm.noProviderSelected": "Yapılandırmak için bir sağlayıcı seçin",

    // Settings - Appearance
    "settings.appearance.theme": "Tema",
    "settings.appearance.darkMode": "Karanlık Tema",
    "settings.appearance.lightMode": "Aydınlık Tema",
    "settings.appearance.system": "Sistem",

    // Settings - About
    "settings.about.version": "Sürüm",
    "settings.about.description": "AI Yazılım Mimarı — Kanıta dayalı kök neden tespiti ve mühendislik yol haritası üretimi ile profesyonel depo analiz aracı.",

    // Report
    "report.export": "Raporu Dışa Aktar",
    "report.exported": "Rapor dışa aktarıldı:",
    "report.exportFailed": "Dışa aktarma başarısız",

    // Tabs
    "tabs.github": "GitHub Deposu",
    "tabs.local": "Yerel Klasör",

    // Common
    "common.search": "Ara...",
    "common.close": "Kapat",
    "common.save": "Kaydet",
    "common.cancel": "İptal",
    "common.delete": "Sil",
    "common.copy": "Kopyala",
    "common.copied": "Kopyalandı!",
    "common.copyMarkdown": "Markdown olarak kopyala",
    "common.loading": "Yükleniyor...",
    "common.noData": "Veri mevcut değil",
    "common.error": "Bir şeyler ters gitti",
    "common.retry": "Tekrar dene",

    // Analysis
    "analysis.complete": "Analiz tamamlandı!",
    "analysis.demoMode": "Demo sonuçları gösteriliyor (API erişilemez)",
    "analysis.failed": "Analiz başarısız",

    // Charts
    "charts.severityDistribution": "Önem Dağılımı",
    "charts.confidenceByRootCause": "Kök Nedenlere Göre Güven",
    "charts.categoryBreakdown": "Kategori Dağılımı",
    "charts.critical": "Kritik",
    "charts.count": "adet",

    // Filters (Root Causes)
    "filter.title": "Filtreler",
    "filter.allSeverities": "Tüm Önem Seviyeleri",
    "filter.allCategories": "Tüm Kategoriler",
    "filter.sortBy": "Sırala",
    "filter.sort.confidence": "Güven (yüksek → düşük)",
    "filter.sort.severity": "Önem (kritik → düşük)",
    "filter.sort.evidence": "Kanıt sayısı (çok → az)",
    "filter.searchPlaceholder": "Kök neden ara...",
    "filter.results": "{total} kök nedenin {count} tanesi",
    "filter.noMatch": "Mevcut filtrelere uyan kök neden yok",
    "filter.clear": "Filtreleri temizle",

    // Analysis Meta
    "meta.title": "Analiz Meta",
    "meta.repository": "Depo",
    "meta.jobId": "İş ID",
    "meta.analyzedAt": "Analiz zamanı",
    "meta.phases": "Fazlar",
    "meta.files": "Dosyalar",
    "meta.languages": "Diller",

    // Keyboard Shortcuts
    "shortcuts.title": "Klavye Kısayolları",
    "shortcuts.openHelp": "Bu yardımı aç",
    "shortcuts.switchTab": "Sekme değiştir (1-7)",
    "shortcuts.focusSearch": "Arama odakla",
    "shortcuts.closeDialog": "Diyalog kapat",
    "shortcuts.toggleTheme": "Tema değiştir",
  },
};

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface LanguageContextValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = React.createContext<LanguageContextValue>({
  lang: "en",
  setLang: () => {},
  t: (key: string) => key,
});

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = React.useState<Language>("en");

  React.useEffect(() => {
    const saved = localStorage.getItem("ra-language") as Language | null;
    if (saved === "tr" || saved === "en") {
      setLangState(saved);
    }
  }, []);

  const setLang = React.useCallback((newLang: Language) => {
    setLangState(newLang);
    localStorage.setItem("ra-language", newLang);
  }, []);

  const t = React.useCallback(
    (key: string) => {
      return translations[lang][key] ?? translations.en[key] ?? key;
    },
    [lang]
  );

  const value = React.useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useI18n() {
  return React.useContext(LanguageContext);
}
