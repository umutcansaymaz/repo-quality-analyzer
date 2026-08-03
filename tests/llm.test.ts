/**
 * LLM katmanı testleri — mock fetch ile provider formatları, JSON parse,
 * hata ve zaman aşımı yolları. Gerçek ağ çağrısı YOKTUR.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { callLLM, parseLLMSections, buildLLMPrompt, explainWithLLM } from "../src/lib/llm";

const baseConfig = {
  provider: "openai",
  apiKey: "sk-test",
  model: "gpt-4o-mini",
  temperature: "0.3",
  maxTokens: "4096",
  baseUrl: "",
  deployment: "",
  apiVersion: "2024-02-15-preview",
  host: "http://localhost",
  port: "11434",
};

afterEach(() => {
  vi.restoreAllMocks();
});

function mockFetchOnce(status: number, body: unknown) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: async () => body,
  }));
}

describe("callLLM — OpenAI", () => {
  it("chat/completions URL + Bearer header + payload üretir", async () => {
    mockFetchOnce(200, { choices: [{ message: { content: "merhaba" } }] });
    const fetchMock = vi.mocked(fetch);
    const out = await callLLM(baseConfig, "test prompt");
    expect(out).toBe("merhaba");
    const [url, init] = fetchMock.mock.calls[0] as [string, any];
    expect(url).toBe("https://api.openai.com/v1/chat/completions");
    expect(init.headers.Authorization).toBe("Bearer sk-test");
    const body = JSON.parse(init.body);
    expect(body.model).toBe("gpt-4o-mini");
    expect(body.messages[0].content).toBe("test prompt");
  });
});

describe("callLLM — OpenRouter", () => {
  it("openrouter baseUrl kullanır", async () => {
    mockFetchOnce(200, { choices: [{ message: { content: "x" } }] });
    const out = await callLLM({ ...baseConfig, provider: "openrouter" }, "p");
    expect(out).toBe("x");
    const url = vi.mocked(fetch).mock.calls[0][0];
    expect(String(url)).toContain("openrouter.ai");
  });
});

describe("callLLM — Anthropic", () => {
  it("x-api-key + anthropic-version header + content parse", async () => {
    mockFetchOnce(200, { content: [{ type: "text", text: "claude yanıtı" }] });
    const out = await callLLM({ ...baseConfig, provider: "anthropic" }, "p");
    expect(out).toBe("claude yanıtı");
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, any];
    expect(String(url)).toContain("api.anthropic.com/v1/messages");
    expect(init.headers["x-api-key"]).toBe("sk-test");
  });
});

describe("callLLM — Gemini", () => {
  it("key query param + candidates parse", async () => {
    mockFetchOnce(200, { candidates: [{ content: { parts: [{ text: "gemini yanıtı" }] } }] });
    const out = await callLLM({ ...baseConfig, provider: "gemini" }, "p");
    expect(out).toBe("gemini yanıtı");
    const url = String(vi.mocked(fetch).mock.calls[0][0]);
    expect(url).toContain("generativelanguage.googleapis.com");
    expect(url).toContain("key=sk-test");
  });
});

describe("callLLM — Azure", () => {
  it("deployment + api-version URL'i ve api-key header", async () => {
    mockFetchOnce(200, { choices: [{ message: { content: "azure" } }] });
    const out = await callLLM(
      { ...baseConfig, provider: "azure_openai", baseUrl: "https://my-resource.openai.azure.com", deployment: "gpt-35" },
      "p"
    );
    expect(out).toBe("azure");
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, any];
    expect(String(url)).toContain("/openai/deployments/gpt-35/chat/completions");
    expect(String(url)).toContain("api-version=2024-02-15-preview");
    expect(init.headers["api-key"]).toBe("sk-test");
  });

  it("baseUrl yoksa hata verir", async () => {
    await expect(callLLM({ ...baseConfig, provider: "azure_openai", baseUrl: "" }, "p")).rejects.toThrow("Base URL");
  });
});

describe("callLLM — Ollama", () => {
  it("host:port /api/chat + message parse", async () => {
    mockFetchOnce(200, { message: { content: "ollama yanıtı" } });
    const out = await callLLM({ ...baseConfig, provider: "ollama", host: "http://127.0.0.1", port: "11434" }, "p");
    expect(out).toBe("ollama yanıtı");
    const url = String(vi.mocked(fetch).mock.calls[0][0]);
    expect(url).toBe("http://127.0.0.1:11434/api/chat");
  });
});

describe("callLLM — hatalar", () => {
  it("API hatası mesajı yüzeye çıkar", async () => {
    mockFetchOnce(401, { error: { message: "Invalid API key" } });
    await expect(callLLM(baseConfig, "p")).rejects.toThrow("401");
  });

  it("ağ hatası anlamlı mesaja çevrilir", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(callLLM(baseConfig, "p")).rejects.toThrow("Ağ hatası");
  });

  it("bilinmeyen provider reddedilir", async () => {
    await expect(callLLM({ ...baseConfig, provider: "nope" }, "p")).rejects.toThrow("Bilinmeyen");
  });
});

describe("parseLLMSections", () => {
  it("düz JSON array parse edilir", () => {
    const raw = `{"sections":[{"title":"T1","body":"B1","confidence":"high"},{"title":"T2","body":"B2","confidence":"low"}]}`;
    const s = parseLLMSections(raw);
    expect(s).toHaveLength(2);
    expect(s[0].confidence).toBe("high");
  });

  it("```json fence kaldırılır", () => {
    const raw = "```json\n{\"sections\":[{\"title\":\"T\",\"body\":\"B\",\"confidence\":\"medium\"}]}\n```";
    const s = parseLLMSections(raw);
    expect(s).toHaveLength(1);
  });

  it("geçersiz JSON → ham metin fallback", () => {
    const s = parseLLMSections("Bu bir düz metin yanıtı.");
    expect(s).toHaveLength(1);
    expect(s[0].body).toContain("düz metin");
  });

  it("geçersiz confidence medium'a normalize edilir", () => {
    const raw = `{"sections":[{"title":"T","body":"B","confidence":"ultra"}]}`;
    expect(parseLLMSections(raw)[0].confidence).toBe("medium");
  });
});

describe("buildLLMPrompt", () => {
  it("root cause + snippet içerir, 10 rc / 3 snippet sınırlı", () => {
    const rcs = Array.from({ length: 15 }, (_, i) => ({
      category: `cat${i}`,
      severity: "high",
      message: `m${i}`,
      file_path: `f${i}.ts`,
      evidence_count: 2,
      verified: 1,
    }));
    const snips = Array.from({ length: 5 }, (_, i) => ({ file_path: `f${i}.ts`, line: i, snippet: "x".repeat(50) }));
    const prompt = buildLLMPrompt(rcs, snips);
    expect(prompt).toContain("cat0");
    expect(prompt).toContain("cat9");
    expect(prompt).not.toContain("cat14");
  });
});

describe("explainWithLLM", () => {
  it("key yoksa hata döner (Ollama hariç)", async () => {
    const out = await explainWithLLM({ ...baseConfig, apiKey: "" }, [], []);
    expect(out.error).toContain("API key");
  });

  it("çağrı hatası error alanına yazılır, throw edilmez", async () => {
    mockFetchOnce(500, { error: { message: "boom" } });
    const out = await explainWithLLM(baseConfig, [{ category: "a", severity: "high", message: "m", file_path: "f", evidence_count: 1, verified: 1 }], []);
    expect(out.sections).toHaveLength(0);
    expect(out.error).toBeTruthy();
  });
});
