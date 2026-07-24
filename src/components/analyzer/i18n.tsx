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

    // Graph controls
    "graph.zoomIn": "Zoom in",
    "graph.zoomOut": "Zoom out",
    "graph.reset": "Reset view",
    "graph.highlightConnected": "Connected nodes",
    "graph.noConnected": "No connected nodes",
    "graph.edges": "edges",
    "graph.fit": "Fit to screen",
    "graph.legend": "Legend",
    "graph.search": "Search nodes...",
    "graph.edgeLegend": "Edges",
    "graph.edgeAffects": "Affects (strong)",
    "graph.edgeBelongsTo": "Belongs to (weak)",

    // Files extras
    "files.search": "Filter files...",
    "files.size": "Size",
    "files.type": "Type",
    "files.items": "items",
    "files.preview": "Repository overview",
    "files.previewDesc": "Select a file to inspect its evidence, root causes, and graph connections.",
    "files.totalFiles": "Total files",
    "files.totalSize": "Total size",
    "files.rootCauses": "Root causes",
    "files.recommendations": "Recommendations",
    "files.graphConnections": "Graph connections",
    "files.evidenceCount": "Evidence count",
    "files.topFiles": "Top files by evidence",

    // Evidence — sortable columns
    "evidence.sortBy": "Click to sort by {col}",
    "evidence.sorted": "Sorted by {col} ({dir})",

    // Roadmap filters
    "roadmap.filterPriority": "Priority",
    "roadmap.filterRisk": "Risk",
    "roadmap.filterSprint": "Sprint",
    "roadmap.allPriorities": "All Priorities",
    "roadmap.allRisks": "All Risks",
    "roadmap.allSprints": "All Sprints",
    "roadmap.results": "{count} of {total} steps",
    "roadmap.clearFilters": "Clear filters",

    // Landing — feature cards + how it works
    "landing.featuresTitle": "What you get",
    "landing.featuresSubtitle": "A complete engineering intelligence report for any repository.",
    "landing.feature.rootCausesTitle": "Root Cause Detection",
    "landing.feature.rootCausesDesc": "Evidence-based detection of architectural root causes — not just symptoms.",
    "landing.feature.graphTitle": "Knowledge Graph",
    "landing.feature.graphDesc": "Interactive visualization of files, classes, modules, and their dependencies.",
    "landing.feature.roadmapTitle": "Engineering Roadmap",
    "landing.feature.roadmapDesc": "Prioritized, sprint-ready refactoring plan with ROI estimates and risks.",
    "landing.feature.explainabilityTitle": "Explainability Chains",
    "landing.feature.explainabilityDesc": "Every recommendation traces back to evidence, analyzers, and source files.",
    "landing.feature.trustTitle": "Trust Panel",
    "landing.feature.trustDesc": "Confidence, evidence count, reasoning depth, and hallucination risk metrics.",
    "landing.feature.aiTitle": "AI Engineering Review",
    "landing.feature.aiDesc": "Optional LLM-powered review that challenges the plan and surfaces trade-offs.",
    "landing.howItWorks": "How it works",
    "landing.howItWorks.step1Title": "Enter a repository URL",
    "landing.howItWorks.step1Desc": "Paste any public GitHub repository URL and hit Analyze.",
    "landing.howItWorks.step2Title": "Pipeline runs 9 phases",
    "landing.howItWorks.step2Desc": "Detection, metrics, evidence, graph, root causes, planning, and review.",
    "landing.howItWorks.step3Title": "Explore the dashboard",
    "landing.howItWorks.step3Desc": "Drill into root causes, roadmap, evidence, graph, files, and AI review.",
    "landing.exampleRepos": "Try an example:",

    // History drawer
    "history.title": "Analysis History",
    "history.empty": "No analyses yet. Run your first analysis to see it here.",
    "history.reopen": "Reopen",
    "history.remove": "Remove",
    "history.clearAll": "Clear all",
    "history.count": "{count} analyses",
    "history.demoBadge": "demo",
    "history.justNow": "just now",
    "history.minutesAgo": "{m}m ago",
    "history.hoursAgo": "{h}h ago",
    "history.exportJson": "Export all (JSON)",
    "history.exportedJson": "History exported as JSON",
    "history.fullBackup": "Full backup (with results)",
    "history.exportedFull": "Full backup exported as JSON",
    "history.reanalyze": "Re-analyze",
    "history.reanalyzing": "Re-analyzing…",
    "health.grade": "Grade",

    // Settings extras
    "settings.back": "Back",
    "settings.llm.providerCards": "Choose a provider",
    "settings.llm.providerHelp": "Select a provider to enable AI-powered engineering review. Your key is stored locally in this browser.",
    "settings.llm.status": "Status",

    // Compare view
    "compare.title": "Compare Analyses",
    "compare.current": "Current",
    "compare.baseline": "Baseline",
    "compare.selectBaseline": "Select a baseline to compare",
    "compare.healthScores": "Health Scores",
    "compare.rootCauses": "Root Causes",
    "compare.delta": "Δ",
    "compare.improved": "improved",
    "compare.regressed": "regressed",
    "compare.unchanged": "unchanged",
    "compare.new": "new",
    "compare.gone": "gone",
    "compare.noBaseline": "Run another analysis or reopen a history entry, then select it as a baseline here.",
    "compare.better": "better",
    "compare.worse": "worse",
    "compare.same": "same",
    "compare.close": "Close comparison",
    "compare.evidence": "Evidence",
    "compare.roadmap": "Roadmap Steps",
    "compare.quickWins": "Quick Wins",

    // AI Review — parsed ROI fields
    "ai.roi": "ROI",
    "ai.priority": "Priority",
    "ai.estimate": "Estimate",
    "ai.step": "Step",

    // Footer
    "footer.builtWith": "Built with Next.js, TypeScript, Tailwind CSS, and shadcn/ui",
    "footer.shortcutsHint": "Press",
    "footer.toSeeShortcuts": "for keyboard shortcuts",
    "footer.copyright": "AI Software Architect",
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

    // Graph controls
    "graph.zoomIn": "Yakınlaş",
    "graph.zoomOut": "Uzaklaş",
    "graph.reset": "Sıfırla",
    "graph.highlightConnected": "Bağlı düğümler",
    "graph.noConnected": "Bağlı düğüm yok",
    "graph.edges": "kenar",
    "graph.fit": "Ekrana sığdır",
    "graph.legend": "Lejant",
    "graph.search": "Düğüm ara...",
    "graph.edgeLegend": "Kenarlar",
    "graph.edgeAffects": "Etkiler (güçlü)",
    "graph.edgeBelongsTo": "Ait (zayıf)",

    // Files extras
    "files.search": "Dosya filtrele...",
    "files.size": "Boyut",
    "files.type": "Tip",
    "files.items": "öğe",
    "files.preview": "Depo özeti",
    "files.previewDesc": "Kanıt, kök neden ve graf bağlantılarını incelemek için bir dosya seçin.",
    "files.totalFiles": "Toplam dosya",
    "files.totalSize": "Toplam boyut",
    "files.rootCauses": "Kök nedenler",
    "files.recommendations": "Öneriler",
    "files.graphConnections": "Graf bağlantıları",
    "files.evidenceCount": "Kanıt sayısı",
    "files.topFiles": "Kanıta göre en çok dosyalar",

    // Kanıtlar — sıralanabilir kolonlar
    "evidence.sortBy": "{col} ile sıralamak için tıklayın",
    "evidence.sorted": "{col} ({dir}) göre sıralı",

    // Roadmap filters
    "roadmap.filterPriority": "Öncelik",
    "roadmap.filterRisk": "Risk",
    "roadmap.filterSprint": "Sprint",
    "roadmap.allPriorities": "Tüm Öncelikler",
    "roadmap.allRisks": "Tüm Riskler",
    "roadmap.allSprints": "Tüm Sprintler",
    "roadmap.results": "{total} adımın {count} tanesi",
    "roadmap.clearFilters": "Filtreleri temizle",

    // Landing — özellik kartları + nasıl çalışır
    "landing.featuresTitle": "Neler sunuluyor",
    "landing.featuresSubtitle": "Herhangi bir depo için eksiksiz mühendislik zekası raporu.",
    "landing.feature.rootCausesTitle": "Kök Neden Tespiti",
    "landing.feature.rootCausesDesc": "Sadece belirtiler değil, mimari kök nedenlerin kanıta dayalı tespiti.",
    "landing.feature.graphTitle": "Bilgi Grafiği",
    "landing.feature.graphDesc": "Dosya, sınıf, modül ve bağımlılıkların etkileşimli görselleştirmesi.",
    "landing.feature.roadmapTitle": "Mühendislik Yol Haritası",
    "landing.feature.roadmapDesc": "Önceliklendirilmiş, sprint hazır yeniden düzenleme planı, ROI ve risklerle.",
    "landing.feature.explainabilityTitle": "Açıklanabilirlik Zincirleri",
    "landing.feature.explainabilityDesc": "Her öneri kanıta, analizör ve kaynak dosyalara kadar izlenebilir.",
    "landing.feature.trustTitle": "Güven Paneli",
    "landing.feature.trustDesc": "Güven, kanıt sayısı, akıl yürütme derinliği ve halüsinasyon riski metrikleri.",
    "landing.feature.aiTitle": "AI Mühendislik İncelemesi",
    "landing.feature.aiDesc": "Planı eleştiren ve trade-off'ları ortaya çıkaran isteğe bağlı LLM destekli inceleme.",
    "landing.howItWorks": "Nasıl çalışır",
    "landing.howItWorks.step1Title": "Depo URL'i girin",
    "landing.howItWorks.step1Desc": "Herhangi bir public GitHub depo URL'i yapıştırın ve Analiz Et'e basın.",
    "landing.howItWorks.step2Title": "Pipeline 9 faz çalıştırır",
    "landing.howItWorks.step2Desc": "Tespit, metrik, kanıt, graf, kök neden, planlama ve inceleme.",
    "landing.howItWorks.step3Title": "Dashboard'u keşfedin",
    "landing.howItWorks.step3Desc": "Kök nedenler, yol haritası, kanıt, graf, dosyalar ve AI incelemesini derinlemesine inceleyin.",
    "landing.exampleRepos": "Örnek deneyin:",

    // Geçmiş çekmecesi
    "history.title": "Analiz Geçmişi",
    "history.empty": "Henüz analiz yok. İlk analizinizi çalıştırın.",
    "history.reopen": "Yeniden aç",
    "history.remove": "Kaldır",
    "history.clearAll": "Tümünü temizle",
    "history.count": "{count} analiz",
    "history.demoBadge": "demo",
    "history.justNow": "az önce",
    "history.minutesAgo": "{m} dk önce",
    "history.hoursAgo": "{h} sa önce",
    "history.exportJson": "Tümünü dışa aktar (JSON)",
    "history.exportedJson": "Geçmiş JSON olarak dışa aktarıldı",
    "history.fullBackup": "Tam yedek (sonuçlarla)",
    "history.exportedFull": "Tam yedek JSON olarak dışa aktarıldı",
    "history.reanalyze": "Yeniden analiz et",
    "history.reanalyzing": "Yeniden analiz ediliyor…",
    "health.grade": "Not",

    // Ayarlar ekstraları
    "settings.back": "Geri",
    "settings.llm.providerCards": "Bir sağlayıcı seçin",
    "settings.llm.providerHelp": "AI destekli mühendislik incelemesini etkinleştirmek için bir sağlayıcı seçin. Anahtarınız bu tarayıcıda yerel olarak saklanır.",
    "settings.llm.status": "Durum",

    // Karşılaştırma görünümü
    "compare.title": "Analizleri Karşılaştır",
    "compare.current": "Mevcut",
    "compare.baseline": "Taban",
    "compare.selectBaseline": "Karşılaştırılacak tabanı seçin",
    "compare.healthScores": "Sağlık Skorları",
    "compare.rootCauses": "Kök Nedenler",
    "compare.delta": "Δ",
    "compare.improved": "iyileşti",
    "compare.regressed": "geriledi",
    "compare.unchanged": "değişmedi",
    "compare.new": "yeni",
    "compare.gone": "kaybolan",
    "compare.noBaseline": "Başka bir analiz çalıştırın veya geçmişten bir giriş yeniden açın, ardından burada taban olarak seçin.",
    "compare.better": "daha iyi",
    "compare.worse": "daha kötü",
    "compare.same": "aynı",
    "compare.close": "Karşılaştırmayı kapat",
    "compare.evidence": "Kanıtlar",
    "compare.roadmap": "Yol Haritası Adımları",
    "compare.quickWins": "Hızlı Kazanımlar",

    // AI İncelemesi — ayrıştırılmış ROI alanları
    "ai.roi": "ROI",
    "ai.priority": "Öncelik",
    "ai.estimate": "Tahmini",
    "ai.step": "Adım",

    // Footer
    "footer.builtWith": "Next.js, TypeScript, Tailwind CSS ve shadcn/ui ile yapıldı",
    "footer.shortcutsHint": "Klavye kısayolları için",
    "footer.toSeeShortcuts": "tuşuna basın",
    "footer.copyright": "AI Yazılım Mimarı",
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
