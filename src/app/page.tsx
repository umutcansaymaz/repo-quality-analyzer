"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Github,
  Search,
  FileCode2,
  GitBranch,
  Bug,
  Network,
  Brain,
  Map as MapIcon,
  Sparkles,
  Loader2,
  CheckCircle2,
  Circle,
  AlertCircle,
  ArrowLeft,
  Download,
  Sun,
  Moon,
  ChevronRight,
  Activity,
  Shield,
  TrendingUp,
  Zap,
  Target,
  Lightbulb,
  FileText,
  Eye,
  Beaker,
  Layers,
  Settings as SettingsIcon,
  Globe,
  Key,
  Info,
  Copy,
  Trash2,
  EyeOff,
  CheckCircle,
  XCircle,
  FolderOpen,
  Database,
  Gauge,
  Plus,
  Minus,
  Maximize,
  RotateCcw,
  History,
  Clock,
  Rocket,
  Workflow,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "@/components/ui/sheet";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { LanguageProvider, useI18n, type Language } from "@/components/analyzer/i18n";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer, Legend } from "recharts";
import { generateDemoData } from "@/lib/demo-data";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ViewState = "landing" | "progress" | "results" | "settings";

interface PipelineStep {
  id: string;
  labelKey: string;
  icon: React.ReactNode;
  status: "pending" | "running" | "completed" | "error";
}

interface AnalysisData {
  jobId: string;
  status: string;
  repository: string;
  result: any;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function apiFetch(path: string, options?: RequestInit) {
  const res = await fetch(path, options);
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res;
}

// ---------------------------------------------------------------------------
// LLM Configuration (shared across Settings + Status + Trust + Overview)
// ---------------------------------------------------------------------------

// Custom event dispatched whenever the saved LLM config changes,
// so every component on the page re-reads localStorage immediately
// (the native "storage" event only fires across OTHER tabs, not same-tab).
export const LLM_CONFIG_CHANGED_EVENT = "ra-llm-config-changed";
const LLM_CONFIG_STORAGE_KEY = "ra-llm-config";

export interface LLMConfig {
  provider: string;
  apiKey: string;
  model: string;
  temperature: string;
  maxTokens: string;
  baseUrl: string;
  endpoint: string;
  deployment: string;
  apiVersion: string;
  host: string;
  port: string;
  savedAt?: string;
}

const EMPTY_CONFIG: LLMConfig = {
  provider: "",
  apiKey: "",
  model: "",
  temperature: "0.3",
  maxTokens: "4096",
  baseUrl: "",
  endpoint: "",
  deployment: "",
  apiVersion: "2024-02-15-preview",
  host: "http://localhost",
  port: "11434",
};

export const LLM_PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic Claude",
  gemini: "Google Gemini",
  openrouter: "OpenRouter",
  azure_openai: "Azure OpenAI",
  ollama: "Ollama (Local)",
};

function readLLMConfig(): LLMConfig {
  if (typeof window === "undefined") return EMPTY_CONFIG;
  try {
    const raw = window.localStorage.getItem(LLM_CONFIG_STORAGE_KEY);
    if (!raw) return EMPTY_CONFIG;
    const parsed = JSON.parse(raw);
    return { ...EMPTY_CONFIG, ...parsed };
  } catch {
    return EMPTY_CONFIG;
  }
}

function writeLLMConfig(config: Partial<LLMConfig>) {
  if (typeof window === "undefined") return;
  const next = { ...readLLMConfig(), ...config, savedAt: new Date().toISOString() };
  window.localStorage.setItem(LLM_CONFIG_STORAGE_KEY, JSON.stringify(next));
  // Notify same-tab listeners (Settings -> Dashboard live update)
  window.dispatchEvent(new Event(LLM_CONFIG_CHANGED_EVENT));
}

function clearLLMConfig() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(LLM_CONFIG_STORAGE_KEY);
  window.dispatchEvent(new Event(LLM_CONFIG_CHANGED_EVENT));
}

/**
 * Subscribe to the saved LLM configuration.
 * Re-renders whenever Settings saves or deletes the config (same tab + cross tab).
 */
export function useLLMConfig() {
  const [config, setConfig] = React.useState<LLMConfig>(EMPTY_CONFIG);

  React.useEffect(() => {
    setConfig(readLLMConfig());
    const handler = () => setConfig(readLLMConfig());
    window.addEventListener(LLM_CONFIG_CHANGED_EVENT, handler);
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener(LLM_CONFIG_CHANGED_EVENT, handler);
      window.removeEventListener("storage", handler);
    };
  }, []);

  const hasProvider = !!config.provider;
  const hasApiKey = !!config.apiKey && config.apiKey.trim().length > 0;
  const isOllama = config.provider === "ollama";
  // Ollama runs locally and does not require an API key.
  const isConfigured = hasProvider && (hasApiKey || isOllama);
  const providerLabel = config.provider
    ? LLM_PROVIDER_LABELS[config.provider] || config.provider
    : "";

  return { config, isConfigured, hasApiKey, hasProvider, isOllama, providerLabel };
}

// Effective LLM status, combining backend review + saved config.
// - "active": backend analysis actually used an LLM (review.offline === false)
// - "ready": user saved a valid API key, but no LLM analysis has run yet
// - "offline": no API key configured (demo data / deterministic fallback)
export type LLMStatus = "active" | "ready" | "offline";

export function useLLMStatus(review: any): LLMStatus {
  const { isConfigured } = useLLMConfig();
  if (review && review.offline === false) return "active";
  if (isConfigured) return "ready";
  return "offline";
}

// Shared badge renderer so every surface shows the same colors / icons.
export function LLMStatusBadge({
  status,
  t,
  size = "sm",
}: {
  status: LLMStatus;
  t: (k: string) => string;
  size?: "sm" | "xs";
}) {
  const cls = size === "xs" ? "text-xs gap-1" : "gap-1";
  if (status === "active") {
    return (
      <Badge variant="default" className={`${cls} bg-green-600 hover:bg-green-600`}>
        <CheckCircle className="h-3 w-3" />
        {t("trust.active")}
      </Badge>
    );
  }
  if (status === "ready") {
    return (
      <Badge variant="default" className={`${cls} bg-amber-500 hover:bg-amber-500`}>
        <Circle className="h-3 w-3 fill-amber-50 text-amber-50" />
        {t("trust.ready")}
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className={cls}>
      <Circle className="h-3 w-3" />
      {t("trust.offline")}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Analysis History (localStorage-persisted list of past analyses)
// ---------------------------------------------------------------------------

export const HISTORY_CHANGED_EVENT = "ra-history-changed";
const HISTORY_STORAGE_KEY = "ra-analysis-history";
const HISTORY_MAX = 20;

export interface HistoryEntry {
  id: string;            // job id (or generated)
  repoUrl: string;
  owner: string;
  name: string;
  analyzedAt: string;    // ISO timestamp
  grade: string;         // health grade (e.g. "B-")
  overall: number;       // health score 0-100
  rootCauseCount: number;
  evidenceCount: number;
  isDemo: boolean;
  result: any;           // full analysis result payload
}

function readHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeHistory(entries: HistoryEntry[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(entries.slice(0, HISTORY_MAX)));
  window.dispatchEvent(new Event(HISTORY_CHANGED_EVENT));
}

export function addHistoryEntry(entry: HistoryEntry) {
  const all = readHistory();
  // Dedupe by repoUrl — keep the latest analysis per repo
  const filtered = all.filter((e) => e.repoUrl !== entry.repoUrl);
  filtered.unshift(entry);
  writeHistory(filtered);
}

export function removeHistoryEntry(id: string) {
  writeHistory(readHistory().filter((e) => e.id !== id));
}

export function clearHistory() {
  writeHistory([]);
}

export function useHistoryEntries(): HistoryEntry[] {
  const [entries, setEntries] = React.useState<HistoryEntry[]>([]);
  React.useEffect(() => {
    const load = () => setEntries(readHistory());
    load();
    window.addEventListener(HISTORY_CHANGED_EVENT, load);
    window.addEventListener("storage", load);
    return () => {
      window.removeEventListener(HISTORY_CHANGED_EVENT, load);
      window.removeEventListener("storage", load);
    };
  }, []);
  return entries;
}

// ---------------------------------------------------------------------------
// Main App (with providers)
// ---------------------------------------------------------------------------

export default function Home() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
}

function AppContent() {
  const [view, setView] = React.useState<ViewState>("landing");
  const [repoUrl, setRepoUrl] = React.useState("");
  const [analysisData, setAnalysisData] = React.useState<AnalysisData | null>(null);
  const [pipelineSteps, setPipelineSteps] = React.useState<PipelineStep[]>([]);
  const { theme, setTheme } = useTheme();
  const { lang, setLang, t } = useI18n();
  const [mounted, setMounted] = React.useState(false);
  const [globalSearch, setGlobalSearch] = React.useState("");
  const [searchResults, setSearchResults] = React.useState<any[] | null>(null);
  const [showShortcuts, setShowShortcuts] = React.useState(false);
  const [showHistory, setShowHistory] = React.useState(false);
  const [showCompare, setShowCompare] = React.useState(false);
  const [showOnboarding, setShowOnboarding] = React.useState(false);
  const searchInputRef = React.useRef<HTMLInputElement>(null);
  const historyEntries = useHistoryEntries();

  React.useEffect(() => setMounted(true), []);

  // Show onboarding wizard on first launch (when localStorage flag is not set).
  React.useEffect(() => {
    if (!mounted) return;
    try {
      const done = localStorage.getItem("ra-onboarding-complete");
      if (!done) setShowOnboarding(true);
    } catch { /* ignore */ }
  }, [mounted]);

  // Keyboard shortcuts:
  //  ?       → open shortcuts help
  //  /       → focus global search
  //  1-7     → switch dashboard tabs (only when on results view)
  //  Esc     → close dialog / clear search
  //  t       → toggle theme
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

      // Esc always works
      if (e.key === "Escape") {
        if (showShortcuts) { setShowShortcuts(false); return; }
        if (globalSearch) { setGlobalSearch(""); setSearchResults(null); return; }
        return;
      }

      // ? opens help (even when typing? no — only when not typing to avoid hijack)
      if (e.key === "?" && !typing) {
        e.preventDefault();
        setShowShortcuts(true);
        return;
      }

      // / focuses search
      if (e.key === "/" && !typing) {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      // t toggles theme
      if (e.key.toLowerCase() === "t" && !typing) {
        setTheme(theme === "dark" ? "light" : "dark");
        return;
      }

      // 1-7 switch tabs (only on results view, not typing)
      if (view === "results" && !typing && /^[1-7]$/.test(e.key)) {
        const tabs = ["overview", "rootcauses", "roadmap", "evidence", "graph", "files", "ai"];
        const idx = parseInt(e.key, 10) - 1;
        if (tabs[idx]) {
          // Radix TabsTrigger activates on pointerdown, not click — use a custom
          // event that ResultsDashboard listens for and feeds to setActiveTab.
          window.dispatchEvent(new CustomEvent("ra-switch-tab", { detail: tabs[idx] }));
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [view, theme, globalSearch, showShortcuts, setTheme]);

  const handleAnalyze = async () => {
    if (!repoUrl.trim()) {
      toast.error(t("landing.enterUrl"));
      return;
    }
    setView("progress");
    setPipelineSteps(getInitialSteps(t));

    const stepIds = ["detection", "language", "dependency", "metrics", "evidence", "graph", "rootcause", "planning", "review"];

    try {
      setStepStatus("detection", "running");

      // Read LLM config from localStorage so the mock API knows whether to
      // generate an LLM-powered review (offline: false) or a fallback.
      let llmConfig: any = null;
      try {
        const raw = localStorage.getItem("ra-llm-config");
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed.provider && (parsed.provider === "ollama" || parsed.apiKey)) {
            llmConfig = parsed;
          }
        }
      } catch { /* ignore */ }

      const apiPromise = apiFetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: repoUrl, use_cache: true, llm_config: llmConfig }),
      }).catch(() => null);

      for (const stepId of stepIds) {
        setStepStatus(stepId, "running");
        await sleep(500 + Math.random() * 600);
        setStepStatus(stepId, "completed");
      }

      let resultData: any = null;
      let isDemo = false;
      const apiRes = await apiPromise;
      if (apiRes) {
        try {
          const data = await apiRes.json();
          // Pass repo + LLM info as query params so the mock /api/result route
          // can regenerate the demo result if the job isn't in its in-memory
          // store (e.g. after server restart) — with the correct LLM state.
          const params = new URLSearchParams({ repo: repoUrl });
          if (llmConfig) {
            params.set("use_llm", "true");
            if (llmConfig.provider) params.set("provider", llmConfig.provider);
            if (llmConfig.model) params.set("model", llmConfig.model);
          }
          const resultRes = await apiFetch(`/api/result/${data.job_id}?${params}`);
          resultData = await resultRes.json();
        } catch {
          resultData = getDemoData(repoUrl);
          isDemo = true;
        }
      } else {
        resultData = getDemoData(repoUrl);
        isDemo = true;
      }

      setAnalysisData({ jobId: "demo", status: "completed", repository: repoUrl, result: resultData });
      // Persist to history so the user can reopen past analyses from the header drawer.
      try {
        const owner = repoUrl.split("/").slice(-2)[0] || "unknown";
        const name = repoUrl.split("/").slice(-1)[0]?.replace(".git", "") || "repo";
        const hs = resultData?.ai_review?.health_score;
        // Always generate a unique id per entry — demo data shares "demo-001" across runs,
        // which would cause React key collisions in the history drawer.
        addHistoryEntry({
          id: `hist-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          repoUrl,
          owner,
          name,
          analyzedAt: new Date().toISOString(),
          grade: hs?.grade || "N/A",
          overall: hs?.overall || 0,
          rootCauseCount: resultData?.root_causes?.root_causes?.length || 0,
          evidenceCount: resultData?.evidence?.statistics?.total_evidence || resultData?.evidence?.evidence?.length || 0,
          isDemo,
          result: resultData,
        });
      } catch { /* localStorage might be full — non-fatal */ }
      setView("results");
      toast.success(t("analysis.complete"));
    } catch {
      const demoData = getDemoData(repoUrl);
      setAnalysisData({ jobId: "demo", status: "completed", repository: repoUrl, result: demoData });
      // Persist demo run to history too.
      try {
        const owner = repoUrl.split("/").slice(-2)[0] || "unknown";
        const name = repoUrl.split("/").slice(-1)[0]?.replace(".git", "") || "repo";
        const hs = demoData?.ai_review?.health_score;
        addHistoryEntry({
          id: `hist-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          repoUrl,
          owner,
          name,
          analyzedAt: new Date().toISOString(),
          grade: hs?.grade || "N/A",
          overall: hs?.overall || 0,
          rootCauseCount: demoData?.root_causes?.root_causes?.length || 0,
          evidenceCount: demoData?.evidence?.statistics?.total_evidence || demoData?.evidence?.evidence?.length || 0,
          isDemo: true,
          result: demoData,
        });
      } catch { /* non-fatal */ }
      setView("results");
      toast.info(t("analysis.demoMode"));
    }
  };

  const handleReset = () => {
    setView("landing");
    setRepoUrl("");
    setAnalysisData(null);
    setPipelineSteps([]);
    setGlobalSearch("");
    setSearchResults(null);
  };

  // Reopen a past analysis from the history drawer — restores the full result
  // payload without re-running the pipeline.
  const handleReopenHistory = (entry: HistoryEntry) => {
    setRepoUrl(entry.repoUrl);
    setAnalysisData({ jobId: entry.id, status: "completed", repository: entry.repoUrl, result: entry.result });
    setView("results");
    setShowHistory(false);
    toast.success(t("analysis.complete"));
  };

  // Re-run the pipeline for a history entry's repo — closes the drawer, fills
  // the URL in state, and triggers handleAnalyze directly (handleAnalyze reads
  // repoUrl from state, not the DOM, so we don't need to wait for the landing
  // view to mount).
  const handleReanalyze = (entry: HistoryEntry) => {
    setShowHistory(false);
    setRepoUrl(entry.repoUrl);
    // Clear any previous results so the progress view shows cleanly.
    setAnalysisData(null);
    setPipelineSteps(getInitialSteps(t));
    setView("progress");
    // Defer handleAnalyze so React processes the view/state change first.
    setTimeout(() => handleAnalyze(), 0);
  };

  const setStepStatus = (id: string, status: PipelineStep["status"]) => {
    setPipelineSteps((prev) => prev.map((s) => (s.id === id ? { ...s, status } : s)));
  };

  // Global search handler
  React.useEffect(() => {
    if (!globalSearch.trim() || !analysisData) {
      setSearchResults(null);
      return;
    }
    const q = globalSearch.toLowerCase();
    const results: any[] = [];
    const data = analysisData.result;

    // Search evidence
    (data?.evidence?.evidence || []).forEach((ev: any) => {
      if (ev.message?.toLowerCase().includes(q) || ev.file_path?.toLowerCase().includes(q) || ev.analyzer?.toLowerCase().includes(q) || ev.category?.toLowerCase().includes(q)) {
        results.push({ type: "evidence", label: ev.message, detail: ev.file_path, data: ev });
      }
    });

    // Search root causes
    (data?.root_causes?.root_causes || []).forEach((rc: any) => {
      if (rc.title?.toLowerCase().includes(q) || rc.category?.toLowerCase().includes(q) || rc.description?.toLowerCase().includes(q)) {
        results.push({ type: "rootCause", label: rc.title, detail: rc.category, data: rc });
      }
    });

    // Search plan steps
    (data?.engineering_plan?.steps || []).forEach((step: any) => {
      if (step.title?.toLowerCase().includes(q) || step.technical_description?.toLowerCase().includes(q)) {
        results.push({ type: "recommendation", label: step.title, detail: step.root_cause_category, data: step });
      }
    });

    // Search files
    (data?.file_inventory?.files || []).forEach((f: string) => {
      if (f.toLowerCase().includes(q)) {
        results.push({ type: "file", label: f, detail: "file", data: { path: f } });
      }
    });

    setSearchResults(results);
  }, [globalSearch, analysisData]);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-sm">
        <div className="container mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <button onClick={handleReset} className="flex items-center gap-2 font-bold tracking-tight">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Brain className="h-4 w-4" />
            </div>
            <span className="hidden sm:inline">{t("app.title")}</span>
          </button>
          <div className="flex items-center gap-2">
            {analysisData && view === "results" && (
              <div className="relative hidden sm:block">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  ref={searchInputRef}
                  value={globalSearch}
                  onChange={(e) => setGlobalSearch(e.target.value)}
                  placeholder={t("common.search")}
                  className="h-9 w-48 pl-9 lg:w-64"
                />
              </div>
            )}
            {analysisData && view === "results" && <ReportExport data={analysisData.result} />}
            {analysisData && view === "results" && historyEntries.length > 0 && (
              <Button variant="ghost" size="sm" className="h-9 gap-1.5 px-2" onClick={() => setShowCompare(true)} title={t("compare.title")}>
                <GitBranch className="h-4 w-4" />
                <span className="hidden sm:inline">{t("compare.title")}</span>
              </Button>
            )}
            {mounted && (
              <>
                <Select value={lang} onValueChange={(v) => setLang(v as Language)}>
                  <SelectTrigger className="h-9 w-[80px]">
                    <Globe className="mr-1 h-4 w-4" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">EN</SelectItem>
                    <SelectItem value="tr">TR</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="ghost" size="icon" onClick={() => setShowHistory(true)} title={t("history.title")} className="relative">
                  <History className="h-4 w-4" />
                  {historyEntries.length > 0 && (
                    <span className="absolute -right-0.5 -top-0.5 flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-primary-foreground">
                      {historyEntries.length > 9 ? "9+" : historyEntries.length}
                    </span>
                  )}
                </Button>
                <Button variant="ghost" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
                  {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </Button>
                <Button variant="ghost" size="icon" onClick={() => setShowShortcuts(true)} title={t("shortcuts.title")}>
                  <Info className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" onClick={() => setView("settings")}>
                  <SettingsIcon className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        </div>
        {/* Global search results dropdown */}
        {searchResults && searchResults.length > 0 && view === "results" && (
          <div className="absolute left-0 right-0 top-14 border-b bg-background shadow-lg">
            <ScrollArea className="max-h-80">
              <div className="container mx-auto max-w-7xl p-4">
                {searchResults.slice(0, 20).map((r, i) => (
                  <div key={i} className="flex items-center gap-3 rounded p-2 hover:bg-muted/50 cursor-pointer">
                    {r.type === "evidence" && <Beaker className="h-4 w-4 text-blue-500" />}
                    {r.type === "rootCause" && <Bug className="h-4 w-4 text-red-500" />}
                    {r.type === "recommendation" && <MapIcon className="h-4 w-4 text-purple-500" />}
                    {r.type === "file" && <FileCode2 className="h-4 w-4 text-green-500" />}
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-sm font-medium">{r.label}</p>
                      <p className="truncate text-xs text-muted-foreground">{r.detail}</p>
                    </div>
                    <Badge variant="outline" className="text-xs">{r.type}</Badge>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}
      </header>

      <main className="flex-1">
        <AnimatePresence mode="wait">
          {view === "landing" && (
            <motion.div key="landing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, y: -20 }}>
              <LandingView repoUrl={repoUrl} setRepoUrl={setRepoUrl} onAnalyze={handleAnalyze} />
            </motion.div>
          )}
          {view === "progress" && (
            <motion.div key="progress" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <ProgressView steps={pipelineSteps} repoUrl={repoUrl} />
            </motion.div>
          )}
          {view === "results" && analysisData && (
            <motion.div key="results" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <ResultsDashboard data={analysisData.result} onReset={handleReset} />
            </motion.div>
          )}
          {view === "settings" && (
            <motion.div key="settings" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <SettingsView onBack={() => setView(analysisData ? "results" : "landing")} />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Sticky footer — sits at viewport bottom when content is short,
          pushed down naturally when content overflows. */}
      <footer className="mt-auto border-t bg-background/80 backdrop-blur-sm">
        <div className="container mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Brain className="h-3.5 w-3.5 text-primary" />
            <span className="font-medium">{t("footer.copyright")}</span>
            <span className="hidden text-muted-foreground/60 sm:inline">·</span>
            <span className="hidden sm:inline">{t("footer.builtWith")}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span>{t("footer.shortcutsHint")}</span>
            <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded border border-border bg-muted px-1 font-mono text-[10px] font-semibold">?</kbd>
            <span>{t("footer.toSeeShortcuts")}</span>
          </div>
        </div>
      </footer>

      {/* Keyboard shortcuts help dialog */}
      <ShortcutsHelpDialog open={showShortcuts} onOpenChange={setShowShortcuts} />

      {/* Onboarding wizard — shown on first launch */}
      <OnboardingWizard
        open={showOnboarding}
        onOpenChange={(v) => {
          setShowOnboarding(v);
          if (!v) {
            try { localStorage.setItem("ra-onboarding-complete", "true"); } catch { /* ignore */ }
          }
        }}
        onComplete={() => {
          try { localStorage.setItem("ra-onboarding-complete", "true"); } catch { /* ignore */ }
          setShowOnboarding(false);
        }}
      />

      {/* Analysis history drawer */}
      <HistorySheet
        open={showHistory}
        onOpenChange={setShowHistory}
        entries={historyEntries}
        onReopen={handleReopenHistory}
        onReanalyze={handleReanalyze}
      />

      {/* Comparison dialog — diff current vs a baseline from history */}
      <CompareDialog
        open={showCompare}
        onOpenChange={setShowCompare}
        current={analysisData?.result}
        historyEntries={historyEntries}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Landing View
// ---------------------------------------------------------------------------

function LandingView({ repoUrl, setRepoUrl, onAnalyze }: { repoUrl: string; setRepoUrl: (v: string) => void; onAnalyze: () => void }) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = React.useState("github");
  const [localPath, setLocalPath] = React.useState("");
  const [localError, setLocalError] = React.useState("");
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Handle local folder selection.
  // Uses <input type="file" webkitdirectory> which works across Windows/macOS/Linux.
  const handleFolderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setLocalError("");
    const files = e.target.files;
    if (!files || files.length === 0) return;

    // The first file's webkitRelativePath gives the top-level folder name.
    // We check if any file is inside a .git directory (indicating a git repo).
    const allPaths: string[] = [];
    let hasGitDir = false;
    for (let i = 0; i < files.length; i++) {
      const relPath = (files[i] as any).webkitRelativePath || "";
      allPaths.push(relPath);
      if (relPath.includes("/.git/") || relPath.includes("/.git")) {
        hasGitDir = true;
      }
    }

    // Extract the top-level folder name from the first file's relative path.
    const topFolder = allPaths[0]?.split("/")[0] || "";
    if (!topFolder) {
      setLocalError(t("local.readError"));
      return;
    }

    if (!hasGitDir) {
      setLocalError(t("local.notGitRepo"));
      return;
    }

    // Set a synthetic path that the analysis pipeline can use.
    // The mock API will use this as the repo identifier.
    const fullPath = `/local/${topFolder}`;
    setLocalPath(fullPath);
    setRepoUrl(fullPath);
  };

  const handleLocalAnalyze = () => {
    if (!localPath) {
      setLocalError(t("local.noFolderSelected"));
      return;
    }
    setLocalError("");
    onAnalyze();
  };

  const features: { icon: React.ReactNode; title: string; desc: string; accent: string }[] = [
    { icon: <Bug className="h-5 w-5" />,        title: t("landing.feature.rootCausesTitle"),    desc: t("landing.feature.rootCausesDesc"),    accent: "text-rose-500 bg-rose-500/10" },
    { icon: <Network className="h-5 w-5" />,    title: t("landing.feature.graphTitle"),         desc: t("landing.feature.graphDesc"),         accent: "text-sky-500 bg-sky-500/10" },
    { icon: <MapIcon className="h-5 w-5" />,        title: t("landing.feature.roadmapTitle"),       desc: t("landing.feature.roadmapDesc"),       accent: "text-violet-500 bg-violet-500/10" },
    { icon: <Eye className="h-5 w-5" />,        title: t("landing.feature.explainabilityTitle"),desc: t("landing.feature.explainabilityDesc"),accent: "text-amber-500 bg-amber-500/10" },
    { icon: <Shield className="h-5 w-5" />,     title: t("landing.feature.trustTitle"),          desc: t("landing.feature.trustDesc"),          accent: "text-emerald-500 bg-emerald-500/10" },
    { icon: <Sparkles className="h-5 w-5" />,   title: t("landing.feature.aiTitle"),             desc: t("landing.feature.aiDesc"),             accent: "text-pink-500 bg-pink-500/10" },
  ];

  const steps: { num: string; title: string; desc: string; icon: React.ReactNode }[] = [
    { num: "1", title: t("landing.howItWorks.step1Title"), desc: t("landing.howItWorks.step1Desc"), icon: <Github className="h-5 w-5" /> },
    { num: "2", title: t("landing.howItWorks.step2Title"), desc: t("landing.howItWorks.step2Desc"), icon: <Workflow className="h-5 w-5" /> },
    { num: "3", title: t("landing.howItWorks.step3Title"), desc: t("landing.howItWorks.step3Desc"), icon: <Rocket className="h-5 w-5" /> },
  ];

  const examples = [
    "https://github.com/facebook/react",
    "https://github.com/microsoft/vscode",
    "https://github.com/torvalds/linux",
  ];

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center px-4 py-12">
      <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="w-full max-w-2xl text-center">
        <div className="mb-6 flex justify-center">
          <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/60 shadow-lg shadow-primary/20">
            <Brain className="h-10 w-10 text-primary-foreground" />
          </div>
        </div>
        <h1 className="mb-3 text-4xl font-bold tracking-tight sm:text-5xl">{t("app.title")}</h1>
        <p className="mb-8 whitespace-pre-line text-base text-muted-foreground sm:text-lg">{t("app.subtitle")}</p>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="github" className="gap-1.5">
              <Github className="h-4 w-4" /> {t("tabs.github")}
            </TabsTrigger>
            <TabsTrigger value="local" className="gap-1.5">
              <FolderOpen className="h-4 w-4" /> {t("tabs.local")}
            </TabsTrigger>
          </TabsList>
          <TabsContent value="github" className="mt-4">
            <div className="flex flex-col gap-3 sm:flex-row">
              <Input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder={t("landing.placeholder")} className="h-12 flex-1 text-base" onKeyDown={(e) => e.key === "Enter" && onAnalyze()} />
              <Button size="lg" className="h-12 px-8 text-base" onClick={onAnalyze}>
                <Sparkles className="mr-2 h-5 w-5" />
                {t("app.analyze")}
              </Button>
            </div>
            {/* Example repo chips */}
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-xs text-muted-foreground">{t("landing.exampleRepos")}</span>
              {examples.map((ex) => {
                const short = ex.replace("https://github.com/", "");
                return (
                  <button
                    key={ex}
                    onClick={() => setRepoUrl(ex)}
                    className="rounded-full border bg-muted/40 px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  >
                    {short}
                  </button>
                );
              })}
              {/* Demo Analysis button — lets first-time users explore the
                  full dashboard without entering a URL. */}
              <button
                onClick={() => { setRepoUrl("https://github.com/demo/sample-project"); onAnalyze(); }}
                className="rounded-full border border-primary/40 bg-primary/10 px-3 py-1 text-xs font-medium text-primary transition-all hover:bg-primary/20 hover:shadow-sm"
              >
                <Sparkles className="mr-1 inline h-3 w-3" /> Demo Analizi
              </button>
            </div>
          </TabsContent>
          <TabsContent value="local" className="mt-4">
            {/* Hidden file input for folder selection — webkitdirectory works
                across Windows/macOS/Linux in all modern browsers. */}
            <input
              ref={fileInputRef}
              type="file"
              // @ts-expect-error — webkitdirectory is a non-standard attribute
              webkitdirectory=""
              directory=""
              multiple
              className="hidden"
              onChange={handleFolderSelect}
            />
            <div
              className="flex flex-col items-center gap-3 rounded-lg border-2 border-dashed border-muted-foreground/30 p-8 text-center transition-colors hover:border-primary/40 cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add("border-primary"); }}
              onDragLeave={(e) => { e.currentTarget.classList.remove("border-primary"); }}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove("border-primary");
                const items = e.dataTransfer.items;
                if (items && items.length > 0) {
                  // Trigger the file input as fallback (drag-drop directory
                  // access requires additional APIs; the click-to-browse path
                  // is the primary interaction).
                  fileInputRef.current?.click();
                }
              }}
            >
              <FolderOpen className="h-10 w-10 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">{localPath ? t("local.folderSelected") : t("local.dragDrop")}</p>
              {localPath && (
                <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-1.5 text-sm">
                  <FolderOpen className="h-4 w-4 text-primary" />
                  <span className="font-mono text-xs">{localPath}</span>
                </div>
              )}
              <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>
                <FolderOpen className="mr-1.5 h-4 w-4" /> {t("local.browse")}
              </Button>
            </div>
            {localError && (
              <div className="mt-3 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{localError}</span>
              </div>
            )}
            {localPath && !localError && (
              <div className="mt-3 flex justify-end">
                <Button size="lg" className="h-12 px-8 text-base" onClick={handleLocalAnalyze}>
                  <Sparkles className="mr-2 h-5 w-5" />
                  {t("app.analyze")}
                </Button>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </motion.div>

      {/* Feature cards grid */}
      <div className="mt-20 w-full max-w-5xl">
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">{t("landing.featuresTitle")}</h2>
          <p className="mt-2 text-sm text-muted-foreground sm:text-base">{t("landing.featuresSubtitle")}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.07 }}
              className="group rounded-xl border bg-card p-5 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5"
            >
              <div className={`mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg ${f.accent}`}>{f.icon}</div>
              <h3 className="text-base font-semibold">{f.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* How it works */}
      <div className="mt-20 w-full max-w-4xl">
        <h2 className="mb-8 text-center text-2xl font-bold tracking-tight sm:text-3xl">{t("landing.howItWorks")}</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {steps.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.1 }}
              className="relative rounded-xl border bg-card p-5"
            >
              <div className="mb-3 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">{s.num}</div>
                <div className="text-primary">{s.icon}</div>
              </div>
              <h3 className="text-sm font-semibold">{s.title}</h3>
              <p className="mt-1 text-xs text-muted-foreground">{s.desc}</p>
              {/* Connector arrow (desktop only, not on last card) */}
              {i < steps.length - 1 && (
                <div className="absolute -right-3 top-1/2 hidden -translate-y-1/2 text-muted-foreground/40 sm:block">
                  <ChevronRight className="h-5 w-5" />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Progress View
// ---------------------------------------------------------------------------

function getInitialSteps(t: (k: string) => string): PipelineStep[] {
  return [
    { id: "detection", labelKey: "pipeline.detection", icon: <Github className="h-5 w-5" />, status: "pending" },
    { id: "language", labelKey: "pipeline.language", icon: <FileText className="h-5 w-5" />, status: "pending" },
    { id: "dependency", labelKey: "pipeline.dependency", icon: <Layers className="h-5 w-5" />, status: "pending" },
    { id: "metrics", labelKey: "pipeline.metrics", icon: <Activity className="h-5 w-5" />, status: "pending" },
    { id: "evidence", labelKey: "pipeline.evidence", icon: <Beaker className="h-5 w-5" />, status: "pending" },
    { id: "graph", labelKey: "pipeline.graph", icon: <Network className="h-5 w-5" />, status: "pending" },
    { id: "rootcause", labelKey: "pipeline.rootcause", icon: <Bug className="h-5 w-5" />, status: "pending" },
    { id: "planning", labelKey: "pipeline.planning", icon: <MapIcon className="h-5 w-5" />, status: "pending" },
    { id: "review", labelKey: "pipeline.review", icon: <Sparkles className="h-5 w-5" />, status: "pending" },
  ];
}

function ProgressView({ steps, repoUrl }: { steps: PipelineStep[]; repoUrl: string }) {
  const { t } = useI18n();
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const progress = (completedCount / steps.length) * 100;

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-4">
      <div className="w-full max-w-lg">
        <div className="mb-8 text-center">
          <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-primary" />
          <h2 className="text-xl font-semibold">{t("pipeline.analyzing")}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{repoUrl}</p>
        </div>
        <Progress value={progress} className="mb-8 h-2" />
        <div className="space-y-2">
          {steps.map((step, i) => (
            <motion.div key={step.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} className="flex items-center gap-3 rounded-lg border p-3">
              <div className="flex-shrink-0">
                {step.status === "completed" && <CheckCircle2 className="h-5 w-5 text-green-500" />}
                {step.status === "running" && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                {step.status === "pending" && <Circle className="h-5 w-5 text-muted-foreground" />}
                {step.status === "error" && <AlertCircle className="h-5 w-5 text-destructive" />}
              </div>
              <div className="flex-shrink-0 text-muted-foreground">{step.icon}</div>
              <span className={`text-sm ${step.status === "pending" ? "text-muted-foreground" : "text-foreground"}`}>{t(step.labelKey)}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Results Dashboard
// ---------------------------------------------------------------------------

function ResultsDashboard({ data, onReset }: { data: any; onReset: () => void }) {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = React.useState("overview");

  // Listen for keyboard-driven tab switches (1-7) dispatched by AppContent.
  React.useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<string>).detail;
      if (typeof detail === "string") setActiveTab(detail);
    };
    window.addEventListener("ra-switch-tab", handler);
    return () => window.removeEventListener("ra-switch-tab", handler);
  }, []);

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={onReset}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t("app.newAnalysis")}
        </Button>
      </div>

      {/* Health Score + LLM Status + Trust Panel row */}
      <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
        <div className="space-y-4">
          <HealthScoreCard data={data} />
          <LLMStatusCard data={data} />
          {/* Pipeline phases card — fills the vertical gap when the right
              sidebar (Trust + Meta) is taller than the left column. */}
          <PipelinePhasesCard data={data} />
        </div>
        {/* Sticky sidebar: Trust Panel stays visible while scrolling long dashboards */}
        <div className="lg:sticky lg:top-20 lg:self-start lg:w-72 space-y-4">
          <PlatformStatusCard />
          <TrustPanel data={data} />
          <AnalysisMetaCard data={data} />
        </div>
      </div>

      {/* Main tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6">
        <TabsList className="flex w-full flex-wrap gap-1">
          <TabsTrigger value="overview" data-tab="overview" className="gap-1.5"><Activity className="h-4 w-4" /> {t("dashboard.overview")}</TabsTrigger>
          <TabsTrigger value="rootcauses" data-tab="rootcauses" className="gap-1.5"><Bug className="h-4 w-4" /> {t("dashboard.rootCauses")}</TabsTrigger>
          <TabsTrigger value="roadmap" data-tab="roadmap" className="gap-1.5"><MapIcon className="h-4 w-4" /> {t("dashboard.roadmap")}</TabsTrigger>
          <TabsTrigger value="evidence" data-tab="evidence" className="gap-1.5"><Beaker className="h-4 w-4" /> {t("dashboard.evidence")}</TabsTrigger>
          <TabsTrigger value="graph" data-tab="graph" className="gap-1.5"><Network className="h-4 w-4" /> {t("dashboard.graph")}</TabsTrigger>
          <TabsTrigger value="files" data-tab="files" className="gap-1.5"><FileCode2 className="h-4 w-4" /> {t("dashboard.files")}</TabsTrigger>
          <TabsTrigger value="ai" data-tab="ai" className="gap-1.5"><Sparkles className="h-4 w-4" /> {t("dashboard.aiReview")}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4"><OverviewSection data={data} /></TabsContent>
        <TabsContent value="rootcauses" className="mt-4"><RootCausesSection data={data} /></TabsContent>
        <TabsContent value="roadmap" className="mt-4"><RoadmapSection data={data} /></TabsContent>
        <TabsContent value="evidence" className="mt-4"><EvidenceSection data={data} /></TabsContent>
        <TabsContent value="graph" className="mt-4"><GraphSection data={data} /></TabsContent>
        <TabsContent value="files" className="mt-4"><FileExplorerSection data={data} /></TabsContent>
        <TabsContent value="ai" className="mt-4"><AIReviewSection data={data} /></TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Health Score Card
// ---------------------------------------------------------------------------

function HealthScoreCard({ data }: { data: any }) {
  const { t } = useI18n();
  const hs = data?.ai_review?.health_score;
  const grade = hs?.grade || "N/A";
  const overall = hs?.overall || 0;
  const gradeColor = overall >= 80 ? "text-emerald-500" : overall >= 60 ? "text-amber-500" : "text-rose-500";
  const ringStroke = overall >= 80 ? "#10b981" : overall >= 60 ? "#f59e0b" : "#f43f5e";
  const meta = data?.repository_metadata;

  // Circular ring geometry
  const R = 34;
  const C = 2 * Math.PI * R;
  const dash = (overall / 100) * C;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            {/* Circular gradient progress ring around the grade letter */}
            <div className="relative flex h-20 w-20 items-center justify-center">
              <svg className="absolute inset-0 -rotate-90" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r={R} fill="none" stroke="currentColor" strokeWidth="5" className="text-muted/40" />
                <circle
                  cx="40" cy="40" r={R} fill="none" stroke={ringStroke} strokeWidth="5"
                  strokeLinecap="round"
                  strokeDasharray={`${dash} ${C}`}
                  style={{ transition: "stroke-dasharray 0.8s ease" }}
                />
              </svg>
              <div className={`text-3xl font-bold ${gradeColor}`}>{grade}</div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{t("dashboard.health")}</p>
              <p className="text-2xl font-semibold">{overall.toFixed(1)} / 100</p>
            </div>
          </div>
          {meta && (
            <div className="flex flex-wrap gap-4 text-sm">
              {meta.license && <div className="flex items-center gap-1.5"><Shield className="h-4 w-4 text-muted-foreground" /><span>{meta.license}</span></div>}
              {meta.total_commits != null && <div className="flex items-center gap-1.5"><GitBranch className="h-4 w-4 text-muted-foreground" /><span>{meta.total_commits} {t("health.commits")}</span></div>}
              {meta.contributors && <div className="flex items-center gap-1.5"><Github className="h-4 w-4 text-muted-foreground" /><span>{meta.contributors.length} {t("health.contributors")}</span></div>}
            </div>
          )}
          {hs && (
            <div className="flex flex-wrap gap-3">
              {[
                { label: t("health.security"), value: hs.security },
                { label: t("health.architecture"), value: hs.architecture },
                { label: t("health.quality"), value: hs.code_quality },
                { label: t("health.testing"), value: hs.testing },
                { label: t("health.docs"), value: hs.documentation },
              ].map((s) => (
                <div key={s.label} className="text-center">
                  <div className={`text-lg font-semibold ${getScoreColor(s.value)}`}>{s.value?.toFixed(0)}</div>
                  <div className="text-xs text-muted-foreground">{s.label}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// LLM Status Card
// ---------------------------------------------------------------------------

function LLMStatusCard({ data }: { data: any }) {
  const { t } = useI18n();
  const review = data?.engineering_review;
  const { config, providerLabel, isConfigured } = useLLMConfig();
  const status = useLLMStatus(review);
  if (!review && !isConfigured) return null;

  // Prefer the backend-reported provider/model (when an LLM was actually used),
  // otherwise fall back to the user's saved config so the card reflects what
  // WILL be used on the next analysis.
  const provider = review?.model_info?.provider && review.model_info.provider !== "offline"
    ? review.model_info.provider
    : providerLabel || "—";
  const model = review?.model_info?.model && review.model_info.model !== "deterministic-fallback"
    ? review.model_info.model
    : config.model || "—";
  const tokens = (review?.prompt_tokens || 0) + (review?.completion_tokens || 0);

  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="font-medium">{t("llm.status")}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">{t("llm.provider")}:</span>
            <span className="font-medium">{provider}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">{t("llm.model")}:</span>
            <span className="font-medium">{model}</span>
          </div>
          <LLMStatusBadge status={status} t={t} />
          {tokens > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">{t("llm.estimatedTokens")}:</span>
              <span className="font-medium">{tokens}</span>
            </div>
          )}
          {status === "ready" && (
            <span className="text-xs text-amber-600 dark:text-amber-400 italic">
              {t("llm.readyHint")}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Trust Panel
// ---------------------------------------------------------------------------

function TrustPanel({ data }: { data: any }) {
  const { t } = useI18n();
  const evidence = data?.evidence;
  const evCount = evidence?.statistics?.total_evidence || evidence?.evidence?.length || 0;
  const analyzerCount = Object.keys(evidence?.statistics?.by_analyzer_counts || {}).length;
  const rootCauses = data?.root_causes?.root_causes || [];
  const avgConfidence = data?.root_causes?.statistics?.average_confidence || 0;
  const review = data?.engineering_review;
  const status = useLLMStatus(review);

  // Hallucination risk by status:
  // - active: LLM produced output, so a small hallucination risk exists
  // - ready:  key saved but not used yet, so no hallucination risk for current data
  // - offline: deterministic fallback, zero hallucination risk
  const hallucinationRisk = status === "active" ? 15 : status === "ready" ? 5 : 0;

  // Reasoning depth: count of pipeline phases that produced data
  let depth = 0;
  if (data?.evidence) depth++;
  if (data?.knowledge_graph) depth++;
  if (data?.root_causes) depth++;
  if (data?.engineering_plan) depth++;
  if (data?.engineering_review) depth++;

  // Trust score: weighted combination
  const trustScore = Math.round(
    (avgConfidence * 100 * 0.3) +
    (Math.min(evCount / 10, 1) * 100 * 0.2) +
    (Math.min(analyzerCount / 3, 1) * 100 * 0.15) +
    (depth / 5 * 100 * 0.2) +
    ((100 - hallucinationRisk) * 0.15)
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Shield className="h-4 w-4" /> {t("trust.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <TrustRow label={t("trust.trustScore")} value={
          <div className="flex items-center gap-2">
            <div className="text-lg font-bold tabular-nums">{trustScore}</div>
            <div className="h-2 w-24 rounded-full bg-muted overflow-hidden">
              <div className={`h-full ${trustScore >= 70 ? "bg-green-500" : trustScore >= 50 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${trustScore}%` }} />
            </div>
          </div>
        } />
        <TrustRow label={t("trust.confidence")} value={`${(avgConfidence * 100).toFixed(0)}%`} />
        <TrustRow label={t("trust.evidenceCount")} value={evCount} />
        <TrustRow label={t("trust.analyzerCount")} value={analyzerCount} />
        <TrustRow label={t("trust.reasoningDepth")} value={`${depth}/5`} />
        <TrustRow label={t("trust.hallucinationRisk")} value={
          <Badge variant={hallucinationRisk < 10 ? "default" : "secondary"} className="text-xs">
            {hallucinationRisk < 10 ? t("trust.low") : t("trust.medium")}
          </Badge>
        } />
        <TrustRow label={t("trust.llmStatus")} value={<LLMStatusBadge status={status} t={t} size="xs" />} />
      </CardContent>
    </Card>
  );
}

// Small card that fills the gap under the Trust Panel on tall dashboards,
// showing persistent analysis metadata (repo, job ID, timestamp, phase count).
function AnalysisMetaCard({ data }: { data: any }) {
  const { t } = useI18n();
  const repo = data?.repository;
  const repoLabel = repo ? `${repo.owner || ""}/${repo.name || ""}` : "—";
  const jobId = data?.id || "—";
  const analyzedAt = data?.analyzed_at || data?.created_at || new Date().toISOString();
  // Count the 9 pipeline phases that produced data — must match PipelinePhasesCard
  // so the two surfaces stay consistent.
  const phaseCount = [
    !!data?.repository,
    !!data?.file_inventory,
    !!data?.knowledge_graph?.nodes?.some((n: any) => n.node_type === "dependency"),
    !!data?.evidence?.evidence?.some((e: any) => e.finding_type === "metric"),
    !!data?.evidence?.evidence?.length,
    !!data?.knowledge_graph?.nodes?.length,
    !!data?.root_causes?.root_causes?.length,
    !!data?.engineering_plan?.steps?.length,
    !!data?.engineering_review,
  ].filter(Boolean).length;
  const fileCount = data?.file_inventory?.total_files ?? data?.file_inventory?.files?.length ?? 0;

  const fmtDate = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch { return iso; }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Database className="h-4 w-4" /> {t("meta.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <TrustRow label={t("meta.repository")} value={<span className="font-mono text-xs truncate max-w-[140px] block">{repoLabel}</span>} />
        <TrustRow label={t("meta.jobId")} value={<span className="font-mono text-xs">{jobId}</span>} />
        <TrustRow label={t("meta.analyzedAt")} value={<span className="text-xs">{fmtDate(analyzedAt)}</span>} />
        <TrustRow label={t("meta.phases")} value={`${phaseCount}/9`} />
        {fileCount > 0 && <TrustRow label={t("meta.files")} value={fileCount} />}
      </CardContent>
    </Card>
  );
}

// Compact card showing the 9 pipeline phases and which ones produced data.
// Fills the vertical gap in the left column when the right sidebar is taller.
function PipelinePhasesCard({ data }: { data: any }) {
  const { t } = useI18n();
  const phases = [
    { id: "detection",  label: t("pipeline.detection"),  present: !!data?.repository },
    { id: "language",   label: t("pipeline.language"),    present: !!data?.file_inventory },
    { id: "dependency", label: t("pipeline.dependency"),  present: !!data?.knowledge_graph?.nodes?.some((n: any) => n.node_type === "dependency") },
    { id: "metrics",    label: t("pipeline.metrics"),     present: !!data?.evidence?.evidence?.some((e: any) => e.finding_type === "metric") },
    { id: "evidence",   label: t("pipeline.evidence"),    present: !!data?.evidence?.evidence?.length },
    { id: "graph",      label: t("pipeline.graph"),       present: !!data?.knowledge_graph?.nodes?.length },
    { id: "rootcause",  label: t("pipeline.rootcause"),   present: !!data?.root_causes?.root_causes?.length },
    { id: "planning",   label: t("pipeline.planning"),    present: !!data?.engineering_plan?.steps?.length },
    { id: "review",     label: t("pipeline.review"),      present: !!data?.engineering_review },
  ];
  const completed = phases.filter((p) => p.present).length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-2"><Workflow className="h-4 w-4" /> {t("meta.phases")}</span>
          <span className="text-xs font-normal text-muted-foreground tabular-nums">{completed}/{phases.length}</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-2">
          {phases.map((p) => (
            <div
              key={p.id}
              className={`flex items-center gap-1.5 rounded-md border px-2 py-1.5 text-xs ${p.present ? "border-primary/30 bg-primary/5 text-foreground" : "border-border text-muted-foreground/50"}`}
              title={p.label}
            >
              {p.present
                ? <CheckCircle className="h-3 w-3 shrink-0 text-emerald-500" />
                : <Circle className="h-3 w-3 shrink-0" />}
              <span className="truncate">{p.label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// Platform Status card — shows health of backend components.
// Polls /api/health every 30 seconds and displays each component's status.
function PlatformStatusCard() {
  const { t } = useI18n();
  const [health, setHealth] = React.useState<Record<string, { status: string; detail: string }> | null>(null);
  const [lastChecked, setLastChecked] = React.useState<Date | null>(null);
  const [refreshing, setRefreshing] = React.useState(false);

  const fetchHealth = React.useCallback(async () => {
    setRefreshing(true);
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        setHealth(data.components);
        setLastChecked(new Date());
      }
    } catch {
      // If health check fails, show all as offline.
      setHealth(null);
    } finally {
      setRefreshing(false);
    }
  }, []);

  React.useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const components = [
    { key: "backend", label: t("platform.backend") },
    { key: "python", label: t("platform.python") },
    { key: "analyzer", label: t("platform.analyzer") },
    { key: "llm", label: t("platform.llm") },
    { key: "worker", label: t("platform.worker") },
    { key: "database", label: t("platform.database") },
    { key: "api", label: t("platform.api") },
  ];

  const statusConfig: Record<string, { color: string; label: string; dot: string }> = {
    online: { color: "text-emerald-500", label: t("platform.online"), dot: "bg-emerald-500" },
    offline: { color: "text-rose-500", label: t("platform.offline"), dot: "bg-rose-500" },
    warning: { color: "text-amber-500", label: t("platform.warning"), dot: "bg-amber-500" },
  };

  const fmtTime = (d: Date) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Activity className="h-4 w-4" /> {t("platform.title")}
          </CardTitle>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={fetchHealth} disabled={refreshing} title={t("platform.refresh")}>
            <RotateCcw className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {components.map((comp) => {
          const data = health?.[comp.key];
          const status = data?.status || "offline";
          const cfg = statusConfig[status] || statusConfig.offline;
          return (
            <div key={comp.key} className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{comp.label}</span>
              <span className="flex items-center gap-1.5">
                <span className={`h-2 w-2 rounded-full ${cfg.dot}`} />
                <span className={`font-medium ${cfg.color}`}>{cfg.label}</span>
              </span>
            </div>
          );
        })}
        {lastChecked && (
          <div className="pt-2 border-t text-xs text-muted-foreground/60">
            {t("platform.lastChecked")}: {fmtTime(lastChecked)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TrustRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overview Section
// ---------------------------------------------------------------------------

function OverviewSection({ data }: { data: any }) {
  const { t } = useI18n();
  const rootCauses = data?.root_causes?.root_causes || [];
  const plan = data?.engineering_plan;
  const evidence = data?.evidence;
  const evCount = evidence?.statistics?.total_evidence || evidence?.evidence?.length || 0;
  const review = data?.engineering_review;
  const status = useLLMStatus(review);
  const statusLabel = status === "active" ? t("trust.active") : status === "ready" ? t("trust.ready") : t("trust.offline");

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <StatCard icon={<Bug className="h-5 w-5" />} title={t("stats.rootCauses")} value={rootCauses.length} subtitle={t("stats.architecturalIssues")} accent="rose" />
      <StatCard icon={<Beaker className="h-5 w-5" />} title={t("stats.evidenceItems")} value={evCount} subtitle={t("stats.totalFindings")} accent="sky" />
      <StatCard icon={<Zap className="h-5 w-5" />} title={t("stats.quickWins")} value={plan?.quick_wins?.length || 0} subtitle={t("stats.lowEffortFixes")} accent="amber" />
      <StatCard icon={<MapIcon className="h-5 w-5" />} title={t("stats.planSteps")} value={plan?.steps?.length || 0} subtitle={t("stats.refactoringSteps")} accent="violet" />
      <StatCard icon={<TrendingUp className="h-5 w-5" />} title={t("stats.avgRoi")} value={plan?.statistics?.average_roi?.toFixed(2) || "0"} subtitle={t("stats.returnOnInvestment")} accent="emerald" />
      <StatCard
        icon={<Sparkles className="h-5 w-5" />}
        title={t("stats.aiReview")}
        value={statusLabel}
        subtitle={review?.statistics?.total_sections ? `${review.statistics.total_sections} ${t("dashboard.overview").toLowerCase()}` : t("stats.noReview")}
        accent="pink"
      />

      {rootCauses.length > 0 && (
        <>
          {/* Distribution charts: severity donut + confidence bar */}
          <DistributionCharts rootCauses={rootCauses} />

          <Card className="md:col-span-2 lg:col-span-3">
            <CardHeader>
              <CardTitle className="text-lg">{t("dashboard.rootCauses")}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {rootCauses.slice(0, 5).map((rc: any, i: number) => (
                  <RootCauseRow key={rc.id || i} rc={rc} />
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

// Severity donut + per-root-cause confidence bar, rendered with recharts.
function DistributionCharts({ rootCauses }: { rootCauses: any[] }) {
  const { t } = useI18n();

  // Aggregate severity counts from root causes
  const sevCounts = React.useMemo(() => {
    const order = ["critical", "high", "medium", "low", "info"];
    const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    rootCauses.forEach((rc) => { const s = (rc.severity || "info").toLowerCase(); if (counts[s] !== undefined) counts[s]++; });
    return order.filter((s) => counts[s] > 0).map((s) => ({ name: s, value: counts[s] }));
  }, [rootCauses]);

  const SEV_COLORS: Record<string, string> = {
    critical: "#e11d48", high: "#f97316", medium: "#f59e0b", low: "#0ea5e9", info: "#94a3b8",
  };

  // Confidence bar data — shorten labels aggressively so they fit the Y-axis.
  // Strip common prefixes ("God Class: ", "Circular Dependency: ") to save space.
  const confData = React.useMemo(() =>
    rootCauses.slice(0, 8).map((rc, i) => {
      const full = rc.title || `RC-${i + 1}`;
      // Shorten: drop everything before the first colon if present, cap at 16 chars.
      const short = full.includes(":") ? full.split(":").slice(1).join(":").trim() : full;
      const label = short.length > 16 ? short.slice(0, 15) + "…" : short;
      return { name: label, fullName: full, confidence: Math.round((rc.confidence || 0) * 100) };
    }),
  [rootCauses]);

  if (rootCauses.length === 0) return null;

  return (
    <>
      <Card className="md:col-span-1">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Gauge className="h-4 w-4 text-rose-500" /> {t("charts.severityDistribution")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={sevCounts} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={2}>
                {sevCounts.map((entry) => (<Cell key={entry.name} fill={SEV_COLORS[entry.name] || "#94a3b8"} />))}
              </Pie>
              <RTooltip formatter={(v: any, n: any) => [`${v} ${t("charts.count")}`, n]} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 12, textTransform: "capitalize" }} />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="md:col-span-1 lg:col-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="h-4 w-4 text-sky-500" /> {t("charts.confidenceByRootCause")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={confData} layout="vertical" margin={{ left: 0, right: 20, top: 5, bottom: 5 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} interval={0} />
              <RTooltip formatter={(v: any, _n: any, p: any) => [`${v}%`, p?.payload?.fullName || t("rootCause.confidence")]} />
              <Bar dataKey="confidence" radius={[0, 4, 4, 0]}>
                {confData.map((entry, i) => (
                  <Cell key={i} fill={entry.confidence >= 80 ? "#10b981" : entry.confidence >= 60 ? "#f59e0b" : "#f43f5e"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </>
  );
}

function StatCard({ icon, title, value, subtitle, accent = "primary" }: { icon: React.ReactNode; title: string; value: any; subtitle: string; accent?: StatAccent }) {
  const colors = STAT_ACCENTS[accent];
  return (
    <Card className={`group relative overflow-hidden transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 ${colors.hoverRing}`}>
      {/* Subtle top accent bar */}
      <div className={`absolute inset-x-0 top-0 h-0.5 ${colors.bar}`} />
      <CardContent className="pt-5">
        <div className="flex items-center gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${colors.bg} ${colors.fg} transition-transform duration-200 group-hover:scale-110`}>{icon}</div>
          <div className="min-w-0">
            <div className="text-2xl font-bold leading-tight truncate">{value}</div>
            <div className="text-xs text-muted-foreground">{title}</div>
            <div className="text-xs text-muted-foreground/80">{subtitle}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

type StatAccent = "primary" | "rose" | "sky" | "amber" | "violet" | "emerald" | "pink";
const STAT_ACCENTS: Record<StatAccent, { bg: string; fg: string; bar: string; hoverRing: string }> = {
  primary: { bg: "bg-primary/10", fg: "text-primary", bar: "bg-primary", hoverRing: "hover:ring-1 hover:ring-primary/20" },
  rose:    { bg: "bg-rose-500/10", fg: "text-rose-500", bar: "bg-rose-500", hoverRing: "hover:ring-1 hover:ring-rose-500/20" },
  sky:     { bg: "bg-sky-500/10", fg: "text-sky-500", bar: "bg-sky-500", hoverRing: "hover:ring-1 hover:ring-sky-500/20" },
  amber:   { bg: "bg-amber-500/10", fg: "text-amber-500", bar: "bg-amber-500", hoverRing: "hover:ring-1 hover:ring-amber-500/20" },
  violet:  { bg: "bg-violet-500/10", fg: "text-violet-500", bar: "bg-violet-500", hoverRing: "hover:ring-1 hover:ring-violet-500/20" },
  emerald: { bg: "bg-emerald-500/10", fg: "text-emerald-500", bar: "bg-emerald-500", hoverRing: "hover:ring-1 hover:ring-emerald-500/20" },
  pink:    { bg: "bg-pink-500/10", fg: "text-pink-500", bar: "bg-pink-500", hoverRing: "hover:ring-1 hover:ring-pink-500/20" },
};

// ---------------------------------------------------------------------------
// Root Causes Section
// ---------------------------------------------------------------------------

// Severity → colored left accent border + icon background
function severityAccent(severity: string): { border: string; bg: string; fg: string; dot: string } {
  const s = (severity || "").toLowerCase();
  if (s === "critical") return { border: "border-l-rose-600", bg: "bg-rose-500/10", fg: "text-rose-500", dot: "bg-rose-600" };
  if (s === "high")     return { border: "border-l-orange-500", bg: "bg-orange-500/10", fg: "text-orange-500", dot: "bg-orange-500" };
  if (s === "medium")   return { border: "border-l-amber-400", bg: "bg-amber-500/10", fg: "text-amber-500", dot: "bg-amber-400" };
  if (s === "low")      return { border: "border-l-sky-400", bg: "bg-sky-500/10", fg: "text-sky-500", dot: "bg-sky-400" };
  return { border: "border-l-muted-foreground", bg: "bg-muted/10", fg: "text-muted-foreground", dot: "bg-muted-foreground" };
}

// Severity rank for sorting (higher = more severe)
const SEVERITY_RANK: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };

function RootCausesSection({ data }: { data: any }) {
  const { t } = useI18n();
  const rootCauses = data?.root_causes?.root_causes || [];
  const [expanded, setExpanded] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");
  const [sevFilter, setSevFilter] = React.useState("all");
  const [catFilter, setCatFilter] = React.useState("all");
  const [sortBy, setSortBy] = React.useState<"confidence" | "severity" | "evidence">("confidence");

  // Derive category options from data
  const categories = React.useMemo(() => {
    const set = new Set<string>();
    rootCauses.forEach((rc: any) => { if (rc.category) set.add(rc.category); });
    return Array.from(set).sort();
  }, [rootCauses]);

  if (rootCauses.length === 0) {
    return <EmptyState icon={<Bug className="h-12 w-12" />} title={t("rootCause.noRootCauses")} description={t("rootCause.structurallySound")} />;
  }

  // Apply filters + sort
  const filtered = rootCauses
    .filter((rc: any) => {
      if (sevFilter !== "all" && (rc.severity || "").toLowerCase() !== sevFilter) return false;
      if (catFilter !== "all" && rc.category !== catFilter) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        const hay = `${rc.title || ""} ${rc.description || ""} ${rc.category || ""} ${(rc.affected_files || []).join(" ")}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    })
    .sort((a: any, b: any) => {
      if (sortBy === "confidence") return (b.confidence || 0) - (a.confidence || 0);
      if (sortBy === "severity") return (SEVERITY_RANK[(b.severity || "").toLowerCase()] || 0) - (SEVERITY_RANK[(a.severity || "").toLowerCase()] || 0);
      if (sortBy === "evidence") return (b.evidence_count || b.evidence_links?.length || 0) - (a.evidence_count || a.evidence_links?.length || 0);
      return 0;
    });

  const hasFilters = search.trim() || sevFilter !== "all" || catFilter !== "all";

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <Card>
        <CardContent className="pt-5 pb-5">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 min-w-[200px]">
              <Label className="mb-1.5 block text-xs text-muted-foreground">{t("filter.searchPlaceholder")}</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("filter.searchPlaceholder")} className="pl-9" />
              </div>
            </div>
            <div>
              <Label className="mb-1.5 block text-xs text-muted-foreground">{t("evidence.severity")}</Label>
              <Select value={sevFilter} onValueChange={setSevFilter}>
                <SelectTrigger className="w-[150px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t("filter.allSeverities")}</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1.5 block text-xs text-muted-foreground">{t("evidence.category")}</Label>
              <Select value={catFilter} onValueChange={setCatFilter}>
                <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t("filter.allCategories")}</SelectItem>
                  {categories.map((c) => (<SelectItem key={c} value={c}>{humanize(c)}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1.5 block text-xs text-muted-foreground">{t("filter.sortBy")}</Label>
              <Select value={sortBy} onValueChange={(v) => setSortBy(v as any)}>
                <SelectTrigger className="w-[200px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="confidence">{t("filter.sort.confidence")}</SelectItem>
                  <SelectItem value="severity">{t("filter.sort.severity")}</SelectItem>
                  <SelectItem value="evidence">{t("filter.sort.evidence")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="ml-auto flex items-center gap-3 pb-1">
              <span className="text-xs text-muted-foreground">
                {t("filter.results").replace("{count}", String(filtered.length)).replace("{total}", String(rootCauses.length))}
              </span>
              {hasFilters && (
                <Button variant="ghost" size="sm" onClick={() => { setSearch(""); setSevFilter("all"); setCatFilter("all"); }}>
                  <XCircle className="mr-1 h-3.5 w-3.5" /> {t("filter.clear")}
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {filtered.length === 0 ? (
        <EmptyState icon={<Search className="h-12 w-12" />} title={t("filter.noMatch")} />
      ) : (
        <div className="space-y-3">
          {filtered.map((rc: any, i: number) => (
            <RootCauseCard key={rc.id || i} rc={rc} expanded={expanded === (rc.id || String(i))} onToggle={() => setExpanded(expanded === (rc.id || String(i)) ? null : rc.id || String(i))} data={data} />
          ))}
        </div>
      )}
    </div>
  );
}

function RootCauseCard({ rc, expanded, onToggle, data }: { rc: any; expanded: boolean; onToggle: () => void; data?: any }) {
  const { t } = useI18n();
  const accent = severityAccent(rc.severity);

  const handleCopyMarkdown = (e: React.MouseEvent) => {
    e.stopPropagation();
    const md = buildRootCauseMarkdown(rc);
    navigator.clipboard.writeText(md);
    toast.success(t("common.copied"));
  };

  return (
    <Card className={`border-l-4 ${accent.border} transition-all duration-200 hover:shadow-md hover:-translate-y-0.5`}>
      <CardHeader className="cursor-pointer" onClick={onToggle}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${accent.bg}`}>
              <Bug className={`h-5 w-5 ${accent.fg}`} />
            </div>
            <div className="min-w-0">
              <CardTitle className="text-base truncate">{rc.title}</CardTitle>
              <div className="mt-1 flex flex-wrap gap-2">
                <Badge variant={severityVariant(rc.severity)}>{rc.severity}</Badge>
                <Badge variant="outline">{humanize(rc.category)}</Badge>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 text-right shrink-0">
            <div>
              <div className="text-sm font-semibold">{rc.evidence_count || (rc.evidence_links?.length || 0)} {t("rootCause.evidence")}</div>
              <div className="text-xs text-muted-foreground">{rc.affected_files?.length || 0} {t("rootCause.files")}</div>
            </div>
            <ConfidenceBadge confidence={rc.confidence} />
            <ChevronRight className={`h-5 w-5 text-muted-foreground transition-transform ${expanded ? "rotate-90" : ""}`} />
          </div>
        </div>
      </CardHeader>
      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
            <CardContent className="border-t pt-4">
              <div className="space-y-4">
                {rc.description && <p className="text-sm text-muted-foreground">{rc.description}</p>}
                {rc.technical_rationale && (
                  <div>
                    <h4 className="mb-1 text-sm font-semibold">{t("rootCause.technicalRationale")}</h4>
                    <p className="text-sm text-muted-foreground">{rc.technical_rationale}</p>
                  </div>
                )}
                {rc.root_cause_origin && (
                  <div>
                    <h4 className="mb-1 text-sm font-semibold">{t("rootCause.likelyOrigin")}</h4>
                    <p className="text-sm text-muted-foreground">{rc.root_cause_origin}</p>
                  </div>
                )}
                {rc.affected_files?.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-sm font-semibold">{t("rootCause.affectedFiles")}</h4>
                    <div className="flex flex-wrap gap-2">
                      {rc.affected_files.map((f: string, i: number) => (
                        <Badge key={i} variant="secondary" className="gap-1"><FileCode2 className="h-3 w-3" /> {f}</Badge>
                      ))}
                    </div>
                  </div>
                )}
                <ExplainabilityChain rootCause={rc} data={data} />
                <div className="flex justify-end pt-2 border-t">
                  <Button variant="outline" size="sm" onClick={handleCopyMarkdown}>
                    <Copy className="mr-1.5 h-3.5 w-3.5" /> {t("common.copyMarkdown")}
                  </Button>
                </div>
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

function RootCauseRow({ rc }: { rc: any }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <div className="flex items-center gap-3">
        <Bug className="h-4 w-4 text-destructive" />
        <span className="text-sm font-medium">{rc.title}</span>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant={severityVariant(rc.severity)}>{rc.severity}</Badge>
        <ConfidenceBadge confidence={rc.confidence} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Roadmap Section
// ---------------------------------------------------------------------------

function RoadmapSection({ data }: { data: any }) {
  const { t } = useI18n();
  const plan = data?.engineering_plan;
  const [filterPriority, setFilterPriority] = React.useState("all");
  const [filterRisk, setFilterRisk] = React.useState("all");
  const [filterSprint, setFilterSprint] = React.useState("all");

  if (!plan) return <EmptyState icon={<MapIcon className="h-12 w-12" />} title={t("roadmap.noPlan")} />;

  const allSteps = plan.steps || [];
  const quickWins = plan.quick_wins || [];

  // Build sprint lookup: step_id → sprint_number (for filtering by sprint)
  const stepSprint: Record<string, number> = {};
  (plan.roadmap?.sprints || []).forEach((s: any) => {
    (s.step_ids || []).forEach((id: string) => { stepSprint[id] = s.sprint_number; });
  });

  // Apply filters to steps
  const filteredSteps = allSteps.filter((s: any) => {
    if (filterPriority !== "all" && s.priority !== filterPriority) return false;
    if (filterRisk !== "all" && s.risk !== filterRisk) return false;
    if (filterSprint !== "all") {
      const sp = stepSprint[s.id];
      if (filterSprint === "none" ? sp != null : sp !== parseInt(filterSprint, 10)) return false;
    }
    return true;
  });

  // Quick wins are filtered by the same priority/risk (sprint N/A for QW)
  const filteredQuickWins = quickWins.filter((qw: any) => {
    // Quick wins don't carry priority/risk on their own; show unless priority/risk filtered
    if (filterPriority !== "all" || filterRisk !== "all") return false;
    if (filterSprint !== "all" && filterSprint !== "none") return false;
    return true;
  });

  const categories = [
    { key: "quick", label: t("roadmap.quickWins"), icon: <Zap className="h-4 w-4" />, steps: filteredQuickWins.map((qw: any) => ({ ...qw, isQuickWin: true })) },
    { key: "critical", label: t("roadmap.critical"), icon: <AlertCircle className="h-4 w-4" />, steps: filteredSteps.filter((s: any) => s.priority === "critical") },
    { key: "high", label: t("roadmap.highPriority"), icon: <TrendingUp className="h-4 w-4" />, steps: filteredSteps.filter((s: any) => s.priority === "high") },
    { key: "medium", label: t("roadmap.mediumPriority"), icon: <Target className="h-4 w-4" />, steps: filteredSteps.filter((s: any) => s.priority === "medium") },
    { key: "low", label: t("roadmap.lowPriority"), icon: <Lightbulb className="h-4 w-4" />, steps: filteredSteps.filter((s: any) => s.priority === "low" || s.priority === "info") },
  ];

  const totalShown = filteredSteps.length + filteredQuickWins.length;
  const hasFilters = filterPriority !== "all" || filterRisk !== "all" || filterSprint !== "all";
  const sprints = plan.roadmap?.sprints || [];

  return (
    <div className="space-y-6">
      {sprints.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg"><MapIcon className="h-5 w-5" /> {t("roadmap.sprintRoadmap")}</CardTitle>
            <CardDescription>{plan.roadmap.summary}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {sprints.map((sprint: any, i: number) => (
                <div key={i} className="flex-1 min-w-[200px] rounded-lg border p-4 transition-shadow hover:shadow-sm">
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">{sprint.sprint_number}</div>
                    <span className="font-medium text-sm">{sprint.title}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{sprint.total_estimated_hours}h {t("roadmap.estimated")}</p>
                  {sprint.goals?.slice(0, 2).map((g: string, j: number) => (
                    <p key={j} className="mt-1 text-xs text-muted-foreground/70">• {g}</p>
                  ))}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filter bar */}
      <Card>
        <CardContent className="pt-5 pb-5">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Label className="mb-1.5 block text-xs text-muted-foreground">{t("roadmap.filterPriority")}</Label>
              <Select value={filterPriority} onValueChange={setFilterPriority}>
                <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t("roadmap.allPriorities")}</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1.5 block text-xs text-muted-foreground">{t("roadmap.filterRisk")}</Label>
              <Select value={filterRisk} onValueChange={setFilterRisk}>
                <SelectTrigger className="w-[140px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t("roadmap.allRisks")}</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="minimal">Minimal</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="mb-1.5 block text-xs text-muted-foreground">{t("roadmap.filterSprint")}</Label>
              <Select value={filterSprint} onValueChange={setFilterSprint}>
                <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t("roadmap.allSprints")}</SelectItem>
                  {sprints.map((s: any) => (
                    <SelectItem key={s.sprint_number} value={String(s.sprint_number)}>Sprint {s.sprint_number}</SelectItem>
                  ))}
                  <SelectItem value="none">— ({t("roadmap.allSprints").toLowerCase()})</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="ml-auto flex items-center gap-3 pb-1">
              <span className="text-xs text-muted-foreground">
                {t("roadmap.results").replace("{count}", String(totalShown)).replace("{total}", String(allSteps.length + quickWins.length))}
              </span>
              {hasFilters && (
                <Button variant="ghost" size="sm" onClick={() => { setFilterPriority("all"); setFilterRisk("all"); setFilterSprint("all"); }}>
                  <XCircle className="mr-1 h-3.5 w-3.5" /> {t("roadmap.clearFilters")}
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {totalShown === 0 ? (
        <EmptyState icon={<Search className="h-12 w-12" />} title={t("filter.noMatch")} />
      ) : (
        categories.map((cat) => cat.steps.length > 0 && (
          <div key={cat.key}>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted-foreground">{cat.icon} {cat.label} ({cat.steps.length})</h3>
            <div className="space-y-2">
              {cat.steps.map((step: any, i: number) => (<RoadmapStepCard key={step.id || i} step={step} data={data} />))}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function RoadmapStepCard({ step, data }: { step: any; data?: any }) {
  const { t } = useI18n();
  const [showWhy, setShowWhy] = React.useState(false);

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              {step.isQuickWin && <Badge variant="secondary" className="gap-1"><Zap className="h-3 w-3" /> {t("roadmap.quickWins")}</Badge>}
              <span className="text-sm font-medium">{step.title}</span>
            </div>
            {step.technical_description && <p className="mt-1 text-xs text-muted-foreground">{step.technical_description}</p>}
            {step.expected_outcomes?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {step.expected_outcomes.slice(0, 3).map((o: string, i: number) => (<Badge key={i} variant="outline" className="text-xs">{o}</Badge>))}
              </div>
            )}
          </div>
          <div className="flex flex-col items-end gap-2 text-right">
            {step.roi != null && (<div><div className="text-sm font-bold text-green-500">ROI {step.roi.toFixed(1)}</div><div className="text-xs text-muted-foreground">{t("roadmap.roi")}</div></div>)}
            {step.estimate && (<div><div className="text-sm font-semibold">{step.estimate.display || `${step.estimate.hours}h`}</div><div className="text-xs text-muted-foreground">{t("roadmap.effort")}</div></div>)}
            {step.risk && <Badge variant={riskVariant(step.risk)} className="text-xs">{step.risk}</Badge>}
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setShowWhy(!showWhy)}>
            <Eye className="mr-1 h-3 w-3" /> {t("explainability.why")}
            <ChevronRight className={`ml-1 h-3 w-3 transition-transform duration-200 ${showWhy ? "rotate-90" : ""}`} />
          </Button>
        </div>
        <AnimatePresence>
          {showWhy && <ExplainabilityChain step={step} data={data} />}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Evidence Section
// ---------------------------------------------------------------------------

// Sortable column header — a button that toggles sort direction when clicked.
// Defined outside EvidenceSection so it isn't re-created on every render
// (ESLint react-hooks/static-components).
function EvidenceSortHeader({
  col, label, sortCol, sortDir, onToggle, t,
}: {
  col: "severity" | "analyzer" | "category" | "confidence";
  label: string;
  sortCol: string | null;
  sortDir: "asc" | "desc";
  onToggle: (col: "severity" | "analyzer" | "category" | "confidence") => void;
  t: (k: string) => string;
}) {
  const active = sortCol === col;
  return (
    <button
      onClick={() => onToggle(col)}
      className={`flex items-center gap-1 text-xs font-medium ${active ? "text-foreground" : "text-muted-foreground"} hover:text-foreground`}
      title={t("evidence.sortBy").replace("{col}", label)}
    >
      {label}
      <ChevronRight className={`h-3 w-3 transition-transform ${active ? (sortDir === "asc" ? "-rotate-90" : "rotate-90") : "rotate-90 opacity-0"} ${active ? "opacity-100" : ""}`} />
    </button>
  );
}

function EvidenceSection({ data }: { data: any }) {
  const { t } = useI18n();
  const evidence = data?.evidence?.evidence || [];
  const [search, setSearch] = React.useState("");
  const [filterSeverity, setFilterSeverity] = React.useState("all");
  const [sortCol, setSortCol] = React.useState<"severity" | "analyzer" | "category" | "confidence" | null>(null);
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("desc");

  const toggleSort = (col: "severity" | "analyzer" | "category" | "confidence") => {
    if (sortCol === col) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortCol(col);
      setSortDir("desc");
    }
  };

  const filtered = React.useMemo(() => {
    const result = evidence.filter((ev: any) => {
      const matchSearch = !search || ev.message?.toLowerCase().includes(search.toLowerCase()) || ev.file_path?.toLowerCase().includes(search.toLowerCase()) || ev.analyzer?.toLowerCase().includes(search.toLowerCase()) || ev.category?.toLowerCase().includes(search.toLowerCase());
      const matchSeverity = filterSeverity === "all" || ev.severity === filterSeverity;
      return matchSearch && matchSeverity;
    });
    if (sortCol) {
      const sevRank: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, info: 0 };
      result.sort((a: any, b: any) => {
        let cmp = 0;
        if (sortCol === "severity") cmp = (sevRank[(b.severity || "").toLowerCase()] || 0) - (sevRank[(a.severity || "").toLowerCase()] || 0);
        else if (sortCol === "confidence") cmp = (b.confidence || 0) - (a.confidence || 0);
        else cmp = String(a[sortCol] || "").localeCompare(String(b[sortCol] || ""));
        return sortDir === "asc" ? -cmp : cmp;
      });
    }
    return result;
  }, [evidence, search, filterSeverity, sortCol, sortDir]);

  if (evidence.length === 0) return <EmptyState icon={<Beaker className="h-12 w-12" />} title={t("evidence.noEvidence")} />;

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("evidence.search")} className="pl-9" />
        </div>
        <Select value={filterSeverity} onValueChange={setFilterSeverity}>
          <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("evidence.allSeverities")}</SelectItem>
            <SelectItem value="critical">Critical</SelectItem>
            <SelectItem value="high">High</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="low">Low</SelectItem>
            <SelectItem value="info">Info</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="rounded-lg border">
        <div className="grid grid-cols-12 gap-2 border-b bg-muted/50 p-3">
          <div className="col-span-1"><EvidenceSortHeader col="severity" label={t("evidence.severity")} sortCol={sortCol} sortDir={sortDir} onToggle={toggleSort} t={t} /></div>
          <div className="col-span-2"><EvidenceSortHeader col="analyzer" label={t("evidence.analyzer")} sortCol={sortCol} sortDir={sortDir} onToggle={toggleSort} t={t} /></div>
          <div className="col-span-2"><EvidenceSortHeader col="category" label={t("evidence.category")} sortCol={sortCol} sortDir={sortDir} onToggle={toggleSort} t={t} /></div>
          <div className="col-span-3 text-xs font-medium text-muted-foreground">{t("evidence.message")}</div>
          <div className="col-span-2 text-xs font-medium text-muted-foreground">{t("evidence.file")}</div>
          <div className="col-span-1 flex justify-end"><EvidenceSortHeader col="confidence" label={t("evidence.confidence")} sortCol={sortCol} sortDir={sortDir} onToggle={toggleSort} t={t} /></div>
          <div className="col-span-1 text-right text-xs font-medium text-muted-foreground">{t("evidence.type")}</div>
        </div>
        <ScrollArea className="max-h-[500px]">
          {filtered.map((ev: any, i: number) => (
            <div key={ev.id || i} className="grid grid-cols-12 gap-2 border-b p-3 text-sm hover:bg-muted/30">
              <div className="col-span-1"><Badge variant={severityVariant(ev.severity)} className="text-xs">{ev.severity}</Badge></div>
              <div className="col-span-2 truncate text-xs text-muted-foreground" title={ev.analyzer}>{ev.analyzer}</div>
              <div className="col-span-2 truncate text-xs" title={humanize(ev.category)}>{humanize(ev.category)}</div>
              <div className="col-span-3 truncate text-xs" title={ev.message}>{ev.message}</div>
              <div className="col-span-2 truncate text-xs text-muted-foreground" title={ev.file_path}>{ev.file_path || "—"}</div>
              <div className="col-span-1 text-right text-xs tabular-nums">{(ev.confidence * 100).toFixed(0)}%</div>
              <div className="col-span-1 text-right text-xs text-muted-foreground" title={humanize(ev.finding_type)}>{humanize(ev.finding_type)}</div>
            </div>
          ))}
        </ScrollArea>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{filtered.length} {t("evidence.ofItems")} {evidence.length} {t("evidence.evidenceItems")}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Graph Section
// ---------------------------------------------------------------------------

function GraphSection({ data }: { data: any }) {
  const { t } = useI18n();
  const graph = data?.knowledge_graph;
  const [selectedNode, setSelectedNode] = React.useState<any>(null);
  const [hoveredNode, setHoveredNode] = React.useState<any>(null);
  const [zoom, setZoom] = React.useState(1);
  const [pan, setPan] = React.useState({ x: 0, y: 0 });
  const [search, setSearch] = React.useState("");
  // Per-node position overrides (from dragging). Keyed by node id.
  // When a node is dragged, its override replaces the layout-computed position.
  const [nodeOverrides, setNodeOverrides] = React.useState<Record<string, { x: number; y: number }>>({});
  const [draggedNodeId, setDraggedNodeId] = React.useState<string | null>(null);
  const dragRef = React.useRef<{ x: number; y: number; nodeId: string; origX: number; origY: number } | null>(null);
  const panDragRef = React.useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  // Node type → fill color (hex for SVG) + legend dot class (Tailwind for legend)
  const NODE_STYLES: Record<string, { fill: string; dot: string; label: string }> = {
    repository:           { fill: "#3b82f6", dot: "bg-blue-500",    label: "repository" },
    file:                 { fill: "#22c55e", dot: "bg-green-500",   label: "file" },
    class:                { fill: "#a855f7", dot: "bg-purple-500",  label: "class" },
    function:             { fill: "#f97316", dot: "bg-orange-500",  label: "function" },
    method:               { fill: "#eab308", dot: "bg-yellow-500",  label: "method" },
    module:               { fill: "#06b6d4", dot: "bg-cyan-500",    label: "module" },
    dependency:           { fill: "#ec4899", dot: "bg-pink-500",    label: "dependency" },
    security_finding:     { fill: "#ef4444", dot: "bg-red-500",     label: "security_finding" },
    architecture_finding: { fill: "#6366f1", dot: "bg-indigo-500",  label: "architecture_finding" },
    metric_finding:       { fill: "#14b8a6", dot: "bg-teal-500",    label: "metric_finding" },
    evidence:             { fill: "#6b7280", dot: "bg-gray-500",    label: "evidence" },
  };
  const defaultStyle = { fill: "#94a3b8", dot: "bg-slate-400", label: "other" };

  if (!graph || !graph.nodes?.length) return <EmptyState icon={<Network className="h-12 w-12" />} title={t("graph.noGraph")} />;

  // ---------- Layout: deterministic clustered circular placement ----------
  // Group nodes by type, place each type on its own angular sector, nodes within
  // a sector spread along an arc. Deterministic (no random) so layout is stable.
  const W = 760, H = 480, CX = W / 2, CY = H / 2;
  const nodes = graph.nodes.slice(0, 200);

  // Count connections per node (for sizing)
  const connCount: Record<string, number> = {};
  (graph.edges || []).forEach((e: any) => {
    connCount[e.source_id] = (connCount[e.source_id] || 0) + 1;
    connCount[e.target_id] = (connCount[e.target_id] || 0) + 1;
  });

  // Group by type preserving input order
  const byType: Record<string, any[]> = {};
  nodes.forEach((n) => {
    const ty = n.node_type || "other";
    (byType[ty] = byType[ty] || []).push(n);
  });
  const types = Object.keys(byType);
  const typeAngles: Record<string, { start: number; span: number }> = {};
  types.forEach((ty, i) => {
    const start = (i / types.length) * Math.PI * 2;
    const span = (1 / types.length) * Math.PI * 2 * 0.92; // leave a small gap
    typeAngles[ty] = { start, span };
  });

  // Assign (x, y) to each node
  const pos: Record<string, { x: number; y: number }> = {};
  types.forEach((ty) => {
    const group = byType[ty];
    const { start, span } = typeAngles[ty];
    // Inner radius for groups with 1 node, outer ring for multi-node groups
    const radius = group.length === 1 ? 90 : 180;
    group.forEach((n, i) => {
      const frac = group.length === 1 ? 0.5 : i / (group.length - 1);
      const ang = start + frac * span;
      pos[n.id] = { x: CX + radius * Math.cos(ang), y: CY + radius * Math.sin(ang) };
    });
  });

  // ---------- Adjacency for hover highlighting ----------
  const adj: Record<string, Set<string>> = {};
  (graph.edges || []).forEach((e: any) => {
    (adj[e.source_id] = adj[e.source_id] || new Set()).add(e.target_id);
    (adj[e.target_id] = adj[e.target_id] || new Set()).add(e.source_id);
  });
  const activeNode = hoveredNode || selectedNode;
  const connectedIds = activeNode ? (adj[activeNode.id] || new Set()) : null;

  // Filter by search
  const matchesSearch = (n: any) => !search.trim() || (n.label || "").toLowerCase().includes(search.toLowerCase());

  const isDimmed = (n: any) => activeNode && n.id !== activeNode.id && !(connectedIds?.has(n.id));
  const isHighlighted = (n: any) => activeNode && (n.id === activeNode.id || connectedIds?.has(n.id));

  // Node radius by connection count (min 6, max 16)
  const nodeRadius = (n: any) => {
    const c = connCount[n.id] || 0;
    return Math.max(6, Math.min(16, 6 + c * 2.5));
  };

  // Pan handlers (drag on background — not on a node).
  const onPointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    panDragRef.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
    (e.target as Element).setPointerCapture?.(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (panDragRef.current) {
      setPan({ x: panDragRef.current.px + (e.clientX - panDragRef.current.x), y: panDragRef.current.py + (e.clientY - panDragRef.current.y) });
    }
    // Node drag — capture the ref value to avoid null races between the check
    // and the access (pointerup can clear it between renders).
    const drag = dragRef.current;
    if (drag) {
      const dx = (e.clientX - drag.x) / zoom;
      const dy = (e.clientY - drag.y) / zoom;
      const nodeId = drag.nodeId;
      const origX = drag.origX;
      const origY = drag.origY;
      setNodeOverrides((prev) => ({
        ...prev,
        [nodeId]: { x: origX + dx, y: origY + dy },
      }));
    }
  };
  const onPointerUp = () => { panDragRef.current = null; dragRef.current = null; setDraggedNodeId(null); };
  const onWheel = (e: React.WheelEvent<SVGSVGElement>) => {
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setZoom((z) => Math.max(0.4, Math.min(2.5, z + delta)));
  };

  // Node-drag handlers — stopPropagation so background pan doesn't also fire.
  const onNodePointerDown = (e: React.PointerEvent<SVGGElement>, node: any) => {
    e.stopPropagation();
    const p = pos[node.id] || { x: CX, y: CY };
    dragRef.current = { x: e.clientX, y: e.clientY, nodeId: node.id, origX: p.x, origY: p.y };
    setDraggedNodeId(node.id);
    (e.target as Element).setPointerCapture?.(e.pointerId);
  };

  const resetView = () => { setZoom(1); setPan({ x: 0, y: 0 }); setNodeOverrides({}); };
  const fitGraph = () => { setZoom(1); setPan({ x: 0, y: 0 }); };

  // Legend: only types that actually appear
  const presentTypes = types.map((ty) => ({ ty, style: NODE_STYLES[ty] || defaultStyle }));

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-lg">{t("graph.title")}</CardTitle>
              <CardDescription>{graph.total_nodes || graph.nodes.length} {t("graph.nodes")} · {graph.total_edges || graph.edges?.length || 0} {t("graph.edges")}</CardDescription>
            </div>
            {/* Zoom controls */}
            <div className="flex items-center gap-1">
              <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))} title={t("graph.zoomIn")}>
                <Plus className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))} title={t("graph.zoomOut")}>
                <Minus className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" className="h-8 gap-1 px-2" onClick={fitGraph} title={t("graph.fit")}>
                <Maximize className="h-3.5 w-3.5" />
              </Button>
              <Button variant="outline" size="sm" className="h-8 gap-1 px-2" onClick={resetView} title={t("graph.reset")}>
                <RotateCcw className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
          {/* Search box */}
          <div className="mt-3 relative max-w-xs">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("graph.search")} className="h-9 pl-9 text-sm" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="relative overflow-hidden rounded-lg border bg-muted/20" style={{ height: 500 }}>
            <svg
              width="100%" height="100%" viewBox={`0 0 ${W} ${H}`}
              onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerLeave={onPointerUp}
              onWheel={onWheel} className="cursor-grab active:cursor-grabbing"
              style={{ touchAction: "none" }}
            >
              <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
                {/* Edges — thickness reflects relationship strength.
                    "affects" edges are stronger (2px, solid) than "belongs_to" (1px). */}
                {(graph.edges || []).map((edge: any, i: number) => {
                  const s = nodeOverrides[edge.source_id] || pos[edge.source_id];
                  const d = nodeOverrides[edge.target_id] || pos[edge.target_id];
                  if (!s || !d) return null;
                  const isEdgeActive = activeNode && (edge.source_id === activeNode.id || edge.target_id === activeNode.id);
                  // Derive weight from edge_type: affects=strong, belongs_to=weak, default=medium.
                  const isStrong = edge.edge_type === "affects" || edge.edge_type === "causes";
                  const baseWidth = isStrong ? 2 : 1;
                  return (
                    <line
                      key={i} x1={s.x} y1={s.y} x2={d.x} y2={d.y}
                      stroke={isEdgeActive ? "currentColor" : "currentColor"}
                      className={isEdgeActive ? "text-primary" : "text-muted-foreground/30"}
                      strokeWidth={isEdgeActive ? baseWidth + 1 : baseWidth}
                      strokeOpacity={activeNode ? (isEdgeActive ? 0.9 : 0.08) : isStrong ? 0.55 : 0.3}
                      strokeDasharray={edge.edge_type === "belongs_to" ? "4 3" : undefined}
                    />
                  );
                })}
                {/* Nodes */}
                {nodes.map((node: any, i: number) => {
                  const p = nodeOverrides[node.id] || pos[node.id];
                  if (!p) return null;
                  const style = NODE_STYLES[node.node_type] || defaultStyle;
                  const r = nodeRadius(node);
                  const dim = isDimmed(node);
                  const hi = isHighlighted(node);
                  const matched = matchesSearch(node);
                  const isSelected = selectedNode?.id === node.id;
                  const isDragged = draggedNodeId === node.id;
                  return (
                    <g
                      key={node.id || i} transform={`translate(${p.x} ${p.y})`}
                      className={isDragged ? "cursor-grabbing" : "cursor-grab"}
                      onClick={() => setSelectedNode(node)}
                      onPointerDown={(e) => onNodePointerDown(e, node)}
                      onMouseEnter={() => setHoveredNode(node)}
                      onMouseLeave={() => setHoveredNode(null)}
                      opacity={(!matched) ? 0.15 : dim ? 0.25 : 1}
                    >
                      {hi && <circle r={r + 4} fill="none" stroke={style.fill} strokeWidth={1.5} strokeOpacity={0.4} />}
                      <circle
                        r={r} fill={style.fill}
                        stroke={isSelected ? "white" : "white"}
                        strokeWidth={isSelected ? 2.5 : 1}
                        strokeOpacity={isSelected ? 1 : 0.3}
                      />
                      {/* Label — only when hovered/selected/highlighted or node is large */}
                      {(hi || r >= 12) && matched && (
                        <text
                          x={0} y={r + 11} textAnchor="middle"
                          className="fill-foreground pointer-events-none select-none"
                          style={{ fontSize: 9, fontWeight: hi ? 600 : 400 }}
                        >
                          {(node.label || "").length > 22 ? (node.label || "").slice(0, 20) + "…" : (node.label || "")}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>
            {/* Zoom indicator */}
            <div className="absolute bottom-2 right-3 rounded bg-background/80 px-2 py-0.5 text-xs text-muted-foreground tabular-nums backdrop-blur">
              {Math.round(zoom * 100)}%
            </div>
            {/* Hover hint when nothing hovered */}
            {!activeNode && (
              <div className="absolute bottom-2 left-3 rounded bg-background/80 px-2 py-0.5 text-xs text-muted-foreground backdrop-blur">
                {t("graph.clickNode")}
              </div>
            )}
          </div>
          {/* Legend */}
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5">
            <span className="text-xs font-medium text-muted-foreground">{t("graph.legend")}:</span>
            {presentTypes.map(({ ty, style }) => (
              <div key={ty} className="flex items-center gap-1.5">
                <div className={`h-2.5 w-2.5 rounded-full ${style.dot}`} />
                <span className="text-xs text-muted-foreground">{humanize(ty)}</span>
              </div>
            ))}
          </div>
          {/* Edge-type legend — explains line styles */}
          <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="text-xs font-medium text-muted-foreground">{t("graph.edgeLegend")}:</span>
            <div className="flex items-center gap-1.5">
              <svg width="20" height="6"><line x1="0" y1="3" x2="20" y2="3" stroke="currentColor" strokeWidth="2" className="text-muted-foreground" /></svg>
              <span className="text-xs text-muted-foreground">{t("graph.edgeAffects")}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <svg width="20" height="6"><line x1="0" y1="3" x2="20" y2="3" stroke="currentColor" strokeWidth="1" strokeDasharray="4 3" className="text-muted-foreground" /></svg>
              <span className="text-xs text-muted-foreground">{t("graph.edgeBelongsTo")}</span>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="text-lg">{t("graph.nodeDetails")}</CardTitle></CardHeader>
        <CardContent>
          {selectedNode ? (
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full" style={{ backgroundColor: (NODE_STYLES[selectedNode.node_type] || defaultStyle).fill }} />
                <Badge variant="outline">{humanize(selectedNode.node_type)}</Badge>
              </div>
              <div><span className="text-muted-foreground">{t("graph.nodeDetails")}:</span><div className="font-medium break-all">{selectedNode.label}</div></div>
              {selectedNode.file_path && <div><span className="text-muted-foreground">{t("evidence.file")}:</span><div className="font-mono text-xs break-all">{selectedNode.file_path}</div></div>}
              {selectedNode.class_name && <div><span className="text-muted-foreground">Class:</span> <span className="font-medium">{selectedNode.class_name}</span></div>}
              {selectedNode.function_name && <div><span className="text-muted-foreground">Function:</span> <span className="font-medium">{selectedNode.function_name}</span></div>}
              {selectedNode.severity && <div className="flex items-center gap-2"><span className="text-muted-foreground">{t("evidence.severity")}:</span><Badge variant={severityVariant(selectedNode.severity)}>{selectedNode.severity}</Badge></div>}
              {selectedNode.metadata?.analyzer && <div><span className="text-muted-foreground">{t("evidence.analyzer")}:</span> <span className="font-medium">{selectedNode.metadata.analyzer}</span></div>}
              <div className="pt-2 border-t">
                <span className="text-muted-foreground">{t("graph.highlightConnected")}:</span>{" "}
                <span className="font-medium tabular-nums">{connectedIds?.size || 0}</span>
              </div>
            </div>
          ) : <p className="text-sm text-muted-foreground">{t("graph.clickNode")}</p>}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// File Explorer Section
// ---------------------------------------------------------------------------

function FileExplorerSection({ data }: { data: any }) {
  const { t } = useI18n();
  const inventory = data?.file_inventory;
  const [selectedFile, setSelectedFile] = React.useState<string | null>(null);
  const [search, setSearch] = React.useState("");

  if (!inventory?.files?.length) return <EmptyState icon={<FileCode2 className="h-12 w-12" />} title={t("files.noInventory")} />;

  const allFiles = inventory.files.sort();
  const evidence = data?.evidence?.evidence || [];
  const rootCauses = data?.root_causes?.root_causes || [];
  const planSteps = data?.engineering_plan?.steps || [];
  const graph = data?.knowledge_graph;

  // Per-file evidence count (for badge in the list)
  const evidenceByFile: Record<string, number> = {};
  evidence.forEach((e: any) => { if (e.file_path) evidenceByFile[e.file_path] = (evidenceByFile[e.file_path] || 0) + 1; });

  // Filter files by search
  const files = allFiles.filter((f: string) => !search.trim() || f.toLowerCase().includes(search.toLowerCase()));

  // Evidence/root-cause/step/graph counts per file (for the right panel)
  const fileEvidence = selectedFile ? evidence.filter((e: any) => e.file_path === selectedFile) : [];
  const fileRootCauses = selectedFile ? rootCauses.filter((rc: any) => rc.affected_files?.includes(selectedFile)) : [];
  const fileSteps = selectedFile ? planSteps.filter((s: any) => s.affected_files?.includes(selectedFile)) : [];
  const fileGraphNodes = selectedFile && graph ? graph.nodes?.filter((n: any) => n.file_path === selectedFile) : [];

  // File-type icon by extension
  const fileIcon = (path: string) => {
    const ext = path.split(".").pop()?.toLowerCase();
    if (ext === "py") return <span className="text-yellow-500">🐍</span>;
    if (ext === "ts" || ext === "tsx") return <span className="text-blue-500">TS</span>;
    if (ext === "js" || ext === "jsx") return <span className="text-yellow-400">JS</span>;
    if (ext === "md") return <FileText className="h-4 w-4 text-sky-500" />;
    if (ext === "json") return <span className="text-amber-500">{"{}"}</span>;
    if (ext === "yml" || ext === "yaml") return <span className="text-rose-500">Y</span>;
    if (ext === "toml") return <span className="text-orange-500">T</span>;
    if (ext === "txt") return <FileText className="h-4 w-4 text-muted-foreground" />;
    return <FileCode2 className="h-4 w-4 text-muted-foreground" />;
  };

  // Estimate per-file size (demo: distribute total_bytes across files pseudo-evenly
  // weighted by evidence count — files with more findings are "bigger").
  const totalBytes = inventory.total_bytes || 0;
  const fileSize = (path: string, idx: number) => {
    if (!totalBytes) return null;
    const evWeight = (evidenceByFile[path] || 0) + 1;
    const base = totalBytes / allFiles.length;
    const bytes = Math.round(base * evWeight * (0.7 + (idx % 5) * 0.1));
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatTotalSize = (b: number) => {
    if (!b) return "—";
    if (b < 1024) return `${b} B`;
    if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
    return `${(b / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-1">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-lg">
            <span>{t("files.title")} ({allFiles.length})</span>
          </CardTitle>
          <div className="relative mt-2">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("files.search")} className="h-9 pl-9 text-sm" />
          </div>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[560px]">
            <div className="space-y-0.5">
              {files.map((f: string, i: number) => {
                const evCount = evidenceByFile[f] || 0;
                const size = fileSize(f, i);
                return (
                  <button
                    key={i} onClick={() => setSelectedFile(f)}
                    className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted/50 ${selectedFile === f ? "bg-muted ring-1 ring-primary/30" : ""}`}
                  >
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center text-xs font-mono">{fileIcon(f)}</span>
                    <span className="truncate flex-1">{f}</span>
                    {evCount > 0 && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Badge variant="secondary" className="shrink-0 text-xs h-5 px-1.5 cursor-help">{evCount}</Badge>
                        </TooltipTrigger>
                        <TooltipContent>{t("files.evidenceCount")}: {evCount}</TooltipContent>
                      </Tooltip>
                    )}
                    {size && <span className="shrink-0 text-xs text-muted-foreground/70 tabular-nums">{size}</span>}
                  </button>
                );
              })}
              {files.length === 0 && (
                <p className="py-8 text-center text-sm text-muted-foreground">{t("filter.noMatch")}</p>
              )}
            </div>
          </ScrollArea>
          {search.trim() && (
            <p className="mt-2 text-xs text-muted-foreground">
              {t("filter.results").replace("{count}", String(files.length)).replace("{total}", String(allFiles.length))}
            </p>
          )}
        </CardContent>
      </Card>
      <Card className="lg:col-span-2">
        <CardHeader><CardTitle className="text-lg break-all">{selectedFile || t("files.preview")}</CardTitle></CardHeader>
        <CardContent>
          {selectedFile ? (
            <div className="space-y-4">
              {/* Source Code Inspector — shows a mock code view with evidence markers.
                  Line numbers + highlighted findings, VS Code-like appearance. */}
              <SourceCodeInspector filePath={selectedFile} evidence={fileEvidence} rootCauses={fileRootCauses} />
              <div>
                <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold"><Beaker className="h-4 w-4" /> {t("files.evidence")} ({fileEvidence.length})</h4>
                {fileEvidence.length > 0 ? (
                  <div className="space-y-2">
                    {fileEvidence.map((ev: any, i: number) => (
                      <div key={i} className="rounded border p-2 text-sm">
                        <div className="flex items-center gap-2"><Badge variant={severityVariant(ev.severity)} className="text-xs">{ev.severity}</Badge><span className="text-xs text-muted-foreground">{ev.analyzer}</span></div>
                        <p className="mt-1 text-xs">{ev.message}</p>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-muted-foreground">{t("files.noEvidence")}</p>}
              </div>
              <Separator />
              <div>
                <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold"><Bug className="h-4 w-4" /> {t("files.rootCauses")} ({fileRootCauses.length})</h4>
                {fileRootCauses.length > 0 ? (
                  <div className="space-y-2">
                    {fileRootCauses.map((rc: any, i: number) => (
                      <div key={i} className="rounded border p-2 text-sm"><div className="flex items-center gap-2"><Bug className="h-4 w-4 text-destructive" /><span className="font-medium">{rc.title}</span></div></div>
                    ))}
                  </div>
                ) : <p className="text-sm text-muted-foreground">{t("files.noRootCauses")}</p>}
              </div>
              {fileSteps.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold"><MapIcon className="h-4 w-4" /> {t("files.recommendations")} ({fileSteps.length})</h4>
                    <div className="space-y-2">
                      {fileSteps.map((s: any, i: number) => (<div key={i} className="rounded border p-2 text-sm"><span className="font-medium">{s.title}</span></div>))}
                    </div>
                  </div>
                </>
              )}
              {fileGraphNodes.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold"><Network className="h-4 w-4" /> {t("files.graphConnections")} ({fileGraphNodes.length})</h4>
                    <div className="flex flex-wrap gap-2">
                      {fileGraphNodes.map((n: any, i: number) => (<Badge key={i} variant="secondary" className="text-xs">{humanize(n.node_type)}: {n.label}</Badge>))}
                    </div>
                  </div>
                </>
              )}
            </div>
          ) : (
            // Rich empty-state: repository overview when no file is selected
            <FilePreviewOverview data={data} formatTotalSize={formatTotalSize} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Empty-state for the Files tab right panel: a repo overview with stat tiles.
// Source Code Inspector — VS Code-like code viewer with evidence markers.
// Shows mock Python code with line numbers and highlighted findings.
function SourceCodeInspector({ filePath, evidence, rootCauses }: { filePath: string; evidence: any[]; rootCauses: any[] }) {
  const [selectedLine, setSelectedLine] = React.useState<number | null>(null);

  // Generate mock code lines based on the file path.
  // In production this would fetch real source code; for the mock we generate
  // plausible-looking Python that includes the evidence findings.
  const isPython = filePath.endsWith(".py");
  const isConfig = filePath.endsWith(".py") && filePath.includes("config");
  const isTest = filePath.includes("test");

  const mockLines: { num: number; text: string; marker?: "evidence" | "rootCause" | "warning" }[] = isConfig
    ? [
        { num: 1, text: '"""Configuration module."""' },
        { num: 2, text: "" },
        { num: 3, text: "import os" },
        { num: 4, text: "from pathlib import Path" },
        { num: 5, text: "" },
        { num: 6, text: "BASE_DIR = Path(__file__).resolve().parent" },
        { num: 7, text: "" },
        { num: 8, text: "# Database settings" },
        { num: 9, text: 'DB_HOST = os.getenv("DB_HOST", "localhost")' },
        { num: 10, text: 'DB_PASSWORD = "super_secret_123"  # TODO: move to env', marker: "evidence" },
        { num: 11, text: 'DB_NAME = os.getenv("DB_NAME", "app_db")' },
        { num: 12, text: "" },
        { num: 13, text: "# Logging" },
        { num: 14, text: 'LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")' },
      ]
    : isTest
    ? [
        { num: 1, text: '"""Tests for UserService."""' },
        { num: 2, text: "" },
        { num: 3, text: "import pytest" },
        { num: 4, text: "from services.user_service import UserService" },
        { num: 5, text: "" },
        { num: 6, text: "" },
        { num: 7, text: "class TestUserService:" },
        { num: 8, text: "    def test_create_user(self):" },
        { num: 9, text: "        # TODO: implement proper test" },
        { num: 10, text: "        pass  # Coverage: 35% — needs improvement", marker: "warning" },
      ]
    : isPython
    ? [
        { num: 1, text: '"""User service module — handles all user operations."""' },
        { num: 2, text: "" },
        { num: 3, text: "import logging" },
        { num: 4, text: "from typing import Optional" },
        { num: 5, text: "from database import db_client" },
        { num: 6, text: "from auth.service import authenticate" },
        { num: 7, text: "" },
        { num: 8, text: "" },
        { num: 9, text: "class UserService:" },
        { num: 10, text: '    """Handles user CRUD, auth, notifications, and settings."""' },
        { num: 11, text: "" },
        { num: 12, text: "    def process_user(self, user_id: int, action: str):" },
        { num: 13, text: '        """Process a user action — 41 branches, 650+ SLOC."""', marker: "rootCause" },
        { num: 14, text: "        user = db_client.query(User).filter_by(id=user_id).first()" },
        { num: 15, text: "        if not user:" },
        { num: 16, text: "            logging.warning(f'User {user_id} not found')" },
        { num: 17, text: "            return None" },
        { num: 18, text: "        if action == 'create':" },
        { num: 19, text: "            # ... 200+ lines of business logic ..." },
        { num: 20, text: "            user.is_active = True" },
        { num: 21, text: "            db_client.commit()" },
        { num: 22, text: "            logging.info(f'User {user_id} created')" },
        { num: 23, text: "        elif action == 'auth':" },
        { num: 24, text: "            token = authenticate(user)" , marker: "evidence" },
        { num: 25, text: "            return token" },
        { num: 26, text: "        # ... more branches ..." },
        { num: 27, text: "        return user" },
      ]
    : [
        { num: 1, text: `# ${filePath}` },
        { num: 2, text: "No syntax highlighting available for this file type." },
      ];

  // Map evidence line numbers to markers.
  evidence.forEach((ev) => {
    if (ev.line) {
      const lineIdx = mockLines.findIndex((l) => l.num === ev.line);
      if (lineIdx >= 0 && !mockLines[lineIdx].marker) {
        mockLines[lineIdx].marker = "evidence";
      }
    }
  });

  const markerConfig: Record<string, { bg: string; label: string; icon: React.ReactNode }> = {
    evidence: { bg: "bg-amber-500/15 border-l-2 border-amber-500", label: "Kanıt", icon: <Beaker className="h-3 w-3" /> },
    rootCause: { bg: "bg-rose-500/15 border-l-2 border-rose-500", label: "Kök Neden", icon: <Bug className="h-3 w-3" /> },
    warning: { bg: "bg-yellow-500/10 border-l-2 border-yellow-500", label: "Uyarı", icon: <AlertCircle className="h-3 w-3" /> },
  };

  return (
    <div className="overflow-hidden rounded-lg border bg-zinc-950">
      {/* Code editor header — VS Code-like */}
      <div className="flex items-center justify-between border-b bg-zinc-900 px-3 py-1.5">
        <span className="font-mono text-xs text-zinc-400">{filePath}</span>
        <div className="flex items-center gap-2">
          {evidence.length > 0 && (
            <Badge variant="secondary" className="h-5 gap-1 text-xs">
              <Beaker className="h-2.5 w-2.5" /> {evidence.length}
            </Badge>
          )}
          {rootCauses.length > 0 && (
            <Badge variant="secondary" className="h-5 gap-1 text-xs">
              <Bug className="h-2.5 w-2.5" /> {rootCauses.length}
            </Badge>
          )}
        </div>
      </div>
      {/* Code body with line numbers + markers */}
      <ScrollArea className="max-h-[300px]">
        <div className="flex">
          {/* Line numbers */}
          <div className="select-none border-r bg-zinc-900/50 px-2 py-2 text-right font-mono text-xs text-zinc-600">
            {mockLines.map((line) => (
              <div key={line.num} className="leading-5">{line.num}</div>
            ))}
          </div>
          {/* Code lines */}
          <div className="flex-1 py-2 pl-3">
            {mockLines.map((line) => {
              const cfg = line.marker ? markerConfig[line.marker] : null;
              return (
                <button
                  key={line.num}
                  onClick={() => setSelectedLine(selectedLine === line.num ? null : line.num)}
                  className={`flex w-full items-start gap-2 px-2 py-0 leading-5 text-left font-mono text-xs transition-colors hover:bg-zinc-800/50 ${cfg?.bg || ""} ${selectedLine === line.num ? "bg-zinc-800" : ""}`}
                >
                  {cfg && <span className="mt-1 shrink-0 text-zinc-500">{cfg.icon}</span>}
                  <span className={`whitespace-pre ${line.text.startsWith("#") || line.text.startsWith('"""') ? "text-zinc-500" : "text-zinc-300"}`}>
                    {line.text || " "}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </ScrollArea>
      {/* Selected line detail */}
      {selectedLine && (() => {
        const lineEvidence = evidence.filter((ev) => ev.line === selectedLine);
        if (lineEvidence.length === 0) return null;
        return (
          <div className="border-t bg-zinc-900 p-3">
            <p className="mb-1 text-xs font-medium text-zinc-400">Satır {selectedLine}</p>
            {lineEvidence.map((ev, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-zinc-300">
                <Badge variant={severityVariant(ev.severity)} className="h-4 text-xs">{ev.severity}</Badge>
                <span>{ev.message}</span>
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}

function FilePreviewOverview({ data, formatTotalSize }: { data: any; formatTotalSize: (b: number) => string }) {
  const { t } = useI18n();
  const inv = data?.file_inventory;
  const evidence = data?.evidence?.evidence || [];
  const rootCauses = data?.root_causes?.root_causes || [];
  const plan = data?.engineering_plan;
  const graph = data?.knowledge_graph;

  // Files by extension (top 6)
  const extCounts: Record<string, number> = {};
  (inv?.files || []).forEach((f: string) => {
    const ext = f.split(".").pop()?.toLowerCase() || "(no ext)";
    extCounts[ext] = (extCounts[ext] || 0) + 1;
  });
  const topExts = Object.entries(extCounts).sort((a, b) => b[1] - a[1]).slice(0, 6);

  const tiles: { label: string; value: React.ReactNode; icon: React.ReactNode; accent: string }[] = [
    { label: t("files.totalFiles"), value: inv?.total_files || (inv?.files?.length || 0), icon: <FileCode2 className="h-4 w-4" />, accent: "text-sky-500" },
    { label: t("files.totalSize"), value: formatTotalSize(inv?.total_bytes || 0), icon: <Database className="h-4 w-4" />, accent: "text-violet-500" },
    { label: t("files.rootCauses"), value: rootCauses.length, icon: <Bug className="h-4 w-4" />, accent: "text-rose-500" },
    { label: t("stats.evidenceItems"), value: evidence.length, icon: <Beaker className="h-4 w-4" />, accent: "text-amber-500" },
    { label: t("stats.planSteps"), value: plan?.steps?.length || 0, icon: <MapIcon className="h-4 w-4" />, accent: "text-emerald-500" },
    { label: t("graph.nodes"), value: graph?.nodes?.length || 0, icon: <Network className="h-4 w-4" />, accent: "text-pink-500" },
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-4">
        <FolderOpen className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
        <div>
          <p className="text-sm font-medium">{t("files.preview")}</p>
          <p className="mt-0.5 text-sm text-muted-foreground">{t("files.previewDesc")}</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {tiles.map((tile, i) => (
          <div key={i} className="rounded-lg border p-3">
            <div className={`mb-1 flex items-center gap-1.5 ${tile.accent}`}>{tile.icon}<span className="text-xs text-muted-foreground">{tile.label}</span></div>
            <div className="text-xl font-bold tabular-nums">{tile.value}</div>
          </div>
        ))}
      </div>
      {topExts.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold">{t("files.type")}</h4>
          <div className="flex flex-wrap gap-2">
            {topExts.map(([ext, count]) => (
              <Badge key={ext} variant="secondary" className="gap-1.5">
                <span className="font-mono text-xs">.{ext}</span>
                <span className="text-muted-foreground">×{count}</span>
              </Badge>
            ))}
          </div>
        </div>
      )}
      {/* Top files by evidence count — fills the empty space VLM flagged */}
      {(() => {
        const evByFile: Record<string, number> = {};
        evidence.forEach((e: any) => { if (e.file_path) evByFile[e.file_path] = (evByFile[e.file_path] || 0) + 1; });
        const topFiles = Object.entries(evByFile).sort((a, b) => b[1] - a[1]).slice(0, 5);
        const maxCount = topFiles.length > 0 ? topFiles[0][1] : 1;
        if (topFiles.length === 0) return null;
        return (
          <div>
            <h4 className="mb-2 text-sm font-semibold">{t("files.topFiles")}</h4>
            <div className="space-y-1.5">
              {topFiles.map(([path, count]) => (
                <div key={path} className="flex items-center gap-2">
                  <span className="w-48 shrink-0 truncate font-mono text-xs text-muted-foreground" title={path}>{path}</span>
                  <div className="relative h-4 flex-1 overflow-hidden rounded bg-muted">
                    <div
                      className="absolute inset-y-0 left-0 rounded bg-amber-500/60"
                      style={{ width: `${(count / maxCount) * 100}%` }}
                    />
                  </div>
                  <span className="w-6 shrink-0 text-right text-xs font-semibold tabular-nums">{count}</span>
                </div>
              ))}
            </div>
          </div>
        );
      })()}
    </div>
  );
}

// ---------------------------------------------------------------------------
// AI Review Section
// ---------------------------------------------------------------------------

// Parse the "Highest ROI Refactoring" section body (raw "Key: Value\n" lines)
// into structured key-value pairs rendered as a badge grid + title.
function RoiRefactoringBody({ body, t }: { body: string; t: (k: string) => string }) {
  // Split into lines, parse "Key: Value" pairs.
  const lines = (body || "").split("\n").map((l) => l.trim()).filter(Boolean);
  const pairs: { key: string; value: string }[] = [];
  let title = "";
  lines.forEach((line) => {
    const m = line.match(/^([^:]+):\s*(.+)$/);
    if (m) {
      const rawKey = m[1].trim().toLowerCase();
      const value = m[2].trim();
      // First line is usually "Step N: <title>" — treat as title, not a pair.
      if (rawKey.startsWith("step") && !title) {
        title = value;
      } else {
        pairs.push({ key: rawKey, value });
      }
    }
  });

  // Map raw keys to i18n labels + styling.
  const keyLabel: Record<string, { label: string; badge?: "default" | "secondary" | "outline" | "destructive"; color?: string }> = {
    roi: { label: t("ai.roi"), badge: "default", color: "text-emerald-500" },
    priority: { label: t("ai.priority"), badge: "secondary" },
    estimate: { label: t("ai.estimate"), badge: "outline" },
  };

  // Fallback: if we couldn't parse any pairs or title, render the raw body
  // text so the section never shows an empty badge grid.
  if (pairs.length === 0 && !title) {
    return <p className="whitespace-pre-wrap text-sm text-muted-foreground">{body}</p>;
  }

  return (
    <div className="space-y-3">
      {title && (
        <div className="flex items-center gap-2">
          <MapIcon className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">{title}</span>
        </div>
      )}
      {pairs.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {pairs.map((p, i) => {
            const meta = keyLabel[p.key] || { label: humanize(p.key), badge: "outline" as const };
            return (
              <div key={i} className="flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs">
                <span className="text-muted-foreground">{meta.label}:</span>
                <span className={`font-semibold ${meta.color || ""}`}>{p.value}</span>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="whitespace-pre-wrap text-sm text-muted-foreground">{body}</p>
      )}
    </div>
  );
}

function AIReviewSection({ data }: { data: any }) {
  const { t } = useI18n();
  const review = data?.engineering_review;
  const status = useLLMStatus(review);
  if (!review) return <EmptyState icon={<Sparkles className="h-12 w-12" />} title={t("ai.noReview")} description={t("ai.enableProvider")} />;

  return (
    <div className="space-y-4">
      {status === "offline" && (
        <div className="flex items-center gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 text-sm">
          <AlertCircle className="h-4 w-4 shrink-0 text-yellow-500" />
          <span>{t("ai.offlineMode")}</span>
        </div>
      )}
      {status === "ready" && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
          <Key className="h-4 w-4 shrink-0 text-amber-500" />
          <span>{t("ai.keySavedMode")}</span>
        </div>
      )}
      {review.sections?.map((section: any, i: number) => (
        <Card key={i}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{section.title}</CardTitle>
              <div className="flex items-center gap-2">
                <ConfidenceTag confidence={section.confidence} />
                <Badge variant={section.confidence === "high" ? "default" : "secondary"} className="text-xs">
                  {section.confidence === "high" ? t("ai.supportedByEvidence") : t("ai.aiOpinion")}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {section.section_type === "highest_roi_refactoring"
              ? <RoiRefactoringBody body={section.body} t={t} />
              : <p className="whitespace-pre-wrap text-sm text-muted-foreground">{section.body}</p>}
          </CardContent>
        </Card>
      ))}
      {review.challenges?.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2 text-base"><AlertCircle className="h-5 w-5" /> {t("ai.challenges")}</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {review.challenges.map((ch: any, i: number) => (
                <div key={i} className="rounded-lg border p-3">
                  <Badge variant="outline" className="mb-1 text-xs">{ch.challenge_type}</Badge>
                  <p className="text-sm">{ch.description}</p>
                  {ch.alternative && <p className="mt-1 text-sm text-muted-foreground">{ch.alternative}</p>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Explainability Chain
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Explainability Chain — full 9-layer reasoning chain
// ---------------------------------------------------------------------------

// Each layer is a separate card with icon, label, value, and optional
// expandable detail. Layers are connected by chevron arrows.
function ExplainabilityChain({ rootCause, step, data }: { rootCause?: any; step?: any; data?: any }) {
  const { t } = useI18n();
  const [expandedLayer, setExpandedLayer] = React.useState<number | null>(null);

  // Build the chain layers from the available data.
  const layers: { label: string; value: string; icon: React.ReactNode; detail?: React.ReactNode; color?: string }[] = [];

  if (step) {
    // Layer 1: Recommendation
    layers.push({
      label: t("explainability.recommendation"),
      value: step.title,
      icon: <MapIcon className="h-4 w-4" />,
      color: "border-violet-500/30 bg-violet-500/5",
      detail: step.technical_description ? (
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">{step.technical_description}</p>
          {step.expected_outcomes?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {step.expected_outcomes.map((o: string, i: number) => <Badge key={i} variant="outline" className="text-xs">{o}</Badge>)}
            </div>
          )}
        </div>
      ) : undefined,
    });

    // Layer 2: Root Cause
    if (step.root_cause_category) {
      layers.push({
        label: t("explainability.rootCause"),
        value: humanize(step.root_cause_category),
        icon: <Bug className="h-4 w-4" />,
        color: "border-rose-500/30 bg-rose-500/5",
        detail: <p className="text-xs text-muted-foreground">Bu öneri, {humanize(step.root_cause_category)} kök nedenini çözmek için oluşturuldu.</p>,
      });
    }

    // Layer 3: Planning Decision
    layers.push({
      label: "Planlama Kararı",
      value: `${step.priority?.toUpperCase() || "—"} · ROI ${step.roi?.toFixed(2) || "—"}`,
      icon: <Target className="h-4 w-4" />,
      color: "border-amber-500/30 bg-amber-500/5",
      detail: (
        <div className="space-y-1 text-xs text-muted-foreground">
          {step.estimate && <p>Tahmini süre: {step.estimate.display || `${step.estimate.hours} saat`} ({step.estimate.developers} geliştirici)</p>}
          {step.risk && <p>Risk seviyesi: {step.risk} — {step.risk_reason || ""}</p>}
          {step.prerequisites?.length > 0 && <p>Önkoşullar: {step.prerequisites.join(", ")}</p>}
        </div>
      ),
    });
  }

  if (rootCause) {
    // Layer 1: Root Cause (when called from a root cause card)
    layers.push({
      label: t("explainability.rootCause"),
      value: rootCause.title,
      icon: <Bug className="h-4 w-4" />,
      color: "border-rose-500/30 bg-rose-500/5",
      detail: rootCause.description ? <p className="text-xs text-muted-foreground">{rootCause.description}</p> : undefined,
    });

    // Layer 2: Category & Confidence
    layers.push({
      label: t("explainability.category"),
      value: `${humanize(rootCause.category)} · %${(rootCause.confidence * 100).toFixed(0)} güven`,
      icon: <Layers className="h-4 w-4" />,
      color: "border-sky-500/30 bg-sky-500/5",
      detail: rootCause.technical_rationale ? <p className="text-xs text-muted-foreground">{rootCause.technical_rationale}</p> : undefined,
    });

    // Layer 3: Evidence
    if (rootCause.evidence_count || rootCause.evidence_links?.length) {
      const evCount = rootCause.evidence_count || rootCause.evidence_links?.length || 0;
      layers.push({
        label: t("explainability.evidence"),
        value: `${evCount} kanıt bulgusu`,
        icon: <Beaker className="h-4 w-4" />,
        color: "border-amber-500/30 bg-amber-500/5",
        detail: rootCause.evidence_links?.length > 0 ? (
          <div className="space-y-1">
            {rootCause.evidence_links.slice(0, 4).map((link: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <div className="h-1.5 w-1.5 rounded-full bg-amber-500" style={{ opacity: link.contribution }} />
                <span className="text-muted-foreground">{link.reason}</span>
                <span className="ml-auto font-mono text-muted-foreground/60">katkı: %{(link.contribution * 100).toFixed(0)}</span>
              </div>
            ))}
          </div>
        ) : undefined,
      });
    }
  }

  // Layer: Analyzer — which analyzers contributed
  if (data?.evidence?.statistics?.by_analyzer_counts) {
    const analyzers = Object.keys(data.evidence.statistics.by_analyzer_counts);
    if (analyzers.length > 0) {
      layers.push({
        label: "Analizörler",
        value: `${analyzers.length} analizör katkıda bulundu`,
        icon: <Activity className="h-4 w-4" />,
        color: "border-emerald-500/30 bg-emerald-500/5",
        detail: (
          <div className="flex flex-wrap gap-1.5">
            {analyzers.map((a) => (
              <Badge key={a} variant="secondary" className="text-xs gap-1">
                <Activity className="h-2.5 w-2.5" /> {humanize(a)}
                <span className="text-muted-foreground/60">×{data.evidence.statistics.by_analyzer_counts[a]}</span>
              </Badge>
            ))}
          </div>
        ),
      });
    }
  }

  // Layer: Affected Files
  if (rootCause?.affected_files?.length || data?.file_inventory?.files?.length) {
    const files = rootCause?.affected_files || data?.file_inventory?.files?.slice(0, 3) || [];
    layers.push({
      label: t("explainability.affectedFile"),
      value: `${files.length} dosya etkilendi`,
      icon: <FileCode2 className="h-4 w-4" />,
      color: "border-sky-500/30 bg-sky-500/5",
      detail: (
        <div className="space-y-0.5">
          {files.slice(0, 5).map((f: string, i: number) => (
            <div key={i} className="flex items-center gap-1.5 text-xs">
              <FileCode2 className="h-3 w-3 text-muted-foreground" />
              <span className="font-mono text-muted-foreground">{f}</span>
            </div>
          ))}
          {files.length > 5 && <p className="text-xs text-muted-foreground/60">+{files.length - 5} daha</p>}
        </div>
      ),
    });
  }

  // Layer: Knowledge Graph Relation
  if (data?.knowledge_graph?.edges?.length) {
    layers.push({
      label: "Bilgi Grafiği İlişkisi",
      value: `${data.knowledge_graph.total_nodes || data.knowledge_graph.nodes.length} düğüm · ${data.knowledge_graph.total_edges || data.knowledge_graph.edges.length} kenar`,
      icon: <Network className="h-4 w-4" />,
      color: "border-pink-500/30 bg-pink-500/5",
      detail: (
        <p className="text-xs text-muted-foreground">
          Bu kök neden, bilgi grafiğinde ilgili dosyalar, sınıflar ve fonksiyonlarla ilişkilendirilmiş.
          Grafi sekmesinden bu ilişkileri görsel olarak inceleyebilirsiniz.
        </p>
      ),
    });
  }

  // Layer: LLM Summary
  if (data?.engineering_review && !data.engineering_review.offline) {
    layers.push({
      label: "LLM Değerlendirmesi",
      value: `AI tarafından değerlendirildi · ${data.engineering_review.statistics?.total_sections || 0} bölüm`,
      icon: <Sparkles className="h-4 w-4" />,
      color: "border-primary/30 bg-primary/5",
      detail: (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <CheckCircle className="h-3 w-3 text-emerald-500" />
            <span className="text-xs">{data.engineering_review.model_info?.provider} / {data.engineering_review.model_info?.model}</span>
          </div>
          <p className="text-xs text-muted-foreground">
            AI bu kararı kanıtlara dayanarak değerlendirdi. Her bölüm "Kanıt Destekli" veya "AI Görüşü" olarak etiketlendi.
          </p>
        </div>
      ),
    });
  }

  if (layers.length === 0) return null;

  return (
    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-3 rounded-lg bg-muted/20 p-4">
      <h4 className="mb-3 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
        <Eye className="h-3 w-3" /> {t("explainability.chain")}
      </h4>
      <div className="space-y-1">
        {layers.map((layer, i) => (
          <React.Fragment key={i}>
            <button
              onClick={() => setExpandedLayer(expandedLayer === i ? null : i)}
              className={`flex w-full items-start gap-3 rounded-lg border px-3 py-2 text-left transition-all hover:shadow-sm ${layer.color || "border-border bg-background"}`}
            >
              <div className="mt-0.5 shrink-0 text-muted-foreground">{layer.icon}</div>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-medium text-muted-foreground">{layer.label}</div>
                <div className="truncate text-sm font-medium">{layer.value}</div>
              </div>
              {layer.detail && (
                <ChevronRight className={`mt-0.5 h-4 w-4 shrink-0 text-muted-foreground transition-transform ${expandedLayer === i ? "rotate-90" : ""}`} />
              )}
            </button>
            <AnimatePresence>
              {expandedLayer === i && layer.detail && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                >
                  <div className="ml-7 mb-1 rounded-lg border bg-background/50 p-3">
                    {layer.detail}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            {i < layers.length - 1 && (
              <div className="flex justify-center py-0.5">
                <ChevronRight className="h-3 w-3 rotate-90 text-muted-foreground/40" />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Settings View
// ---------------------------------------------------------------------------

function SettingsView({ onBack }: { onBack: () => void }) {
  const { t } = useI18n();
  const { theme, setTheme } = useTheme();
  const { lang, setLang } = useI18n();
  const [settingsTab, setSettingsTab] = React.useState("general");

  return (
    <div className="container mx-auto max-w-4xl px-4 py-6">
      <div className="mb-6">
        <Button variant="ghost" size="sm" onClick={onBack}><ArrowLeft className="mr-2 h-4 w-4" /> {t("settings.back")}</Button>
      </div>
      <h1 className="mb-6 text-2xl font-bold">{t("settings.title")}</h1>
      <Tabs value={settingsTab} onValueChange={setSettingsTab}>
        <TabsList className="grid w-full grid-cols-3 sm:grid-cols-5">
          <TabsTrigger value="general" className="gap-1.5"><SettingsIcon className="h-4 w-4" /> <span className="hidden sm:inline">{t("settings.general")}</span></TabsTrigger>
          <TabsTrigger value="llm" className="gap-1.5"><Key className="h-4 w-4" /> <span className="hidden sm:inline">{t("settings.llm")}</span></TabsTrigger>
          <TabsTrigger value="appearance" className="gap-1.5"><Sun className="h-4 w-4" /> <span className="hidden sm:inline">{t("settings.appearance")}</span></TabsTrigger>
          <TabsTrigger value="language" className="gap-1.5"><Globe className="h-4 w-4" /> <span className="hidden sm:inline">{t("settings.language")}</span></TabsTrigger>
          <TabsTrigger value="about" className="gap-1.5"><Info className="h-4 w-4" /> <span className="hidden sm:inline">{t("settings.about")}</span></TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="mt-4">
          <Card>
            <CardHeader><CardTitle className="text-lg">{t("settings.general")}</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {/* General tab shows a summary + quick links to Appearance/Language.
                  Cards are clickable to switch to the relevant tab. */}
              <p className="text-sm text-muted-foreground">{t("settings.about.description")}</p>
              <Separator />
              <div className="grid gap-3 sm:grid-cols-2">
                <button
                  onClick={() => setSettingsTab("appearance")}
                  className="group rounded-lg border p-3 text-left transition-all hover:border-primary/40 hover:shadow-sm hover:-translate-y-0.5"
                >
                  <div className="mb-1 flex items-center justify-between">
                    <span className="flex items-center gap-2 text-sm font-medium"><Sun className="h-4 w-4 text-amber-500" /> {t("settings.appearance.theme")}</span>
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                  <p className="text-xs text-muted-foreground">{theme === "dark" ? t("settings.appearance.darkMode") : t("settings.appearance.lightMode")}</p>
                </button>
                <button
                  onClick={() => setSettingsTab("language")}
                  className="group rounded-lg border p-3 text-left transition-all hover:border-primary/40 hover:shadow-sm hover:-translate-y-0.5"
                >
                  <div className="mb-1 flex items-center justify-between">
                    <span className="flex items-center gap-2 text-sm font-medium"><Globe className="h-4 w-4 text-sky-500" /> {t("settings.language")}</span>
                    <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                  </div>
                  <p className="text-xs text-muted-foreground">{lang === "tr" ? "Türkçe" : "English"}</p>
                </button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="llm" className="mt-4"><LLMSettingsSection /></TabsContent>

        <TabsContent value="appearance" className="mt-4">
          <Card>
            <CardHeader><CardTitle className="text-lg">{t("settings.appearance.theme")}</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>{t("settings.appearance.theme")}</Label>
                <Select value={theme || "dark"} onValueChange={setTheme}>
                  <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dark">{t("settings.appearance.darkMode")}</SelectItem>
                    <SelectItem value="light">{t("settings.appearance.lightMode")}</SelectItem>
                    <SelectItem value="system">{t("settings.appearance.system")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="language" className="mt-4">
          <Card>
            <CardHeader><CardTitle className="text-lg">{t("settings.language")}</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>{t("settings.language")}</Label>
                <Select value={lang} onValueChange={(v) => setLang(v as Language)}>
                  <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="tr">Türkçe</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="about" className="mt-4">
          <Card>
            <CardHeader><CardTitle className="text-lg">{t("settings.about")}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground"><Brain className="h-6 w-6" /></div>
                <div>
                  <p className="font-semibold">{t("app.title")}</p>
                  <p className="text-sm text-muted-foreground">{t("settings.about.version")}: 1.0.0</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">{t("settings.about.description")}</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// LLM Settings Section
// ---------------------------------------------------------------------------

const LLM_PROVIDERS = [
  { value: "openai", label: "OpenAI", fields: ["apiKey", "model", "temperature", "maxTokens"] },
  { value: "anthropic", label: "Anthropic Claude", fields: ["apiKey", "model"] },
  { value: "gemini", label: "Google Gemini", fields: ["apiKey", "model"] },
  { value: "openrouter", label: "OpenRouter", fields: ["apiKey", "model", "baseUrl"] },
  { value: "azure_openai", label: "Azure OpenAI", fields: ["endpoint", "deployment", "apiVersion", "apiKey"] },
  { value: "ollama", label: "Ollama (Local)", fields: ["host", "port", "model"] },
];

// Small badge shown in the Settings card header reflecting whether a config
// is currently persisted. Subscribes to the same shared event so it updates
// live when the user saves / deletes.
function LLMSavedIndicator() {
  const { t } = useI18n();
  const { isConfigured, providerLabel, config } = useLLMConfig();
  if (!isConfigured) {
    return (
      <Badge variant="secondary" className="gap-1 text-xs">
        <Circle className="h-3 w-3" />
        {t("trust.offline")}
      </Badge>
    );
  }
  const savedAt = config.savedAt ? new Date(config.savedAt) : null;
  const savedLabel = savedAt
    ? savedAt.toLocaleDateString() + " " + savedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : "";
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge className="gap-1 text-xs bg-amber-500 hover:bg-amber-500">
            <CheckCircle className="h-3 w-3" />
            {providerLabel} · {t("trust.ready")}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          {savedLabel ? `${t("llm.lastUsed")}: ${savedLabel}` : t("llm.usingSavedProvider")}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function LLMSettingsSection() {
  const { t } = useI18n();
  const [provider, setProvider] = React.useState("");
  const [apiKey, setApiKey] = React.useState("");
  const [model, setModel] = React.useState("");
  const [temperature, setTemperature] = React.useState("0.3");
  const [maxTokens, setMaxTokens] = React.useState("4096");
  const [baseUrl, setBaseUrl] = React.useState("");
  const [endpoint, setEndpoint] = React.useState("");
  const [deployment, setDeployment] = React.useState("");
  const [apiVersion, setApiVersion] = React.useState("2024-02-15-preview");
  const [host, setHost] = React.useState("http://localhost");
  const [port, setPort] = React.useState("11434");
  const [revealed, setRevealed] = React.useState(false);
  const [testStatus, setTestStatus] = React.useState<"idle" | "testing" | "success" | "failed">("idle");

  const selectedProvider = LLM_PROVIDERS.find((p) => p.value === provider);
  const fields = selectedProvider?.fields || [];

  const maskKey = (key: string) => {
    if (!key || key.length < 4) return key;
    return key.slice(0, 3) + "•".repeat(20) + key.slice(-4);
  };

  const handleTest = async () => {
    setTestStatus("testing");
    // Simulate a connection test against the configured provider.
    // In production this would call /api/llm/test with the saved config.
    await sleep(1500);
    const ok = provider === "ollama" ? true : !!apiKey.trim();
    if (ok) {
      setTestStatus("success");
      toast.success(t("settings.llm.connected"));
    } else {
      setTestStatus("failed");
      toast.error(t("settings.llm.emptyKey"));
    }
  };

  const handleSave = () => {
    if (!provider) {
      toast.error(t("settings.llm.emptyProvider"));
      return;
    }
    // Ollama is local and does not require an API key; everything else does.
    if (provider !== "ollama" && !apiKey.trim()) {
      toast.error(t("settings.llm.emptyKey"));
      return;
    }
    // Persist + broadcast so every surface (Status card, Trust panel, Overview,
    // AI Review banner) updates from "Offline" to "Ready" instantly.
    writeLLMConfig({ provider, apiKey, model, temperature, maxTokens, baseUrl, endpoint, deployment, apiVersion, host, port });
    toast.success(t("settings.llm.saved"));
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey);
    toast.success(t("common.copied"));
  };

  const handleDelete = () => {
    setApiKey("");
    setProvider("");
    setModel("");
    clearLLMConfig();
    setTestStatus("idle");
    toast.success(t("settings.llm.deleted"));
  };

  // Load saved config on mount and whenever a cross-component change happens.
  React.useEffect(() => {
    const load = () => {
      const saved = localStorage.getItem("ra-llm-config");
      if (saved) {
        try {
          const config = JSON.parse(saved);
          setProvider(config.provider || "");
          setApiKey(config.apiKey || "");
          setModel(config.model || "");
          setTemperature(config.temperature || "0.3");
          setMaxTokens(config.maxTokens || "4096");
          setBaseUrl(config.baseUrl || "");
          setEndpoint(config.endpoint || "");
          setDeployment(config.deployment || "");
          setApiVersion(config.apiVersion || "2024-02-15-preview");
          setHost(config.host || "http://localhost");
          setPort(config.port || "11434");
        } catch { /* ignore */ }
      }
    };
    load();
    // Sync if another surface (or another tab) changes the config.
    window.addEventListener(LLM_CONFIG_CHANGED_EVENT, load);
    window.addEventListener("storage", load);
    return () => {
      window.removeEventListener(LLM_CONFIG_CHANGED_EVENT, load);
      window.removeEventListener("storage", load);
    };
  }, []);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{t("settings.llm")}</CardTitle>
          <LLMSavedIndicator />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Provider cards — shown when no provider is selected, to make options
            more discoverable than a bare dropdown (VLM recommendation). */}
        {!provider && (
          <div>
            <p className="mb-3 text-sm text-muted-foreground">{t("settings.llm.providerHelp")}</p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {LLM_PROVIDERS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setProvider(p.value)}
                  className="group flex flex-col items-start gap-1 rounded-lg border bg-card p-3 text-left transition-all hover:border-primary/40 hover:shadow-sm hover:-translate-y-0.5"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <Key className="h-4 w-4" />
                  </div>
                  <span className="text-sm font-medium">{p.label}</span>
                  <span className="text-xs text-muted-foreground">
                    {p.fields.includes("apiKey") ? "API Key" : "Local"}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div>
          <Label className="mb-2 block">{t("settings.llm.provider")}</Label>
          <Select value={provider} onValueChange={setProvider}>
            <SelectTrigger><SelectValue placeholder={t("settings.llm.noProviderSelected")} /></SelectTrigger>
            <SelectContent>
              {LLM_PROVIDERS.map((p) => (<SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>))}
            </SelectContent>
          </Select>
        </div>

        {fields.includes("apiKey") && (
          <div>
            <Label className="mb-2 block">{t("settings.llm.apiKey")}</Label>
            <div className="flex gap-2">
              <Input type={revealed ? "text" : "password"} value={revealed ? apiKey : maskKey(apiKey)} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." className="flex-1" />
              <Button variant="outline" size="icon" onClick={() => setRevealed(!revealed)}>{revealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</Button>
              <Button variant="outline" size="icon" onClick={handleCopy}><Copy className="h-4 w-4" /></Button>
              <Button variant="outline" size="icon" onClick={handleDelete}><Trash2 className="h-4 w-4" /></Button>
            </div>
          </div>
        )}

        {fields.includes("model") && (
          <div>
            <Label className="mb-2 block">{t("settings.llm.model")}</Label>
            <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="gpt-4, claude-3-opus, gemini-pro..." />
          </div>
        )}

        {fields.includes("temperature") && (
          <div>
            <Label className="mb-2 block">{t("settings.llm.temperature")}</Label>
            <Input value={temperature} onChange={(e) => setTemperature(e.target.value)} type="text" inputMode="decimal" />
          </div>
        )}

        {fields.includes("maxTokens") && (
          <div>
            <Label className="mb-2 block">{t("settings.llm.maxTokens")}</Label>
            <Input value={maxTokens} onChange={(e) => setMaxTokens(e.target.value)} type="text" inputMode="numeric" />
          </div>
        )}

        {fields.includes("baseUrl") && (
          <div>
            <Label className="mb-2 block">{t("settings.llm.baseUrl")}</Label>
            <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://openrouter.ai/api/v1" />
          </div>
        )}

        {fields.includes("endpoint") && (
          <div>
            <Label className="mb-2 block">{t("settings.llm.endpoint")}</Label>
            <Input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="https://my-resource.openai.azure.com" />
          </div>
        )}

        {fields.includes("deployment") && (
          <div>
            <Label className="mb-2 block">{t("settings.llm.deployment")}</Label>
            <Input value={deployment} onChange={(e) => setDeployment(e.target.value)} placeholder="my-deployment-name" />
          </div>
        )}

        {fields.includes("apiVersion") && (
          <div>
            <Label className="mb-2 block">{t("settings.llm.apiVersion")}</Label>
            <Input value={apiVersion} onChange={(e) => setApiVersion(e.target.value)} placeholder="2024-02-15-preview" />
          </div>
        )}

        {fields.includes("host") && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="mb-2 block">{t("settings.llm.host")}</Label>
              <Input value={host} onChange={(e) => setHost(e.target.value)} placeholder="http://localhost" />
            </div>
            <div>
              <Label className="mb-2 block">{t("settings.llm.port")}</Label>
              <Input value={port} onChange={(e) => setPort(e.target.value)} placeholder="11434" />
            </div>
          </div>
        )}

        {provider && (
          <div className="flex items-center gap-2 pt-4">
            <Button variant="outline" onClick={handleTest} disabled={testStatus === "testing"}>
              {testStatus === "testing" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {t("settings.llm.testConnection")}
            </Button>
            {testStatus === "success" && <Badge className="gap-1"><CheckCircle className="h-3 w-3" /> {t("settings.llm.connected")}</Badge>}
            {testStatus === "failed" && <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" /> {t("settings.llm.connectionFailed")}</Badge>}
            <div className="flex-1" />
            <Button onClick={handleSave}>{t("settings.llm.save")}</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Report Export
// ---------------------------------------------------------------------------

function ReportExport({ data }: { data: any }) {
  const { t } = useI18n();
  const [open, setOpen] = React.useState(false);

  const handleExport = async (format: string) => {
    try {
      const res = await apiFetch("/api/report", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_id: data?.id || "latest", format, repository_url: data?.repository?.url || "" }) });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      // Use the filename from Content-Disposition if present, otherwise guess.
      const cd = res.headers.get("Content-Disposition") || "";
      const m = cd.match(/filename="([^"]+)"/);
      a.download = m ? m[1] : `report.${format === "md" ? "md" : format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${t("report.exported")} ${format.toUpperCase()}`);
    } catch (err: any) {
      toast.error(`${t("report.exportFailed")}: ${err.message}`);
    }
    setOpen(false);
  };

  return (
    <div className="relative">
      <Button variant="ghost" size="icon" onClick={() => setOpen(!open)}><Download className="h-4 w-4" /></Button>
      {open && (
        <div className="absolute right-0 top-full mt-1 z-50 rounded-lg border bg-background shadow-lg">
          <div className="p-1">
            <button onClick={() => handleExport("html")} className="flex w-full items-center gap-2 rounded px-3 py-1.5 text-sm hover:bg-muted">HTML</button>
            <button onClick={() => handleExport("md")} className="flex w-full items-center gap-2 rounded px-3 py-1.5 text-sm hover:bg-muted">Markdown</button>
            <button onClick={() => handleExport("json")} className="flex w-full items-center gap-2 rounded px-3 py-1.5 text-sm hover:bg-muted">JSON</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared Components
// ---------------------------------------------------------------------------

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = (confidence * 100).toFixed(0);
  const color = confidence >= 0.8 ? "bg-green-500" : confidence >= 0.6 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-1.5">
      <div className={`h-2 w-2 rounded-full ${color}`} />
      <span className="text-xs font-medium">{pct}%</span>
    </div>
  );
}

// Build a Markdown representation of a root cause for the "Copy as Markdown" button.
function buildRootCauseMarkdown(rc: any): string {
  const lines: string[] = [];
  lines.push(`## ${rc.title || "Root Cause"}`);
  lines.push("");
  lines.push(`| Field | Value |`);
  lines.push(`|---|---|`);
  lines.push(`| ID | \`${rc.id || "—"}\` |`);
  lines.push(`| Category | \`${rc.category || "—"}\` |`);
  lines.push(`| Severity | **${rc.severity || "—"}** |`);
  lines.push(`| Confidence | ${((rc.confidence || 0) * 100).toFixed(0)}% |`);
  lines.push(`| Evidence Count | ${rc.evidence_count || rc.evidence_links?.length || 0} |`);
  lines.push(`| Affected Files | ${rc.affected_files?.length || 0} |`);
  lines.push("");
  if (rc.description) { lines.push(`### Description`); lines.push(""); lines.push(rc.description); lines.push(""); }
  if (rc.technical_rationale) { lines.push(`### Technical Rationale`); lines.push(""); lines.push(rc.technical_rationale); lines.push(""); }
  if (rc.root_cause_origin) { lines.push(`### Likely Origin`); lines.push(""); lines.push(rc.root_cause_origin); lines.push(""); }
  if (rc.affected_files?.length) {
    lines.push(`### Affected Files`);
    lines.push("");
    rc.affected_files.forEach((f: string) => lines.push(`- \`${f}\``));
    lines.push("");
  }
  return lines.join("\n");
}

function ConfidenceTag({ confidence }: { confidence: string }) {
  const color = confidence === "high" ? "text-green-500" : confidence === "medium" ? "text-yellow-500" : "text-red-500";
  return <span className={`text-xs font-medium uppercase ${color}`}>{confidence}</span>;
}

// Keyboard <kbd> key cap visual
function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-6 min-w-6 items-center justify-center rounded border border-border bg-muted px-1.5 font-mono text-xs font-semibold text-foreground shadow-[0_1px_0_0_rgb(0_0_0_/_0.1)]">
      {children}
    </kbd>
  );
}

// Help dialog listing all keyboard shortcuts
function ShortcutsHelpDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const { t } = useI18n();
  const rows: { keys: React.ReactNode; label: string }[] = [
    { keys: <Kbd>?</Kbd>, label: t("shortcuts.openHelp") },
    { keys: <><Kbd>1</Kbd><span className="text-muted-foreground">…</span><Kbd>7</Kbd></>, label: t("shortcuts.switchTab") },
    { keys: <Kbd>/</Kbd>, label: t("shortcuts.focusSearch") },
    { keys: <Kbd>T</Kbd>, label: t("shortcuts.toggleTheme") },
    { keys: <Kbd>Esc</Kbd>, label: t("shortcuts.closeDialog") },
  ];
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Info className="h-5 w-5 text-primary" /> {t("shortcuts.title")}
          </DialogTitle>
          <DialogDescription className="sr-only">{t("shortcuts.title")}</DialogDescription>
        </DialogHeader>
        <div className="divide-y">
          {rows.map((r, i) => (
            <div key={i} className="flex items-center justify-between py-2.5">
              <span className="text-sm">{r.label}</span>
              <span className="flex items-center gap-1">{r.keys}</span>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Right-side drawer listing past analyses. Each entry shows repo, grade,
// timestamp, and counts; clicking reopens the full dashboard from localStorage
// without re-running the pipeline.
function HistorySheet({
  open, onOpenChange, entries, onReopen, onReanalyze,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  entries: HistoryEntry[];
  onReopen: (entry: HistoryEntry) => void;
  onReanalyze: (entry: HistoryEntry) => void;
}) {
  const { t } = useI18n();
  const [reanalyzingId, setReanalyzingId] = React.useState<string | null>(null);

  const fmtDate = (iso: string) => {
    try {
      const d = new Date(iso);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return t("history.justNow");
      if (diffMin < 60) return t("history.minutesAgo").replace("{m}", String(diffMin));
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return t("history.hoursAgo").replace("{h}", String(diffHr));
      return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch { return iso; }
  };

  const gradeColor = (overall: number) =>
    overall >= 80 ? "text-emerald-500" : overall >= 60 ? "text-amber-500" : "text-rose-500";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-md flex flex-col">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <History className="h-5 w-5 text-primary" /> {t("history.title")}
          </SheetTitle>
          <SheetDescription>
            {entries.length > 0
              ? t("history.count").replace("{count}", String(entries.length))
              : t("history.empty")}
          </SheetDescription>
        </SheetHeader>

        {entries.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center py-16 text-center">
            <div className="mb-3 text-muted-foreground/30"><History className="h-12 w-12" /></div>
            <p className="text-sm text-muted-foreground">{t("history.empty")}</p>
          </div>
        ) : (
          <ScrollArea className="flex-1 -mx-6 px-6">
            <div className="space-y-2 pb-4">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className="group rounded-lg border p-3 transition-colors hover:bg-muted/40"
                >
                  <div className="flex items-start gap-3">
                    {/* Grade circle */}
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border">
                      <span className={`text-sm font-bold ${gradeColor(entry.overall)}`}>{entry.grade}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate text-sm font-medium">{entry.owner}/{entry.name}</span>
                        {entry.isDemo && (
                          <Badge variant="outline" className="shrink-0 text-[10px] h-4 px-1">{t("history.demoBadge")}</Badge>
                        )}
                      </div>
                      <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        <span>{fmtDate(entry.analyzedAt)}</span>
                      </div>
                      <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1"><Bug className="h-3 w-3" />{entry.rootCauseCount}</span>
                        <span className="flex items-center gap-1"><Beaker className="h-3 w-3" />{entry.evidenceCount}</span>
                        <span className="flex items-center gap-1"><Gauge className="h-3 w-3" />{entry.overall.toFixed(0)}/100</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
                    <Button size="sm" variant="default" className="h-7 text-xs" onClick={() => onReopen(entry)}>
                      <ArrowLeft className="mr-1 h-3 w-3 rotate-180" /> {t("history.reopen")}
                    </Button>
                    <Button
                      size="sm" variant="outline" className="h-7 text-xs"
                      disabled={reanalyzingId === entry.id}
                      onClick={() => {
                        setReanalyzingId(entry.id);
                        // Defer so the button's loading state shows before the view switches.
                        setTimeout(() => onReanalyze(entry), 50);
                      }}
                    >
                      {reanalyzingId === entry.id
                        ? <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        : <RotateCcw className="mr-1 h-3 w-3" />}
                      {reanalyzingId === entry.id ? t("history.reanalyzing") : t("history.reanalyze")}
                    </Button>
                    <Button
                      size="sm" variant="ghost" className="h-7 text-xs text-muted-foreground hover:text-destructive"
                      onClick={() => { removeHistoryEntry(entry.id); toast.success(t("common.delete")); }}
                    >
                      <Trash2 className="mr-1 h-3 w-3" /> {t("history.remove")}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}

        {entries.length > 0 && (
          <SheetFooter className="flex-row flex-wrap gap-2">
            <Button
              variant="outline" size="sm"
              onClick={() => {
                const blob = new Blob([JSON.stringify(entries.map(({ result, ...meta }) => meta), null, 2)], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `analysis-history-${new Date().toISOString().slice(0, 10)}.json`;
                a.click();
                URL.revokeObjectURL(url);
                toast.success(t("history.exportedJson"));
              }}
            >
              <Download className="mr-1.5 h-3.5 w-3.5" /> {t("history.exportJson")}
            </Button>
            <Button
              variant="outline" size="sm"
              onClick={() => {
                // Full backup: includes the complete result payloads (larger file).
                const blob = new Blob([JSON.stringify(entries, null, 2)], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `analysis-full-backup-${new Date().toISOString().slice(0, 10)}.json`;
                a.click();
                URL.revokeObjectURL(url);
                toast.success(t("history.exportedFull"));
              }}
            >
              <Database className="mr-1.5 h-3.5 w-3.5" /> {t("history.fullBackup")}
            </Button>
            <Button
              variant="outline" size="sm" className="text-muted-foreground hover:text-destructive"
              onClick={() => { clearHistory(); toast.success(t("history.clearAll")); }}
            >
              <Trash2 className="mr-1.5 h-3.5 w-3.5" /> {t("history.clearAll")}
            </Button>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  );
}

// Comparison dialog: diff the current analysis against a baseline selected
// from history. Shows health-score deltas + root-cause added/removed/changed.
function CompareDialog({
  open, onOpenChange, current, historyEntries,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  current: any;
  historyEntries: HistoryEntry[];
}) {
  const { t } = useI18n();
  const [baselineId, setBaselineId] = React.useState<string>("");

  const baseline = React.useMemo(
    () => historyEntries.find((e) => e.id === baselineId),
    [historyEntries, baselineId]
  );

  // Health score dimensions to compare
  const scoreDims = React.useMemo(() => {
    if (!current || !baseline) return [];
    const ch = current?.ai_review?.health_score || {};
    const bh = baseline.result?.ai_review?.health_score || {};
    return [
      { key: "overall",        label: t("dashboard.health"),  cur: ch.overall,        base: bh.overall },
      { key: "security",       label: t("health.security"),   cur: ch.security,       base: bh.security },
      { key: "architecture",   label: t("health.architecture"), cur: ch.architecture, base: bh.architecture },
      { key: "code_quality",   label: t("health.quality"),    cur: ch.code_quality,   base: bh.code_quality },
      { key: "testing",        label: t("health.testing"),    cur: ch.testing,        base: bh.testing },
      { key: "documentation",  label: t("health.docs"),       cur: ch.documentation,  base: bh.documentation },
    ].filter((d) => d.cur != null || d.base != null);
  }, [current, baseline, t]);

  // Root cause diff: match by category (since titles vary)
  const rcDiff = React.useMemo(() => {
    if (!current || !baseline || !baseline.result) return null;
    try {
      const curRcs: any[] = (current?.root_causes?.root_causes as any[]) || [];
      const baseRcs: any[] = (baseline.result?.root_causes?.root_causes as any[]) || [];
      if (!Array.isArray(curRcs) || !Array.isArray(baseRcs)) return null;
      const curByCat = new Map<string, any>();
      curRcs.forEach((r: any) => { if (r && r.category) curByCat.set(r.category, r); });
      const baseByCat = new Map<string, any>();
      baseRcs.forEach((r: any) => { if (r && r.category) baseByCat.set(r.category, r); });
      const allCats: string[] = [];
      curByCat.forEach((_, k) => allCats.push(k));
      baseByCat.forEach((_, k) => { if (!allCats.includes(k)) allCats.push(k); });
      const rows: { category: string; cur?: any; base?: any; status: "new" | "gone" | "changed" | "unchanged" }[] = [];
      allCats.forEach((cat) => {
        const c = curByCat.get(cat);
        const b = baseByCat.get(cat);
        if (c && !b) rows.push({ category: cat, cur: c, status: "new" });
        else if (!c && b) rows.push({ category: cat, base: b, status: "gone" });
        else if (c && b) {
          const confDelta = Math.abs((c.confidence || 0) - (b.confidence || 0));
          rows.push({ category: cat, cur: c, base: b, status: confDelta > 0.01 ? "changed" : "unchanged" });
        }
      });
      return rows;
    } catch (e) {
      console.error("rcDiff error", e);
      return null;
    }
  }, [current, baseline]);

  // Count-based diffs: evidence, roadmap steps, quick wins.
  const countDiffs = React.useMemo(() => {
    if (!current || !baseline || !baseline.result) return null;
    try {
      const curEv = current?.evidence?.statistics?.total_evidence || current?.evidence?.evidence?.length || 0;
      const baseEv = baseline.result?.evidence?.statistics?.total_evidence || baseline.result?.evidence?.evidence?.length || 0;
      const curSteps = current?.engineering_plan?.steps?.length || 0;
      const baseSteps = baseline.result?.engineering_plan?.steps?.length || 0;
      const curQw = current?.engineering_plan?.quick_wins?.length || 0;
      const baseQw = baseline.result?.engineering_plan?.quick_wins?.length || 0;
      return [
        { label: t("compare.evidence"), cur: curEv, base: baseEv },
        { label: t("compare.roadmap"), cur: curSteps, base: baseSteps },
        { label: t("compare.quickWins"), cur: curQw, base: baseQw },
      ];
    } catch {
      return null;
    }
  }, [current, baseline, t]);

  const fmtNum = (n: any) => (n == null ? "—" : Number(n).toFixed(1));
  const delta = (cur: any, base: any) => {
    if (cur == null || base == null) return null;
    return Number(cur) - Number(base);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-primary" /> {t("compare.title")}
          </DialogTitle>
          <DialogDescription>{t("compare.selectBaseline")}</DialogDescription>
        </DialogHeader>

        {/* Baseline selector */}
        <div className="flex items-center gap-2">
          <Select value={baselineId} onValueChange={setBaselineId}>
            <SelectTrigger className="flex-1"><SelectValue placeholder={t("compare.selectBaseline")} /></SelectTrigger>
            <SelectContent>
              {historyEntries.map((e) => (
                <SelectItem key={e.id} value={e.id}>
                  {e.owner}/{e.name} · {e.grade} · {new Date(e.analyzedAt).toLocaleDateString()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {!baseline ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            {t("compare.noBaseline")}
          </div>
        ) : (
          <div className="space-y-5">
            {/* Header row: current vs baseline labels */}
            <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-xs font-medium text-muted-foreground">
              <span className="text-left">{t("compare.baseline")}: {baseline.owner}/{baseline.name}</span>
              <span className="text-center">{t("compare.delta")}</span>
              <span className="text-right">{t("compare.current")}: {current?.repository?.owner}/{current?.repository?.name}</span>
            </div>

            {/* Health scores table */}
            {scoreDims.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold">{t("compare.healthScores")}</h4>
                <div className="space-y-1">
                  {scoreDims.map((d) => {
                    const dl = delta(d.cur, d.base);
                    const status = dl == null ? "same" : dl > 0.5 ? "better" : dl < -0.5 ? "worse" : "same";
                    const color = status === "better" ? "text-emerald-500" : status === "worse" ? "text-rose-500" : "text-muted-foreground";
                    const sign = dl != null && dl > 0 ? "+" : "";
                    return (
                      <div key={d.key} className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded border px-3 py-1.5 text-sm">
                        <span className="text-left tabular-nums">{fmtNum(d.base)}</span>
                        <span className={`text-center font-mono text-xs font-semibold tabular-nums ${color}`}>
                          {dl == null ? "—" : `${sign}${dl.toFixed(1)}`}
                        </span>
                        <span className="text-right">
                          <span className="tabular-nums font-medium">{fmtNum(d.cur)}</span>
                          <span className="ml-2 text-xs text-muted-foreground">{d.label}</span>
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Count diffs: evidence, roadmap steps, quick wins */}
            {countDiffs && (
              <div>
                <h4 className="mb-2 text-sm font-semibold">{t("stats.evidenceItems")} & {t("dashboard.roadmap")}</h4>
                <div className="grid grid-cols-3 gap-2">
                  {countDiffs.map((d, i) => {
                    const dl = d.cur - d.base;
                    const status = dl > 0 ? "better" : dl < 0 ? "worse" : "same";
                    const color = status === "better" ? "text-emerald-500" : status === "worse" ? "text-rose-500" : "text-muted-foreground";
                    const sign = dl > 0 ? "+" : "";
                    return (
                      <div key={i} className="rounded border p-2 text-center">
                        <div className="text-xs text-muted-foreground">{d.label}</div>
                        <div className="mt-1 text-lg font-bold tabular-nums">{d.cur}</div>
                        <div className={`text-xs font-mono font-semibold tabular-nums ${color}`}>
                          {dl === 0 ? "±0" : `${sign}${dl}`}
                        </div>
                        <div className="text-xs text-muted-foreground/70 tabular-nums">was {d.base}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Root causes diff */}
            {rcDiff && rcDiff.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold">{t("compare.rootCauses")}</h4>
                <div className="space-y-1">
                  {rcDiff.map((r) => {
                    const badge = r.status === "new" ? { text: t("compare.new"), cls: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400" }
                      : r.status === "gone" ? { text: t("compare.gone"), cls: "bg-rose-500/15 text-rose-600 dark:text-rose-400" }
                      : r.status === "changed" ? { text: t("compare.improved"), cls: "bg-amber-500/15 text-amber-600 dark:text-amber-400" }
                      : { text: t("compare.unchanged"), cls: "bg-muted text-muted-foreground" };
                    return (
                      <div key={r.category} className="flex items-center justify-between rounded border px-3 py-1.5 text-sm">
                        <span className="font-mono text-xs">{r.category}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground tabular-nums">
                            {r.base ? `${(r.base.confidence * 100).toFixed(0)}%` : "—"} → {r.cur ? `${(r.cur.confidence * 100).toFixed(0)}%` : "—"}
                          </span>
                          <Badge variant="outline" className={`text-xs ${badge.cls} border-0`}>{badge.text}</Badge>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// Onboarding wizard — shown on first launch.
// Steps: Language → Theme → LLM Provider → API Key → Connection Test → Ready.
// Uses existing useI18n, useTheme, LLM_PROVIDERS, writeLLMConfig.
function OnboardingWizard({
  open, onOpenChange, onComplete,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onComplete: () => void;
}) {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();
  const [step, setStep] = React.useState(0);
  // Local state for LLM config (mirrors LLMSettingsSection but simplified).
  const [provider, setProvider] = React.useState("");
  const [apiKey, setApiKey] = React.useState("");
  const [model, setModel] = React.useState("");
  const [testStatus, setTestStatus] = React.useState<"idle" | "testing" | "success" | "failed">("idle");

  const steps = [
    t("onboarding.stepLanguage"),
    t("onboarding.stepTheme"),
    t("onboarding.stepProvider"),
    t("onboarding.stepApiKey"),
    t("onboarding.stepTest"),
    t("onboarding.stepAnalysis"),
  ];
  const total = steps.length;

  const handleSkip = () => {
    onOpenChange(false);
  };

  const handleNext = () => {
    if (step < total - 1) {
      setStep(step + 1);
    } else {
      onComplete();
    }
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  // Save LLM config when moving past the API key step.
  const handleSaveAndTest = async () => {
    if (provider && (provider === "ollama" || apiKey)) {
      try {
        writeLLMConfig({ provider, apiKey, model });
      } catch { /* ignore */ }
    }
    // Simulate connection test.
    setTestStatus("testing");
    await sleep(1500);
    const ok = provider === "ollama" || !!apiKey.trim();
    setTestStatus(ok ? "success" : "failed");
  };

  const canSkipProvider = step === 2 || step === 3 || step === 4;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            {step === 0 ? t("onboarding.title") : steps[step]}
          </DialogTitle>
          <DialogDescription>
            {step === 0 ? t("onboarding.subtitle") : t("onboarding.step").replace("{current}", String(step + 1)).replace("{total}", String(total))}
          </DialogDescription>
        </DialogHeader>

        {/* Progress bar */}
        <div className="mb-4 flex gap-1.5">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? "bg-primary" : "bg-muted"}`}
            />
          ))}
        </div>

        {/* Step content */}
        <div className="min-h-[180px]">
          {step === 0 && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">{t("onboarding.stepLanguage")}</p>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setLang("en")}
                  className={`rounded-lg border p-4 text-center transition-all hover:border-primary/40 hover:shadow-sm ${lang === "en" ? "border-primary ring-1 ring-primary" : ""}`}
                >
                  <Globe className="mx-auto mb-2 h-6 w-6 text-primary" />
                  <span className="text-sm font-medium">English</span>
                </button>
                <button
                  onClick={() => setLang("tr")}
                  className={`rounded-lg border p-4 text-center transition-all hover:border-primary/40 hover:shadow-sm ${lang === "tr" ? "border-primary ring-1 ring-primary" : ""}`}
                >
                  <Globe className="mx-auto mb-2 h-6 w-6 text-primary" />
                  <span className="text-sm font-medium">Türkçe</span>
                </button>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">{t("onboarding.stepTheme")}</p>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setTheme("dark")}
                  className={`rounded-lg border p-4 text-center transition-all hover:border-primary/40 hover:shadow-sm ${theme === "dark" ? "border-primary ring-1 ring-primary" : ""}`}
                >
                  <Moon className="mx-auto mb-2 h-6 w-6 text-primary" />
                  <span className="text-sm font-medium">{t("settings.appearance.darkMode")}</span>
                </button>
                <button
                  onClick={() => setTheme("light")}
                  className={`rounded-lg border p-4 text-center transition-all hover:border-primary/40 hover:shadow-sm ${theme === "light" ? "border-primary ring-1 ring-primary" : ""}`}
                >
                  <Sun className="mx-auto mb-2 h-6 w-6 text-primary" />
                  <span className="text-sm font-medium">{t("settings.appearance.lightMode")}</span>
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">{t("onboarding.stepProvider")}</p>
              <div className="grid grid-cols-2 gap-2">
                {LLM_PROVIDERS.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => { setProvider(p.value); setModel(""); setApiKey(""); }}
                    className={`rounded-lg border p-3 text-left transition-all hover:border-primary/40 hover:shadow-sm ${provider === p.value ? "border-primary ring-1 ring-primary" : ""}`}
                  >
                    <div className="flex items-center gap-2">
                      <Key className="h-4 w-4 text-primary" />
                      <span className="text-sm font-medium">{p.label}</span>
                    </div>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {p.fields.includes("apiKey") ? "API Key" : "Local"}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">{t("onboarding.stepApiKey")}</p>
              {provider === "ollama" ? (
                <div className="space-y-3">
                  <div>
                    <Label className="mb-1.5 block text-xs text-muted-foreground">{t("settings.llm.host")}</Label>
                    <Input value={model ? "" : "http://localhost"} disabled className="h-9 text-sm" />
                    <p className="mt-1 text-xs text-muted-foreground">{t("settings.llm.host")}: http://localhost:{model ? "" : "11434"}</p>
                  </div>
                  <div>
                    <Label className="mb-1.5 block text-xs text-muted-foreground">{t("settings.llm.model")}</Label>
                    <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="llama3, mistral..." className="h-9 text-sm" />
                  </div>
                </div>
              ) : provider ? (
                <div className="space-y-3">
                  <div>
                    <Label className="mb-1.5 block text-xs text-muted-foreground">{t("settings.llm.apiKey")}</Label>
                    <Input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="sk-..." className="h-9 text-sm" />
                  </div>
                  <div>
                    <Label className="mb-1.5 block text-xs text-muted-foreground">{t("settings.llm.model")}</Label>
                    <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="gpt-4o, claude-3-opus..." className="h-9 text-sm" />
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">{t("onboarding.skipProvider")}</p>
              )}
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">{t("onboarding.stepTest")}</p>
              {provider ? (
                <>
                  <Button onClick={handleSaveAndTest} disabled={testStatus === "testing"} className="w-full">
                    {testStatus === "testing" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Key className="mr-2 h-4 w-4" />}
                    {testStatus === "testing" ? t("platform.refreshing") : t("settings.llm.testConnection")}
                  </Button>
                  {testStatus === "success" && (
                    <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-600 dark:text-emerald-400">
                      <CheckCircle className="h-4 w-4 shrink-0" />
                      <span>{t("onboarding.testSuccess")}</span>
                    </div>
                  )}
                  {testStatus === "failed" && (
                    <div className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-600 dark:text-amber-400">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      <span>{t("onboarding.testFailed")}</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex items-center gap-2 rounded-lg border bg-muted/30 p-3 text-sm text-muted-foreground">
                  <Info className="h-4 w-4 shrink-0" />
                  <span>{t("onboarding.skipProvider")}</span>
                </div>
              )}
            </div>
          )}

          {step === 5 && (
            <div className="flex flex-col items-center gap-4 py-4 text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/60 shadow-lg shadow-primary/20">
                <Brain className="h-8 w-8 text-primary-foreground" />
              </div>
              <div>
                <h3 className="text-lg font-semibold">{t("onboarding.stepAnalysis")}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{t("onboarding.stepAnalysisDesc")}</p>
              </div>
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex gap-2">
            {step > 0 && (
              <Button variant="ghost" size="sm" onClick={handleBack}>
                <ArrowLeft className="mr-1 h-4 w-4" /> {t("onboarding.back")}
              </Button>
            )}
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={handleSkip}>
              {t("onboarding.skip")}
            </Button>
            {step === 4 && testStatus !== "success" && provider && (
              <Button variant="ghost" size="sm" onClick={handleNext}>
                {t("onboarding.testSkip")}
              </Button>
            )}
            <Button size="sm" onClick={handleNext}>
              {step === total - 1 ? t("onboarding.finish") : t("onboarding.next")}
              {step < total - 1 && <ChevronRight className="ml-1 h-4 w-4" />}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function EmptyState({ icon, title, description }: { icon: React.ReactNode; title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 text-muted-foreground/40">{icon}</div>
      <h3 className="text-lg font-semibold">{title}</h3>
      {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function sleep(ms: number) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
}
function severityVariant(severity: string): any {
  switch (severity?.toLowerCase()) { case "critical": return "destructive"; case "high": return "destructive"; case "medium": return "secondary"; case "low": return "outline"; default: return "outline"; }
}
function riskVariant(risk: string): any {
  switch (risk?.toLowerCase()) { case "critical": return "destructive"; case "high": return "destructive"; case "medium": return "secondary"; case "low": return "outline"; default: return "outline"; }
}

// Humanize snake_case / kebab-case into Title Case for display.
// e.g. "cyclomatic_complexity" → "Cyclomatic Complexity", "god-class" → "God Class".
// Turkish translations for common technical category names.
// Falls back to Title Case for unknown keys.
const TR_CATEGORY_MAP: Record<string, string> = {
  // Root cause categories
  god_class: "Tanrı Sınıf",
  circular_dependency: "Döngüsel Bağımlılık",
  tight_coupling: "Sıkı Bağlılık",
  shotgun_surgery: "Saçma Değişiklik",
  // Evidence categories
  cyclomatic_complexity: "Döngüsel Karmaşıklık",
  long_method: "Uzun Metod",
  large_file: "Büyük Dosya",
  circular_import: "Döngüsel Import",
  high_coupling: "Yüksek Bağlılık",
  unused_import: "Kullanılmayan Import",
  hardcoded_password: "Sabit Kodlanmış Şifre",
  low_coverage: "Düşük Test Kapsamı",
  dead_code: "Ölü Kod",
  // Finding types
  complexity: "Karmaşıklık",
  code_quality: "Kod Kalitesi",
  metric: "Metrik",
  import: "Import",
  architecture: "Mimari",
  security: "Güvenlik",
  test: "Test",
  // Node types
  repository: "Depo",
  file: "Dosya",
  class: "Sınıf",
  function: "Fonksiyon",
  method: "Metod",
  module: "Modül",
  dependency: "Bağımlılık",
  security_finding: "Güvenlik Bulgusu",
  architecture_finding: "Mimari Bulgu",
  metric_finding: "Metrik Bulgusu",
  evidence: "Kanıt",
  // Edge types
  belongs_to: "Ait",
  affects: "Etkiler",
  causes: "Neden Olur",
};

function humanize(s: string): string {
  if (!s) return "—";
  const lower = s.toLowerCase();
  if (TR_CATEGORY_MAP[lower]) return TR_CATEGORY_MAP[lower];
  return s
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Demo Data — delegated to the shared module so the mock API routes and the
// client-side fallback use the exact same generator.
// ---------------------------------------------------------------------------

function getDemoData(repoUrl: string): any {
  // Read LLM config from localStorage so the fallback also respects the
  // user's saved API key (generates offline: false review when configured).
  let useLLM = false;
  let llmProvider: string | undefined;
  let llmModel: string | undefined;
  try {
    const raw = localStorage.getItem("ra-llm-config");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed.provider && (parsed.provider === "ollama" || parsed.apiKey)) {
        useLLM = true;
        llmProvider = parsed.provider;
        llmModel = parsed.model;
      }
    }
  } catch { /* ignore */ }
  return generateDemoData(repoUrl, { useLLM, llmProvider, llmModel });
}
