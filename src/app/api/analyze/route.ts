import { NextRequest, NextResponse } from "next/server";
import { readdirSync, statSync, readFileSync, rmSync, existsSync } from "fs";
import { join, extname } from "path";
import { cloneRepository } from "@/lib/real-analysis-engine";
import { analyzeLocalFiles, buildLocalReport, shouldSkip, parseGitignore } from "@/lib/local-analysis";
import { isPythonBackendConfigured, callPythonBackend } from "@/lib/backend-config";
import { persistAnalysis } from "@/lib/analysis-store";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const CLONE_TIMEOUT_MS = 60000;
const MAX_CLONE_BYTES = 200 * 1024 * 1024;

/**
 * Analyze endpoint — REAL analysis.
 *
 * POST /api/analyze — clones the repository and scans its files with the same
 * engine used for local folders (analyzeLocalFiles + buildLocalReport).
 * No synthetic/demo data unless cloning fails.
 *
 * Accepts { repository_url, use_cache, llm_config } and returns { job_id, status }.
 */

/** Clone edilen dizindeki dosyaları File[] olarak toplar (node_modules/.git hariç). */
function collectFilesFromDir(dir: string, maxFiles = 8000): File[] {
  const files: File[] = [];
  let totalBytes = 0;

  // Repo'nun kendi .gitignore'undaki segmentler — repo sahibi hangi dizinin
  // analiz dışı olduğuna .gitignore ile karar verir (motor tahmin etmez).
  let gitignoreSegs: Set<string> | undefined;
  try {
    const giPath = join(dir, ".gitignore");
    if (existsSync(giPath)) {
      gitignoreSegs = parseGitignore(readFileSync(giPath, "utf8"));
    }
  } catch {
    gitignoreSegs = undefined;
  }

  const visit = (d: string) => {
    if (files.length >= maxFiles) return;
    let entries: string[] = [];
    try {
      entries = readdirSync(d);
    } catch {
      return;
    }
    for (const name of entries) {
      if (files.length >= maxFiles) return;
      const full = join(d, name);
      try {
        const st = statSync(full);
        if (st.isDirectory()) {
          if (name === ".git" || name === "node_modules" || name === "dist" || name === "build" || name === ".next") continue;
          visit(full);
        } else if (st.isFile() && st.size < 1_000_000 && totalBytes < MAX_CLONE_BYTES) {
          const relPath = full.slice(dir.length).replace(/\\/g, "/").replace(/^\//, "");
          if (shouldSkip(relPath, gitignoreSegs)) continue;
          // Extension filtre: local-analysis kendi SOURCE_EXTS'i ile de filtreler,
          // burada sadece binary olanları atla.
          const ext = extname(name).toLowerCase();
          if ([".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf", ".zip", ".gz", ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".exe", ".dll", ".so", ".class", ".pyc", ".db", ".sqlite"].includes(ext)) continue;
          try {
            const content = readFileSync(full, "utf8");
            files.push(new File([content], relPath));
            totalBytes += st.size;
          } catch {
            // binary/encoding — atla
          }
        }
      } catch {
        // erişilemez — atla
      }
    }
  };

  visit(dir);
  return files;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const repoUrl: string = body.repository_url || "";
    if (!repoUrl) {
      return NextResponse.json({ error: "repository_url is required" }, { status: 400 });
    }
    if (repoUrl.startsWith("local://")) {
      return NextResponse.json({ error: "Use local folder upload for local:// URLs" }, { status: 400 });
    }

    // Python backend yapılandırılmışsa onu kullan (gerçek analiz).
    if (isPythonBackendConfigured()) {
      const backendResult = await callPythonBackend<{ job_id: string; status: string }>(
        "/analyze",
        { method: "POST", body: { repository_url: repoUrl, use_cache: body.use_cache ?? true } }
      );
      if (backendResult) {
        return NextResponse.json({
          job_id: backendResult.job_id,
          status: backendResult.status,
          repository_url: repoUrl,
        });
      }
    }

    // Gerçek analiz: repo'yu klonla + aynı motorla tara.
    const cleanUrl = repoUrl.replace(/\.git$/, "").replace(/\/$/, "");
    const parts = cleanUrl.split("/");
    const org = parts[parts.length - 2] || "unknown";
    const name = parts[parts.length - 1] || "repo";
    const repoName = `${org}/${name}`;

    const clone = cloneRepository(cleanUrl, repoName);
    if (!clone.success) {
      return NextResponse.json(
        { error: `Repo klonlanamadı: ${clone.error || "bilinmeyen hata"}` },
        { status: 502 }
      );
    }

    const files = collectFilesFromDir(clone.path);
    if (files.length === 0) {
      return NextResponse.json(
        { error: "Repoda analiz edilebilir kaynak dosya bulunamadı" },
        { status: 422 }
      );
    }

    const llmConfig = body.llm_config;
    const options = {
      useLLM: !!llmConfig && (llmConfig.provider === "ollama" || (llmConfig.provider && llmConfig.apiKey)),
      llmProvider: llmConfig?.provider,
      llmModel: llmConfig?.model,
    };

    const scan = await analyzeLocalFiles(files);
    const report = buildLocalReport(scan, repoName, options);
    report.repository.url = cleanUrl;
    report.repository.host = "github.com";
    report.repository.access = "public";
    report.repository_metadata.scan_summary.is_clone = true;

    // Analiz bitti — .git klasörünü sil (disk israfı), çalışma ağacını koru.
    try {
      rmSync(join(clone.path, ".git"), { recursive: true, force: true });
    } catch { /* best-effort */ }

    const jobId = report.id;
    jobStore.set(jobId, report);
    persistAnalysis(jobId, report);

    return NextResponse.json({ job_id: jobId, status: "completed", repository_url: cleanUrl, is_real: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

// In-memory job store (per server instance).
export const jobStore: Map<string, unknown> = new Map();
