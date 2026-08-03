/**
 * Bring-your-own-key LLM layer — called from the BROWSER directly to the
 * provider API. The API key never reaches our server (privacy-first).
 *
 * Provider coverage: OpenAI, OpenRouter, Anthropic, Google Gemini,
 * Azure OpenAI, Ollama (local).
 */

export interface LLMRunConfig {
  provider: string;
  apiKey: string;
  model: string;
  temperature: string;
  maxTokens: string;
  baseUrl: string;
  deployment: string;
  apiVersion: string;
  host: string;
  port: string;
}

export interface LLMSection {
  title: string;
  body: string;
  confidence: "high" | "medium" | "low";
  section_type?: string;
}

export interface LLMExplanationResult {
  sections: LLMSection[];
  error?: string;
  provider: string;
}

/**
 * HTTP hata durumunu kullanıcının anlayacağı mesaja çevirir.
 * 429 (kota) ve 401/403 (key) en yaygın kullanıcı hatalarıdır.
 */
function apiError(status: number, fallback: string): Error {
  if (status === 429) {
    return new Error("Kota aşıldı (429) — provider hesabınızın ücretsiz kotası dolmuş veya billing kapalı. Hesap/plan durumunu kontrol edin.");
  }
  if (status === 401 || status === 403) {
    return new Error(`API anahtarı reddedildi (${status}) — key'i ve model adını kontrol edin.`);
  }
  return new Error(`LLM API hatası (${status}): ${fallback}`);
}

const DEFAULT_TIMEOUT_MS = 90_000;

/**
 * Calls the provider and returns the raw text of the model response.
 * Throws Error with a user-readable message on network/auth/parse failure.
 */
export async function callLLM(config: LLMRunConfig, prompt: string, systemPrompt?: string): Promise<string> {
  const provider = (config.provider || "").toLowerCase();
  const temperature = Number(config.temperature || "0.3") || 0.3;
  const maxTokens = Number(config.maxTokens || "4096") || 4096;
  const model = normalizeModel(provider, config.model);

  switch (provider) {
    case "openai":
    case "openrouter": {
      const baseUrl = (config.baseUrl?.trim() || (provider === "openrouter" ? "https://openrouter.ai/api" : "https://api.openai.com/v1")).replace(/\/$/, "");
      const res = await fetchWithTimeout(`${baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${config.apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages: [
            ...(systemPrompt ? [{ role: "system", content: systemPrompt }] : []),
            { role: "user", content: prompt },
          ],
          temperature,
          max_tokens: maxTokens,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw apiError(res.status, data?.error?.message || res.statusText);
      return data?.choices?.[0]?.message?.content || "";
    }

    case "anthropic": {
      const res = await fetchWithTimeout("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": config.apiKey,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model,
          max_tokens: maxTokens,
          ...(systemPrompt ? { system: systemPrompt } : {}),
          messages: [{ role: "user", content: prompt }],
        }),
      });
      const data = await res.json();
      if (!res.ok) throw apiError(res.status, data?.error?.message || res.statusText);
      return data?.content?.map((c: any) => c.text || "").join("") || "";
    }

    case "gemini": {
      const key = config.apiKey.trim();
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(key)}`;
      const res = await fetchWithTimeout(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature, maxOutputTokens: maxTokens },
          ...(systemPrompt ? { systemInstruction: { parts: [{ text: systemPrompt }] } } : {}),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw apiError(res.status, data?.error?.message || res.statusText);
      return data?.candidates?.[0]?.content?.parts?.map((p: any) => p.text || "").join("") || "";
    }

    case "azure_openai": {
      const baseUrl = (config.baseUrl || "").replace(/\/$/, "");
      const deployment = config.deployment?.trim() || model;
      const apiVersion = config.apiVersion?.trim() || "2024-02-15-preview";
      if (!baseUrl) throw new Error("Azure OpenAI için Base URL gerekli (Settings).");
      const res = await fetchWithTimeout(
        `${baseUrl}/openai/deployments/${encodeURIComponent(deployment)}/chat/completions?api-version=${encodeURIComponent(apiVersion)}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "api-key": config.apiKey,
          },
          body: JSON.stringify({
            messages: [
              ...(systemPrompt ? [{ role: "system", content: systemPrompt }] : []),
              { role: "user", content: prompt },
            ],
            temperature,
            max_tokens: maxTokens,
          }),
        }
      );
      const data = await res.json();
      if (!res.ok) throw apiError(res.status, data?.error?.message || res.statusText);
      return data?.choices?.[0]?.message?.content || "";
    }

    case "ollama": {
      const host = config.host?.trim() || "http://localhost";
      const port = config.port?.trim() || "11434";
      const res = await fetchWithTimeout(`${host.replace(/\/$/, "")}:${port}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model,
          messages: [{ role: "user", content: prompt }],
          stream: false,
          options: { temperature },
        }),
      });
      const data = await res.json();
      if (!res.ok) throw apiError(res.status, data?.error || res.statusText);
      return data?.message?.content || "";
    }

    default:
      throw new Error(`Bilinmeyen provider: ${config.provider}`);
  }
}

function defaultModelFor(provider: string): string {
  switch (provider) {
    case "anthropic": return "claude-sonnet-4-20250514";
    case "gemini": return "gemini-3.5-flash";
    case "openrouter": return "openai/gpt-4o-mini";
    case "ollama": return "llama3.2";
    default: return "gpt-4o-mini";
  }
}

/**
 * Kullanıcıdan gelen model adını provider'ın beklediği formata getirir:
 * - boşlukları "-" yapar ("gemini 2.0 flash" -> "gemini-2.0-flash")
 * - "models/" prefix'ini kaldırır ("models/gemini-2.0-flash" -> "gemini-2.0-flash")
 * - boşsa provider için varsayılanı kullanır
 */
function normalizeModel(provider: string, model: string | undefined): string {
  const m = (model || "").trim().replace(/^models\//i, "").replace(/\s+/g, "-");
  return m || defaultModelFor(provider);
}

async function fetchWithTimeout(url: string, init: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (err: any) {
    if (err?.name === "AbortError") throw new Error("LLM isteği zaman aşımına uğradı (90sn).");
    throw new Error(`Ağ hatası: ${err?.message || err}`);
  } finally {
    clearTimeout(timer);
  }
}

/** LLM'den istenen JSON şekli. */
const SECTION_PROMPT_TEMPLATE = `You are a senior code reviewer. Explain the static-analysis findings below in plain, actionable language (2-4 sentences per finding, in the user's language). Do NOT invent findings — only explain what is listed. Respond with JSON ONLY in this exact shape:
{"sections":[{"title":"short title","body":"explanation","confidence":"high|medium|low"}]}
`;

export interface FindingSummary {
  category: string;
  severity: string;
  message: string;
  file_path: string;
  evidence_count: number;
  verified: number;
}

export interface EvidenceSnippet {
  file_path: string;
  line: number;
  snippet: string;
}

/**
 * Builds the compact prompt from root causes + top evidence snippets.
 */
export function buildLLMPrompt(
  rootCauses: FindingSummary[],
  snippets: EvidenceSnippet[]
): string {
  const lines: string[] = [];
  lines.push("Findings:");
  for (const rc of rootCauses.slice(0, 10)) {
    lines.push(`- [${rc.severity}] ${rc.category}: ${rc.message} (${rc.file_path}, ${rc.verified}/${rc.evidence_count} kanıt doğrulandı)`);
  }
  if (snippets.length > 0) {
    lines.push("");
    lines.push("Key evidence snippets:");
    for (const s of snippets.slice(0, 3)) {
      const snippet = s.snippet.replace(/\s+/g, " ").slice(0, 220);
      lines.push(`- ${s.file_path}:${s.line}: ${snippet}`);
    }
  }
  lines.push("");
  lines.push("Explain the top 3 most important findings; keep the rest brief.");
  return lines.join("\n");
}

/** LLM yanıtından JSON sections'ı ayıklar; başarısızsa ham metin fallback. */
export function parseLLMSections(raw: string): LLMSection[] {
  const text = raw.trim();
  // ```json ... ``` fence'lerini kaldır
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidate = fenced ? fenced[1].trim() : text;
  // İlk { ... son } arası
  const start = candidate.indexOf("{");
  const end = candidate.lastIndexOf("}");
  if (start !== -1 && end > start) {
    try {
      const parsed = JSON.parse(candidate.slice(start, end + 1));
      const arr = Array.isArray(parsed) ? parsed : parsed?.sections;
      if (Array.isArray(arr)) {
        const sections = arr
          .filter((s: any) => s && (s.title || s.body))
          .map((s: any) => ({
            title: String(s.title || "Açıklama"),
            body: String(s.body || ""),
            confidence: (["high", "medium", "low"].includes(s.confidence) ? s.confidence : "medium") as LLMSection["confidence"],
            ...(s.section_type ? { section_type: String(s.section_type) } : {}),
          }));
        if (sections.length > 0) return sections;
      }
    } catch {
      // parse başarısız — ham metin fallback
    }
  }
  return [{ title: "LLM Açıklaması", body: text || "Yanıt boş döndü.", confidence: "medium" }];
}

/**
 * Runs the explanation flow for a report's root causes.
 * Called from the browser — the API key never leaves the client.
 */
export async function explainWithLLM(
  config: LLMRunConfig,
  rootCauses: FindingSummary[],
  snippets: EvidenceSnippet[]
): Promise<LLMExplanationResult> {
  if (!config.apiKey && config.provider !== "ollama") {
    return { sections: [], provider: config.provider || "", error: "API key yapılandırılmamış." };
  }
  const prompt = buildLLMPrompt(rootCauses, snippets);
  try {
    const raw = await callLLM(config, prompt, SECTION_PROMPT_TEMPLATE);
    return { sections: parseLLMSections(raw), provider: config.provider || "" };
  } catch (err: any) {
    return { sections: [], provider: config.provider || "", error: err?.message || String(err) };
  }
}
