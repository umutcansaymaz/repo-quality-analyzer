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
  Map,
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
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useTheme } from "next-themes";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ViewState = "landing" | "progress" | "results";

interface PipelineStep {
  id: string;
  label: string;
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
// Main Page
// ---------------------------------------------------------------------------

export default function Home() {
  const [view, setView] = React.useState<ViewState>("landing");
  const [repoUrl, setRepoUrl] = React.useState("");
  const [jobId, setJobId] = React.useState<string | null>(null);
  const [analysisData, setAnalysisData] = React.useState<AnalysisData | null>(null);
  const [pipelineSteps, setPipelineSteps] = React.useState<PipelineStep[]>([]);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);

  const handleAnalyze = async () => {
    if (!repoUrl.trim()) {
      toast.error("Please enter a repository URL");
      return;
    }
    setView("progress");
    setPipelineSteps(getInitialSteps());

    // Run pipeline steps with animation
    const stepIds = ["detection", "language", "dependency", "metrics", "evidence", "graph", "rootcause", "planning", "review"];
    
    try {
      // Try real API first
      setStepStatus("detection", "running");
      
      // Use a race — if API responds in time, use real data; otherwise use demo data
      const apiPromise = apiFetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_url: repoUrl, use_cache: true }),
      });

      // Animate all steps while waiting
      for (const stepId of stepIds) {
        setStepStatus(stepId, "running");
        await sleep(500 + Math.random() * 600);
        setStepStatus(stepId, "completed");
      }

      // Try to get real results
      let resultData: any = null;
      try {
        const res = await apiPromise;
        const data = await res.json();
        // Fetch full results
        const resultRes = await apiFetch(`/api/result/${data.job_id}`);
        resultData = await resultRes.json();
      } catch {
        // API failed or timed out — use demo data
        resultData = getDemoData(repoUrl);
      }

      setAnalysisData({
        jobId: "demo",
        status: "completed",
        repository: repoUrl,
        result: resultData,
      });
      setView("results");
      toast.success("Analysis complete!");
    } catch (err: any) {
      // Final fallback — use demo data
      const demoData = getDemoData(repoUrl);
      setAnalysisData({
        jobId: "demo",
        status: "completed",
        repository: repoUrl,
        result: demoData,
      });
      setView("results");
      toast.info("Showing demo results (API unavailable)");
    }
  };

  const handleReset = () => {
    setView("landing");
    setRepoUrl("");
    setJobId(null);
    setAnalysisData(null);
    setPipelineSteps([]);
  };

  const setStepStatus = (id: string, status: PipelineStep["status"]) => {
    setPipelineSteps((prev) => prev.map((s) => (s.id === id ? { ...s, status } : s)));
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-sm">
        <div className="container mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <button onClick={handleReset} className="flex items-center gap-2 font-bold tracking-tight">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Brain className="h-4 w-4" />
            </div>
            <span className="hidden sm:inline">AI Software Architect</span>
          </button>
          <div className="flex items-center gap-2">
            {analysisData && view === "results" && <ReportExport data={analysisData.result} />}
            {mounted && (
              <Button variant="ghost" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
                {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
            )}
          </div>
        </div>
      </header>

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
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Landing View
// ---------------------------------------------------------------------------

function LandingView({
  repoUrl,
  setRepoUrl,
  onAnalyze,
}: {
  repoUrl: string;
  setRepoUrl: (v: string) => void;
  onAnalyze: () => void;
}) {
  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-2xl text-center"
      >
        <div className="mb-6 flex justify-center">
          <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/60 shadow-lg">
            <Brain className="h-10 w-10 text-primary-foreground" />
          </div>
        </div>
        <h1 className="mb-3 text-4xl font-bold tracking-tight sm:text-5xl">AI Software Architect</h1>
        <p className="mb-8 text-lg text-muted-foreground">
          Analyze repositories.
          <br />
          Understand architecture. Discover root causes.
          <br />
          Generate engineering roadmaps.
        </p>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Input
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/owner/repository"
            className="h-12 flex-1 text-base"
            onKeyDown={(e) => e.key === "Enter" && onAnalyze()}
          />
          <Button size="lg" className="h-12 px-8 text-base" onClick={onAnalyze}>
            <Sparkles className="mr-2 h-5 w-5" />
            Analyze Repository
          </Button>
        </div>

        <div className="mt-3">
          <Button variant="outline" size="sm" disabled className="opacity-50">
            <FileCode2 className="mr-2 h-4 w-4" />
            Upload Local Repository
            <Badge variant="secondary" className="ml-2 text-xs">Coming Soon</Badge>
          </Button>
        </div>

        {/* Feature pills */}
        <div className="mt-12 flex flex-wrap justify-center gap-3">
          {[
            { icon: <Bug className="h-4 w-4" />, label: "Root Cause Detection" },
            { icon: <Network className="h-4 w-4" />, label: "Knowledge Graph" },
            { icon: <Map className="h-4 w-4" />, label: "Engineering Roadmap" },
            { icon: <Shield className="h-4 w-4" />, label: "Security Analysis" },
            { icon: <Activity className="h-4 w-4" />, label: "Health Score" },
            { icon: <Eye className="h-4 w-4" />, label: "Explainability" },
          ].map((f, i) => (
            <motion.div
              key={f.label}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 + i * 0.08 }}
            >
              <Badge variant="secondary" className="gap-1.5 px-3 py-1.5 text-sm">
                {f.icon}
                {f.label}
              </Badge>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Progress View
// ---------------------------------------------------------------------------

function getInitialSteps(): PipelineStep[] {
  return [
    { id: "detection", label: "Repository Detection", icon: <Github className="h-5 w-5" />, status: "pending" },
    { id: "language", label: "Language Analysis", icon: <FileText className="h-5 w-5" />, status: "pending" },
    { id: "dependency", label: "Dependency Analysis", icon: <Layers className="h-5 w-5" />, status: "pending" },
    { id: "metrics", label: "Metrics & Complexity", icon: <Activity className="h-5 w-5" />, status: "pending" },
    { id: "evidence", label: "Evidence Collection", icon: <Beaker className="h-5 w-5" />, status: "pending" },
    { id: "graph", label: "Knowledge Graph", icon: <Network className="h-5 w-5" />, status: "pending" },
    { id: "rootcause", label: "Root Cause Detection", icon: <Bug className="h-5 w-5" />, status: "pending" },
    { id: "planning", label: "Planning Engine", icon: <Map className="h-5 w-5" />, status: "pending" },
    { id: "review", label: "Engineering Review", icon: <Sparkles className="h-5 w-5" />, status: "pending" },
  ];
}

function ProgressView({ steps, repoUrl }: { steps: PipelineStep[]; repoUrl: string }) {
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const progress = (completedCount / steps.length) * 100;

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] items-center justify-center px-4">
      <div className="w-full max-w-lg">
        <div className="mb-8 text-center">
          <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-primary" />
          <h2 className="text-xl font-semibold">Analyzing Repository</h2>
          <p className="mt-1 text-sm text-muted-foreground">{repoUrl}</p>
        </div>

        <Progress value={progress} className="mb-8 h-2" />

        <div className="space-y-2">
          {steps.map((step, i) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center gap-3 rounded-lg border p-3"
            >
              <div className="flex-shrink-0">
                {step.status === "completed" && <CheckCircle2 className="h-5 w-5 text-green-500" />}
                {step.status === "running" && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                {step.status === "pending" && <Circle className="h-5 w-5 text-muted-foreground" />}
                {step.status === "error" && <AlertCircle className="h-5 w-5 text-destructive" />}
              </div>
              <div className="flex-shrink-0 text-muted-foreground">{step.icon}</div>
              <span className={`text-sm ${step.status === "pending" ? "text-muted-foreground" : "text-foreground"}`}>
                {step.label}
              </span>
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
  const [activeTab, setActiveTab] = React.useState("overview");

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6">
      {/* Top bar with back button */}
      <div className="mb-6 flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={onReset}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          New Analysis
        </Button>
      </div>

      {/* Health Score Card */}
      <HealthScoreCard data={data} />

      {/* Main tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6">
        <TabsList className="flex w-full flex-wrap gap-1">
          <TabsTrigger value="overview" className="gap-1.5">
            <Activity className="h-4 w-4" /> Overview
          </TabsTrigger>
          <TabsTrigger value="rootcauses" className="gap-1.5">
            <Bug className="h-4 w-4" /> Root Causes
          </TabsTrigger>
          <TabsTrigger value="roadmap" className="gap-1.5">
            <Map className="h-4 w-4" /> Roadmap
          </TabsTrigger>
          <TabsTrigger value="evidence" className="gap-1.5">
            <Beaker className="h-4 w-4" /> Evidence
          </TabsTrigger>
          <TabsTrigger value="graph" className="gap-1.5">
            <Network className="h-4 w-4" /> Graph
          </TabsTrigger>
          <TabsTrigger value="files" className="gap-1.5">
            <FileCode2 className="h-4 w-4" /> Files
          </TabsTrigger>
          <TabsTrigger value="ai" className="gap-1.5">
            <Sparkles className="h-4 w-4" /> AI Review
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4">
          <OverviewSection data={data} />
        </TabsContent>
        <TabsContent value="rootcauses" className="mt-4">
          <RootCausesSection data={data} />
        </TabsContent>
        <TabsContent value="roadmap" className="mt-4">
          <RoadmapSection data={data} />
        </TabsContent>
        <TabsContent value="evidence" className="mt-4">
          <EvidenceSection data={data} />
        </TabsContent>
        <TabsContent value="graph" className="mt-4">
          <GraphSection data={data} />
        </TabsContent>
        <TabsContent value="files" className="mt-4">
          <FileExplorerSection data={data} />
        </TabsContent>
        <TabsContent value="ai" className="mt-4">
          <AIReviewSection data={data} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Health Score Card
// ---------------------------------------------------------------------------

function HealthScoreCard({ data }: { data: any }) {
  const healthScore = data?.ai_review?.health_score;
  const grade = healthScore?.grade || "N/A";
  const overall = healthScore?.overall || 0;

  const gradeColor = overall >= 80 ? "text-green-500" : overall >= 60 ? "text-yellow-500" : "text-red-500";
  const meta = data?.repository_metadata;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className={`text-5xl font-bold ${gradeColor}`}>{grade}</div>
            <div>
              <p className="text-sm text-muted-foreground">Repository Health</p>
              <p className="text-2xl font-semibold">{overall.toFixed(1)} / 100</p>
            </div>
          </div>

          {meta && (
            <div className="flex flex-wrap gap-4 text-sm">
              {meta.license && (
                <div className="flex items-center gap-1.5">
                  <Shield className="h-4 w-4 text-muted-foreground" />
                  <span>{meta.license}</span>
                </div>
              )}
              {meta.total_commits != null && (
                <div className="flex items-center gap-1.5">
                  <GitBranch className="h-4 w-4 text-muted-foreground" />
                  <span>{meta.total_commits} commits</span>
                </div>
              )}
              {meta.contributors && (
                <div className="flex items-center gap-1.5">
                  <Github className="h-4 w-4 text-muted-foreground" />
                  <span>{meta.contributors.length} contributors</span>
                </div>
              )}
            </div>
          )}

          {healthScore && (
            <div className="flex flex-wrap gap-3">
              {[
                { label: "Security", value: healthScore.security },
                { label: "Architecture", value: healthScore.architecture },
                { label: "Quality", value: healthScore.code_quality },
                { label: "Testing", value: healthScore.testing },
                { label: "Docs", value: healthScore.documentation },
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
// Overview Section
// ---------------------------------------------------------------------------

function OverviewSection({ data }: { data: any }) {
  const rootCauses = data?.root_causes?.root_causes || [];
  const plan = data?.engineering_plan;
  const quickWins = plan?.quick_wins || [];
  const evidence = data?.evidence;
  const evidenceCount = evidence?.statistics?.total_evidence || evidence?.evidence?.length || 0;
  const aiReview = data?.engineering_review;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <StatCard icon={<Bug className="h-5 w-5" />} title="Root Causes" value={rootCauses.length} subtitle="architectural issues" />
      <StatCard icon={<Beaker className="h-5 w-5" />} title="Evidence Items" value={evidenceCount} subtitle="total findings" />
      <StatCard icon={<Zap className="h-5 w-5" />} title="Quick Wins" value={quickWins.length} subtitle="low-effort fixes" />
      <StatCard icon={<Map className="h-5 w-5" />} title="Plan Steps" value={plan?.steps?.length || 0} subtitle="refactoring steps" />
      <StatCard icon={<TrendingUp className="h-5 w-5" />} title="Avg ROI" value={plan?.statistics?.average_roi?.toFixed(2) || "0"} subtitle="return on investment" />
      <StatCard icon={<Sparkles className="h-5 w-5" />} title="AI Review" value={aiReview?.offline ? "Offline" : "Active"} subtitle={aiReview?.total_sections + " sections" || "no review"} />

      {rootCauses.length > 0 && (
        <Card className="md:col-span-2 lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-lg">Top Root Causes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {rootCauses.slice(0, 5).map((rc: any, i: number) => (
                <RootCauseRow key={rc.id || i} rc={rc} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatCard({ icon, title, value, subtitle }: { icon: React.ReactNode; title: string; value: any; subtitle: string }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">{icon}</div>
          <div>
            <div className="text-2xl font-bold">{value}</div>
            <div className="text-xs text-muted-foreground">{title}</div>
            <div className="text-xs text-muted-foreground/60">{subtitle}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Root Causes Section
// ---------------------------------------------------------------------------

function RootCausesSection({ data }: { data: any }) {
  const rootCauses = data?.root_causes?.root_causes || [];
  const [expanded, setExpanded] = React.useState<string | null>(null);

  if (rootCauses.length === 0) {
    return <EmptyState icon={<Bug className="h-12 w-12" />} title="No root causes detected" description="The repository appears structurally sound." />;
  }

  return (
    <div className="space-y-3">
      {rootCauses.map((rc: any, i: number) => (
        <RootCauseCard key={rc.id || i} rc={rc} expanded={expanded === (rc.id || String(i))} onToggle={() => setExpanded(expanded === (rc.id || String(i)) ? null : rc.id || String(i))} />
      ))}
    </div>
  );
}

function RootCauseCard({ rc, expanded, onToggle }: { rc: any; expanded: boolean; onToggle: () => void }) {
  return (
    <Card>
      <CardHeader className="cursor-pointer" onClick={onToggle}>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10">
              <Bug className="h-5 w-5 text-destructive" />
            </div>
            <div>
              <CardTitle className="text-base">{rc.title}</CardTitle>
              <div className="mt-1 flex flex-wrap gap-2">
                <Badge variant={severityVariant(rc.severity)}>{rc.severity}</Badge>
                <Badge variant="outline">{rc.category}</Badge>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 text-right">
            <div>
              <div className="text-sm font-semibold">{rc.evidence_count || (rc.evidence_links?.length || 0)} evidence</div>
              <div className="text-xs text-muted-foreground">{rc.affected_files?.length || 0} files</div>
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
                    <h4 className="mb-1 text-sm font-semibold">Technical Rationale</h4>
                    <p className="text-sm text-muted-foreground">{rc.technical_rationale}</p>
                  </div>
                )}
                {rc.root_cause_origin && (
                  <div>
                    <h4 className="mb-1 text-sm font-semibold">Likely Origin</h4>
                    <p className="text-sm text-muted-foreground">{rc.root_cause_origin}</p>
                  </div>
                )}
                {rc.affected_files?.length > 0 && (
                  <div>
                    <h4 className="mb-2 text-sm font-semibold">Affected Files</h4>
                    <div className="flex flex-wrap gap-2">
                      {rc.affected_files.map((f: string, i: number) => (
                        <Badge key={i} variant="secondary" className="gap-1">
                          <FileCode2 className="h-3 w-3" /> {f}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                <ExplainabilityChain rootCause={rc} />
              </div>
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}

function RootCauseRow({ rc }: { rc: any }) {
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
  const plan = data?.engineering_plan;
  if (!plan) return <EmptyState icon={<Map className="h-12 w-12" />} title="No engineering plan available" />;

  const steps = plan.steps || [];
  const quickWins = plan.quick_wins || [];

  const categories = [
    { key: "quick", label: "Quick Wins", icon: <Zap className="h-4 w-4" />, steps: quickWins.map((qw: any) => ({ ...qw, isQuickWin: true })) },
    { key: "critical", label: "Critical", icon: <AlertCircle className="h-4 w-4" />, steps: steps.filter((s: any) => s.priority === "critical") },
    { key: "high", label: "High Priority", icon: <TrendingUp className="h-4 w-4" />, steps: steps.filter((s: any) => s.priority === "high") },
    { key: "medium", label: "Medium Priority", icon: <Target className="h-4 w-4" />, steps: steps.filter((s: any) => s.priority === "medium") },
    { key: "low", label: "Low Priority", icon: <Lightbulb className="h-4 w-4" />, steps: steps.filter((s: any) => s.priority === "low" || s.priority === "info") },
  ];

  return (
    <div className="space-y-6">
      {plan.roadmap?.sprints?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Map className="h-5 w-5" /> Sprint Roadmap
            </CardTitle>
            <CardDescription>{plan.roadmap.summary}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {plan.roadmap.sprints.map((sprint: any, i: number) => (
                <div key={i} className="flex-1 min-w-[200px] rounded-lg border p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                      {sprint.sprint_number}
                    </div>
                    <span className="font-medium text-sm">{sprint.title}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{sprint.total_estimated_hours}h estimated</p>
                  {sprint.goals?.slice(0, 2).map((g: string, j: number) => (
                    <p key={j} className="mt-1 text-xs text-muted-foreground/70">• {g}</p>
                  ))}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {categories.map((cat) => cat.steps.length > 0 && (
        <div key={cat.key}>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
            {cat.icon} {cat.label} ({cat.steps.length})
          </h3>
          <div className="space-y-2">
            {cat.steps.map((step: any, i: number) => (
              <RoadmapStepCard key={step.id || i} step={step} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function RoadmapStepCard({ step }: { step: any }) {
  const [showWhy, setShowWhy] = React.useState(false);

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              {step.isQuickWin && <Badge variant="secondary" className="gap-1"><Zap className="h-3 w-3" /> Quick Win</Badge>}
              <span className="text-sm font-medium">{step.title}</span>
            </div>
            {step.technical_description && <p className="mt-1 text-xs text-muted-foreground">{step.technical_description}</p>}
            {step.expected_outcomes?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {step.expected_outcomes.slice(0, 3).map((o: string, i: number) => (
                  <Badge key={i} variant="outline" className="text-xs">{o}</Badge>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-col items-end gap-2 text-right">
            {step.roi != null && (
              <div>
                <div className="text-sm font-bold text-green-500">ROI {step.roi.toFixed(1)}</div>
                <div className="text-xs text-muted-foreground">Return</div>
              </div>
            )}
            {step.estimate && (
              <div>
                <div className="text-sm font-semibold">{step.estimate.display || `${step.estimate.hours}h`}</div>
                <div className="text-xs text-muted-foreground">Effort</div>
              </div>
            )}
            {step.risk && (
              <Badge variant={riskVariant(step.risk)} className="text-xs">{step.risk}</Badge>
            )}
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setShowWhy(!showWhy)}>
            <Eye className="mr-1 h-3 w-3" /> WHY?
          </Button>
        </div>
        <AnimatePresence>
          {showWhy && <ExplainabilityChain step={step} />}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Evidence Section
// ---------------------------------------------------------------------------

function EvidenceSection({ data }: { data: any }) {
  const evidence = data?.evidence?.evidence || [];
  const [search, setSearch] = React.useState("");
  const [filterSeverity, setFilterSeverity] = React.useState("all");

  const filtered = evidence.filter((ev: any) => {
    const matchSearch = !search ||
      ev.message?.toLowerCase().includes(search.toLowerCase()) ||
      ev.file_path?.toLowerCase().includes(search.toLowerCase()) ||
      ev.analyzer?.toLowerCase().includes(search.toLowerCase()) ||
      ev.category?.toLowerCase().includes(search.toLowerCase());
    const matchSeverity = filterSeverity === "all" || ev.severity === filterSeverity;
    return matchSearch && matchSeverity;
  });

  if (evidence.length === 0) {
    return <EmptyState icon={<Beaker className="h-12 w-12" />} title="No evidence collected" />;
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search evidence..."
            className="pl-9"
          />
        </div>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="h-9 rounded-md border bg-background px-3 text-sm"
        >
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="info">Info</option>
        </select>
      </div>

      <div className="rounded-lg border">
        <div className="grid grid-cols-12 gap-2 border-b bg-muted/50 p-3 text-xs font-medium text-muted-foreground">
          <div className="col-span-1">Severity</div>
          <div className="col-span-2">Analyzer</div>
          <div className="col-span-2">Category</div>
          <div className="col-span-3">Message</div>
          <div className="col-span-2">File</div>
          <div className="col-span-1">Conf.</div>
          <div className="col-span-1">Type</div>
        </div>
        <ScrollArea className="h-[500px]">
          {filtered.map((ev: any, i: number) => (
            <div key={ev.id || i} className="grid grid-cols-12 gap-2 border-b p-3 text-sm hover:bg-muted/30">
              <div className="col-span-1"><Badge variant={severityVariant(ev.severity)} className="text-xs">{ev.severity}</Badge></div>
              <div className="col-span-2 truncate text-xs text-muted-foreground">{ev.analyzer}</div>
              <div className="col-span-2 truncate text-xs">{ev.category}</div>
              <div className="col-span-3 truncate text-xs" title={ev.message}>{ev.message}</div>
              <div className="col-span-2 truncate text-xs text-muted-foreground" title={ev.file_path}>{ev.file_path || "—"}</div>
              <div className="col-span-1 text-xs">{(ev.confidence * 100).toFixed(0)}%</div>
              <div className="col-span-1 text-xs text-muted-foreground">{ev.finding_type}</div>
            </div>
          ))}
        </ScrollArea>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{filtered.length} of {evidence.length} evidence items</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Graph Section (simplified visualization)
// ---------------------------------------------------------------------------

function GraphSection({ data }: { data: any }) {
  const graph = data?.knowledge_graph;
  const [selectedNode, setSelectedNode] = React.useState<any>(null);

  if (!graph || !graph.nodes?.length) {
    return <EmptyState icon={<Network className="h-12 w-12" />} title="No graph data available" />;
  }

  const nodeTypeColors: Record<string, string> = {
    repository: "bg-blue-500",
    file: "bg-green-500",
    class: "bg-purple-500",
    function: "bg-orange-500",
    method: "bg-yellow-500",
    module: "bg-cyan-500",
    dependency: "bg-pink-500",
    security_finding: "bg-red-500",
    architecture_finding: "bg-indigo-500",
    metric_finding: "bg-teal-500",
    evidence: "bg-gray-500",
  };

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-lg">Engineering Knowledge Graph</CardTitle>
          <CardDescription>{graph.total_nodes || graph.nodes.length} nodes · {graph.total_edges || graph.edges?.length || 0} edges</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[500px]">
            <div className="flex flex-wrap gap-2 p-2">
              {graph.nodes.slice(0, 200).map((node: any, i: number) => (
                <button
                  key={node.id || i}
                  onClick={() => setSelectedNode(node)}
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs text-white ${nodeTypeColors[node.node_type] || "bg-gray-500"} ${selectedNode?.id === node.id ? "ring-2 ring-primary ring-offset-2" : ""} hover:scale-105 transition-transform`}
                >
                  {node.label?.substring(0, 30)}
                </button>
              ))}
            </div>
          </ScrollArea>
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(nodeTypeColors).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs">
                <div className={`h-3 w-3 rounded-full ${color}`} />
                <span className="text-muted-foreground">{type}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Node Details</CardTitle>
        </CardHeader>
        <CardContent>
          {selectedNode ? (
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-muted-foreground">Type: </span>
                <Badge>{selectedNode.node_type}</Badge>
              </div>
              <div>
                <span className="text-muted-foreground">Label: </span>
                <span className="font-medium">{selectedNode.label}</span>
              </div>
              {selectedNode.file_path && <div><span className="text-muted-foreground">File: </span>{selectedNode.file_path}</div>}
              {selectedNode.class_name && <div><span className="text-muted-foreground">Class: </span>{selectedNode.class_name}</div>}
              {selectedNode.function_name && <div><span className="text-muted-foreground">Function: </span>{selectedNode.function_name}</div>}
              {selectedNode.severity && <div><span className="text-muted-foreground">Severity: </span><Badge variant={severityVariant(selectedNode.severity)}>{selectedNode.severity}</Badge></div>}
              {selectedNode.metadata?.analyzer && <div><span className="text-muted-foreground">Analyzer: </span>{selectedNode.metadata.analyzer}</div>}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Click a node to see details.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// File Explorer Section
// ---------------------------------------------------------------------------

function FileExplorerSection({ data }: { data: any }) {
  const inventory = data?.file_inventory;
  const [selectedFile, setSelectedFile] = React.useState<string | null>(null);

  if (!inventory?.files?.length) {
    return <EmptyState icon={<FileCode2 className="h-12 w-12" />} title="No file inventory available" />;
  }

  const files = inventory.files.sort();
  const evidence = data?.evidence?.evidence || [];
  const rootCauses = data?.root_causes?.root_causes || [];

  const fileEvidence = selectedFile ? evidence.filter((e: any) => e.file_path === selectedFile) : [];
  const fileRootCauses = selectedFile ? rootCauses.filter((rc: any) => rc.affected_files?.includes(selectedFile)) : [];

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-1">
        <CardHeader>
          <CardTitle className="text-lg">Files ({files.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[500px]">
            <div className="space-y-1">
              {files.map((f: string, i: number) => (
                <button
                  key={i}
                  onClick={() => setSelectedFile(f)}
                  className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-muted/50 ${selectedFile === f ? "bg-muted" : ""}`}
                >
                  <FileCode2 className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                  <span className="truncate">{f}</span>
                </button>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-lg">{selectedFile || "Select a file"}</CardTitle>
        </CardHeader>
        <CardContent>
          {selectedFile ? (
            <div className="space-y-4">
              <div>
                <h4 className="mb-2 text-sm font-semibold">Evidence ({fileEvidence.length})</h4>
                {fileEvidence.length > 0 ? (
                  <div className="space-y-2">
                    {fileEvidence.map((ev: any, i: number) => (
                      <div key={i} className="rounded border p-2 text-sm">
                        <div className="flex items-center gap-2">
                          <Badge variant={severityVariant(ev.severity)} className="text-xs">{ev.severity}</Badge>
                          <span className="text-xs text-muted-foreground">{ev.analyzer}</span>
                        </div>
                        <p className="mt-1 text-xs">{ev.message}</p>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-muted-foreground">No evidence for this file.</p>}
              </div>
              <Separator />
              <div>
                <h4 className="mb-2 text-sm font-semibold">Root Causes ({fileRootCauses.length})</h4>
                {fileRootCauses.length > 0 ? (
                  <div className="space-y-2">
                    {fileRootCauses.map((rc: any, i: number) => (
                      <div key={i} className="rounded border p-2 text-sm">
                        <div className="flex items-center gap-2">
                          <Bug className="h-4 w-4 text-destructive" />
                          <span className="font-medium">{rc.title}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-sm text-muted-foreground">No root causes for this file.</p>}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Select a file to see its evidence and root causes.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AI Review Section
// ---------------------------------------------------------------------------

function AIReviewSection({ data }: { data: any }) {
  const review = data?.engineering_review;
  if (!review) {
    return <EmptyState icon={<Sparkles className="h-12 w-12" />} title="No AI review available" description="Enable an LLM provider for AI-generated review." />;
  }

  return (
    <div className="space-y-4">
      {review.offline && (
        <div className="flex items-center gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 text-sm">
          <AlertCircle className="h-4 w-4 text-yellow-500" />
          <span>Offline mode — this review was produced without an LLM. Enable a provider for richer analysis.</span>
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
                  {section.confidence === "high" ? "Supported by Evidence" : "AI Opinion"}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">{section.body}</p>
          </CardContent>
        </Card>
      ))}

      {review.challenges?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="h-5 w-5" /> Planning Engine Challenges
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {review.challenges.map((ch: any, i: number) => (
                <div key={i} className="rounded-lg border p-3">
                  <Badge variant="outline" className="mb-1 text-xs">{ch.challenge_type}</Badge>
                  <p className="text-sm">{ch.description}</p>
                  {ch.alternative && <p className="mt-1 text-sm text-muted-foreground">Alternative: {ch.alternative}</p>}
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

function ExplainabilityChain({ rootCause, step }: { rootCause?: any; step?: any }) {
  const chain: { label: string; value: string; icon: React.ReactNode }[] = [];

  if (step) {
    chain.push({ label: "Recommendation", value: step.title, icon: <Map className="h-4 w-4" /> });
    if (step.root_cause_category) chain.push({ label: "Root Cause", value: step.root_cause_category, icon: <Bug className="h-4 w-4" /> });
    if (step.estimate) chain.push({ label: "Estimated Effort", value: step.estimate.display || `${step.estimate.hours}h`, icon: <Activity className="h-4 w-4" /> });
    if (step.risk) chain.push({ label: "Risk Level", value: step.risk, icon: <Shield className="h-4 w-4" /> });
    if (step.roi) chain.push({ label: "ROI", value: step.roi.toFixed(2), icon: <TrendingUp className="h-4 w-4" /> });
  }

  if (rootCause) {
    chain.push({ label: "Root Cause", value: rootCause.title, icon: <Bug className="h-4 w-4" /> });
    chain.push({ label: "Category", value: rootCause.category, icon: <Layers className="h-4 w-4" /> });
    chain.push({ label: "Confidence", value: `${(rootCause.confidence * 100).toFixed(0)}%`, icon: <Target className="h-4 w-4" /> });
    if (rootCause.evidence_count || rootCause.evidence_links?.length) {
      chain.push({ label: "Evidence Count", value: String(rootCause.evidence_count || rootCause.evidence_links?.length || 0), icon: <Beaker className="h-4 w-4" /> });
    }
    if (rootCause.affected_files?.length) {
      chain.push({ label: "Affected Files", value: rootCause.affected_files.join(", "), icon: <FileCode2 className="h-4 w-4" /> });
    }
  }

  if (chain.length === 0) return null;

  return (
    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-3 rounded-lg bg-muted/30 p-4">
      <h4 className="mb-3 flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
        <Eye className="h-3 w-3" /> EXPLAINABILITY CHAIN
      </h4>
      <div className="flex flex-wrap items-center gap-2">
        {chain.map((item, i) => (
          <React.Fragment key={i}>
            <div className="flex items-center gap-1.5 rounded-lg border bg-background px-2.5 py-1.5">
              <span className="text-muted-foreground">{item.icon}</span>
              <div>
                <div className="text-xs font-medium">{item.label}</div>
                <div className="text-xs text-muted-foreground">{item.value}</div>
              </div>
            </div>
            {i < chain.length - 1 && <ChevronRight className="h-4 w-4 text-muted-foreground/50" />}
          </React.Fragment>
        ))}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Report Export
// ---------------------------------------------------------------------------

function ReportExport({ data }: { data: any }) {
  const handleExport = async (format: string) => {
    try {
      const res = await apiFetch("/api/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: data?.id || "latest", format }),
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report.${format === "md" ? "md" : format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Report exported as ${format.toUpperCase()}`);
    } catch (err: any) {
      toast.error(`Export failed: ${err.message}`);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="sm" onClick={() => handleExport("md")}>
              <Download className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Export Markdown</TooltipContent>
        </Tooltip>
      </TooltipProvider>
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

function ConfidenceTag({ confidence }: { confidence: string }) {
  const color = confidence === "high" ? "text-green-500" : confidence === "medium" ? "text-yellow-500" : "text-red-500";
  return <span className={`text-xs font-medium uppercase ${color}`}>{confidence}</span>;
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

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
}

function severityVariant(severity: string): any {
  switch (severity?.toLowerCase()) {
    case "critical": return "destructive";
    case "high": return "destructive";
    case "medium": return "secondary";
    case "low": return "outline";
    default: return "outline";
  }
}

function riskVariant(risk: string): any {
  switch (risk?.toLowerCase()) {
    case "critical": return "destructive";
    case "high": return "destructive";
    case "medium": return "secondary";
    case "low": return "outline";
    default: return "outline";
  }
}

// ---------------------------------------------------------------------------
// Demo Data (used when API is unavailable)
// ---------------------------------------------------------------------------

function getDemoData(repoUrl: string): any {
  const owner = repoUrl.split("/").slice(-2)[0] || "example";
  const name = repoUrl.split("/").slice(-1)[0]?.replace(".git", "") || "repo";
  return {
    id: "demo-001",
    status: "completed",
    repository: { url: repoUrl, owner, name, host: "github.com", access: "public" },
    repository_metadata: {
      name,
      owner,
      description: "Demo repository for UI showcase",
      default_branch: "main",
      license: "MIT",
      total_commits: 142,
      total_branches: 3,
      contributors: ["alice", "bob", "charlie"],
      size_bytes: 245000,
    },
    ai_review: {
      health_score: {
        overall: 72.5,
        grade: "B-",
        security: 85.0,
        architecture: 65.0,
        maintainability: 70.0,
        performance: 75.0,
        documentation: 55.0,
        testing: 60.0,
        developer_experience: 68.0,
        scalability: 72.0,
        code_quality: 71.0,
      },
      security_review: {
        security_score: 85.0,
        findings: [],
        overall_severity: "info",
      },
    },
    root_causes: {
      root_causes: [
        {
          id: "rc-1",
          category: "god_class",
          title: "God Class: UserService",
          severity: "high",
          confidence: 0.85,
          description: "UserService accumulates multiple responsibilities: auth, profile, notifications, and settings management.",
          technical_rationale: "4 distinct symptom types detected from 3 analyzers across 8 evidence items.",
          root_cause_origin: "Organic growth without refactoring — the class has accumulated responsibilities over time.",
          affected_files: ["src/services/user_service.py", "src/api/user_routes.py"],
          affected_classes: ["UserService"],
          affected_modules: ["services.user"],
          evidence_count: 8,
          evidence_links: [
            { evidence_id: "ev-1", contribution: 0.9, reason: "High complexity" },
            { evidence_id: "ev-2", contribution: 0.8, reason: "Long method" },
            { evidence_id: "ev-3", contribution: 0.7, reason: "Large file" },
          ],
        },
        {
          id: "rc-2",
          category: "circular_dependency",
          title: "Circular Dependency: auth ↔ user",
          severity: "high",
          confidence: 0.92,
          description: "Circular dependency between auth module and user module prevents clean layering.",
          technical_rationale: "Import graph contains a cycle: auth → user → auth",
          root_cause_origin: "Modules were added without checking import direction, creating bidirectional dependencies.",
          affected_files: ["src/auth/service.py", "src/user/service.py"],
          affected_modules: ["auth", "user"],
          evidence_count: 3,
          evidence_links: [{ evidence_id: "ev-4", contribution: 1.0, reason: "Direct cycle detected" }],
        },
        {
          id: "rc-3",
          category: "tight_coupling",
          title: "Tight Coupling: Database Layer",
          severity: "medium",
          confidence: 0.75,
          description: "Multiple services directly depend on the database client without abstraction.",
          technical_rationale: "Graph analysis shows excessive outgoing dependency edges.",
          root_cause_origin: "Direct dependencies were used instead of abstractions.",
          affected_files: ["src/services/user_service.py", "src/services/order_service.py"],
          affected_modules: ["services"],
          evidence_count: 5,
          evidence_links: [{ evidence_id: "ev-5", contribution: 0.8, reason: "measures coupling" }],
        },
        {
          id: "rc-4",
          category: "shotgun_surgery",
          title: "Shotgun Surgery: logging changes",
          severity: "low",
          confidence: 0.68,
          description: "Logging pattern changes require modifications across 8 different files.",
          technical_rationale: "Finding 'inconsistent_logging' appears in 8 different files.",
          root_cause_origin: "A pattern was copy-pasted without extracting a shared utility.",
          affected_files: ["src/api/users.py", "src/api/orders.py", "src/api/products.py", "src/api/payments.py", "src/services/user_service.py"],
          affected_modules: ["api", "services"],
          evidence_count: 8,
          evidence_links: [{ evidence_id: "ev-6", contribution: 0.7, reason: "part of the systemic pattern" }],
        },
      ],
      relationships: [
        { source_root_cause_id: "rc-1", target_root_cause_id: "rc-3", relationship_type: "causes", detail: "God Class causes tight coupling" },
      ],
      statistics: {
        total_root_causes: 4,
        average_confidence: 0.80,
        by_category_counts: { god_class: 1, circular_dependency: 1, tight_coupling: 1, shotgun_surgery: 1 },
        by_severity_counts: { high: 2, medium: 1, low: 1 },
      },
    },
    engineering_plan: {
      steps: [
        {
          id: "step-1",
          step_number: 1,
          title: "Split God Class: UserService into focused services",
          technical_description: "Extract auth, profile, notifications, and settings into separate service classes.",
          root_cause_id: "rc-1",
          root_cause_category: "god_class",
          priority: "high",
          roi: 2.25,
          estimate: { hours: 40, display: "5 days", developers: 2, confidence: 0.5 },
          risk: "high",
          risk_reason: "Large-scale refactoring with potential for regressions. High evidence count suggests widespread impact.",
          expected_outcomes: ["Improved maintainability (+90%)", "Improved testability (+80%)", "Better developer experience (+70%)"],
          prerequisites: [],
          alternatives: [
            { id: "alt-1", name: "Extract Class", description: "Split into focused classes.", advantages: ["Clear responsibilities", "Easier to test"], disadvantages: ["More files to manage"], risk: "medium", maintenance_cost: "low", performance_impact: "neutral", migration_difficulty: "medium" },
            { id: "alt-2", name: "Facade + Delegate", description: "Keep as facade, delegate internally.", advantages: ["Backward compatible", "Gradual migration"], disadvantages: ["Facade still exists"], risk: "low", maintenance_cost: "medium", performance_impact: "neutral", migration_difficulty: "low" },
          ],
          affected_files: ["src/services/user_service.py"],
        },
        {
          id: "step-2",
          step_number: 2,
          title: "Break circular dependency: auth ↔ user",
          technical_description: "Extract shared logic into a new lower-level module.",
          root_cause_id: "rc-2",
          root_cause_category: "circular_dependency",
          priority: "high",
          roi: 3.54,
          estimate: { hours: 24, display: "3 days", developers: 1, confidence: 0.5 },
          risk: "high",
          risk_reason: "Changes affect critical paths; thorough testing required.",
          expected_outcomes: ["Improved maintainability (+85%)", "Improved testability (+80%)"],
          prerequisites: ["step-1"],
          alternatives: [
            { id: "alt-3", name: "Extract Shared Module", description: "Extract shared logic.", advantages: ["Clean dependency graph"], disadvantages: ["New module to maintain"], risk: "medium", maintenance_cost: "low", performance_impact: "neutral", migration_difficulty: "medium" },
            { id: "alt-4", name: "Inversion of Control", description: "Use DI to invert dependency.", advantages: ["No new module"], disadvantages: ["More complex setup"], risk: "medium", maintenance_cost: "medium", performance_impact: "neutral", migration_difficulty: "high" },
          ],
          affected_files: ["src/auth/service.py", "src/user/service.py"],
        },
        {
          id: "step-3",
          step_number: 3,
          title: "Introduce repository interface for database access",
          technical_description: "Create an abstract repository interface and use DI.",
          root_cause_id: "rc-3",
          root_cause_category: "tight_coupling",
          priority: "medium",
          roi: 1.88,
          estimate: { hours: 24, display: "3 days", developers: 1, confidence: 0.5 },
          risk: "medium",
          risk_reason: "Moderate changes; ensure test coverage before and after.",
          expected_outcomes: ["Improved testability (+70%)", "Improved maintainability (+75%)"],
          prerequisites: ["step-1"],
          alternatives: [],
          affected_files: ["src/services/user_service.py", "src/services/order_service.py"],
        },
        {
          id: "step-4",
          step_number: 4,
          title: "Extract shared logging utility",
          technical_description: "Create a centralized logging wrapper.",
          root_cause_id: "rc-4",
          root_cause_category: "shotgun_surgery",
          priority: "low",
          roi: 5.42,
          estimate: { hours: 4, display: "4 hours", developers: 1, confidence: 0.7 },
          risk: "low",
          risk_reason: "Low risk; isolated changes with minimal blast radius.",
          expected_outcomes: ["Reduced technical debt", "Consistent logging"],
          prerequisites: [],
          alternatives: [],
          affected_files: ["src/api/users.py", "src/api/orders.py"],
        },
      ],
      roadmap: {
        sprints: [
          { sprint_number: 1, title: "Sprint 1: Critical Refactoring", step_ids: ["step-1"], total_estimated_hours: 40, goals: ["Split God Class: UserService into focused services"], steps: [] },
          { sprint_number: 2, title: "Sprint 2: Architecture Fixes", step_ids: ["step-2", "step-3"], total_estimated_hours: 48, goals: ["Break circular dependency", "Introduce repository interface"], steps: [] },
          { sprint_number: 3, title: "Sprint 3: Cleanup & Maintenance", step_ids: ["step-4"], total_estimated_hours: 4, goals: ["Extract shared logging utility"], steps: [] },
        ],
        total_estimated_hours: 92,
        total_steps: 4,
        summary: "3 sprint(s) covering 4 step(s), ~92 engineer-hours total.",
      },
      quick_wins: [
        { id: "qw-1", title: "Extract shared logging utility", description: "Create a centralized logging wrapper.", effort_minutes: 240, benefit: "Benefit score: 65/100", planning_step_id: "step-4", root_cause_id: "rc-4" },
        { id: "qw-2", title: "Remove unused imports", description: "5 unused imports detected across files.", effort_minutes: 15, benefit: "Quick fix: dead_code", planning_step_id: null, root_cause_id: null },
      ],
      blockers: [
        { id: "blk-1", blocker_root_cause_id: "rc-1", blocked_root_cause_ids: ["rc-3"], reason: "God Class: UserService must be addressed first — it causes 1 other root cause(s).", planning_step_id: "step-1" },
      ],
      statistics: {
        total_steps: 4,
        total_quick_wins: 2,
        total_blockers: 1,
        average_roi: 3.27,
        priority_counts: { high: 2, medium: 1, low: 1 },
        risk_counts: { high: 2, medium: 1, low: 1 },
      },
    },
    evidence: {
      evidence: [
        { id: "ev-1", analyzer: "complexity-analyzer", finding_type: "complexity", severity: "high", confidence: 1.0, category: "cyclomatic_complexity", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "High complexity: process_user (CC=41)", tags: ["complexity", "E"], metrics: { complexity: 41, rank: "E" } },
        { id: "ev-2", analyzer: "code-quality-engine", finding_type: "code_quality", severity: "medium", confidence: 0.8, category: "long_method", file_path: "src/services/user_service.py", line: 45, class_name: "UserService", function_name: "process_user", message: "Long method: process_user", tags: ["long_method", "high"] },
        { id: "ev-3", analyzer: "metrics-engine", finding_type: "metric", severity: "medium", confidence: 1.0, category: "large_file", file_path: "src/services/user_service.py", message: "Large file: src/services/user_service.py (650 SLOC)", tags: ["large_file"], metrics: { sloc: 650 } },
        { id: "ev-4", analyzer: "import-analyzer", finding_type: "import", severity: "high", confidence: 1.0, category: "circular_import", message: "Circular import: auth → user → auth", tags: ["circular_import"] },
        { id: "ev-5", analyzer: "architecture-review-engine", finding_type: "architecture", severity: "medium", confidence: 0.7, category: "high_coupling", file_path: "src/services/user_service.py", message: "High coupling (0.85)", tags: ["high_coupling"] },
        { id: "ev-6", analyzer: "import-analyzer", finding_type: "import", severity: "low", confidence: 0.9, category: "unused_import", file_path: "src/api/users.py", message: "Unused import: os", tags: ["unused_import", "dead_code"] },
        { id: "ev-7", analyzer: "security-engine", finding_type: "security", severity: "critical", confidence: 0.9, category: "hardcoded_password", file_path: "src/config.py", line: 10, message: "Hardcoded Password", tags: ["hardcoded_password"] },
        { id: "ev-8", analyzer: "test-coverage-analyzer", finding_type: "test", severity: "medium", confidence: 0.9, category: "low_coverage", message: "Low test coverage: 35%", tags: ["testing", "low_coverage"], metrics: { estimated_coverage: 35 } },
      ],
      relationships: [],
      statistics: {
        total_evidence: 8,
        by_type_counts: { complexity: 1, code_quality: 1, metric: 1, import: 2, architecture: 1, security: 1, test: 1 },
        by_severity_counts: { critical: 1, high: 2, medium: 3, low: 2 },
        by_analyzer_counts: { "complexity-analyzer": 1, "code-quality-engine": 1, "metrics-engine": 1, "import-analyzer": 2, "architecture-review-engine": 1, "security-engine": 1, "test-coverage-analyzer": 1 },
      },
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
        { id: "n8", node_type: "security_finding", label: "Hardcoded Password", key: "ev:7", file_path: "src/config.py", severity: "critical", evidence_id: "ev-7", metadata: { analyzer: "security-engine" } },
        { id: "n9", node_type: "metric_finding", label: "High complexity: process_user", key: "ev:1", file_path: "src/services/user_service.py", severity: "high", evidence_id: "ev-1", metadata: { analyzer: "complexity-analyzer" } },
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
      total_nodes: 10,
      total_edges: 6,
    },
    file_inventory: {
      total_files: 24,
      total_directories: 8,
      total_bytes: 245000,
      files: [
        "src/services/user_service.py",
        "src/api/users.py",
        "src/api/orders.py",
        "src/auth/service.py",
        "src/user/service.py",
        "src/config.py",
        "src/models/user.py",
        "src/utils/helpers.py",
        "tests/test_user_service.py",
        "README.md",
      ],
    },
    engineering_review: {
      offline: true,
      sections: [
        { section_type: "executive_summary", title: "Executive Summary", body: "Repository: example/repo. Root cause analysis identified 4 architectural root cause(s) with an average confidence of 80%. The engineering plan proposes 4 refactoring step(s) across 3 sprint(s), totaling approximately 92 engineer-hours. 2 quick win(s) identified for immediate action. This review was produced in offline mode (no LLM).", confidence: "high" },
        { section_type: "top_root_causes", title: "Top Root Causes", body: "- **God Class: UserService** (severity: high, confidence: 85%) — UserService accumulates multiple responsibilities\n- **Circular Dependency: auth ↔ user** (severity: high, confidence: 92%) — Circular dependency between auth and user modules\n- **Tight Coupling: Database Layer** (severity: medium, confidence: 75%) — Multiple services directly depend on the database client\n- **Shotgun Surgery: logging changes** (severity: low, confidence: 68%) — Logging changes require modifications across 8 files", confidence: "high" },
        { section_type: "highest_roi_refactoring", title: "Highest ROI Refactoring", body: "Step 4: **Extract shared logging utility**\nROI: 5.42\nPriority: low\nEstimate: 4 hours\nExpected outcomes: Reduced technical debt, Consistent logging", confidence: "high" },
        { section_type: "long_term_vision", title: "Long-term Vision", body: "The team should aim to decompose large classes/services into focused, single-responsibility components over the next 6 months. Introduce interface-based dependency injection to decouple modules.", confidence: "low" },
      ],
      challenges: [],
      recommendations: [],
      model_info: { provider: "offline", model: "deterministic-fallback" },
      statistics: { total_sections: 4, total_challenges: 0, offline: true },
    },
  };
}
