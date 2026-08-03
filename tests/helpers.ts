import { analyzeLocalFiles } from "../src/lib/local-analysis";

export function makeFile(content: string, path: string): File {
  return new File([content], path, { type: "text/plain" });
}

export interface RepoFile {
  path: string;
  content: string;
}

export async function scanRepo(files: RepoFile[]): Promise<Awaited<ReturnType<typeof analyzeLocalFiles>>> {
  const fs = files.map((f) => makeFile(f.content, f.path));
  return analyzeLocalFiles(fs);
}

export function categoriesOf(scan: Awaited<ReturnType<typeof analyzeLocalFiles>>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const e of scan.rawEvidence) out[e.category] = (out[e.category] || 0) + 1;
  return out;
}

export function evidenceIn(scan: Awaited<ReturnType<typeof analyzeLocalFiles>>, cat: string): string[] {
  return scan.rawEvidence.filter((e) => e.category === cat).map((e) => e.file_path);
}
