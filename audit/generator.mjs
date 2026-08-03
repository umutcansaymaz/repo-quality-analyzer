/**
 * Audit generator — creates miniature repos with known content.
 *
 * Each repo is either CLEAN (no issues) or has KNOWN issues injected.
 * The injection log is the ground truth: whatever the engine reports
 * beyond what we injected is a FALSE POSITIVE; whatever we injected but
 * the engine missed is a FALSE NEGATIVE.
 *
 * Coverage: 13 categories × 5 languages (ts/py/go/rb/java) × 6 variants
 * + boundary thresholds + cross traps.
 */

// ---------------------------------------------------------------------------
// Clean template builders (stay below engine thresholds)
// ---------------------------------------------------------------------------

const LANGS = ["ts", "py", "go", "rb", "java"];

const cleanBuilders = {
  ts(idx) {
    const lines = [`// module_${idx} — clean helpers`];
    for (let i = 0; i < 12; i++) {
      lines.push(`export function helper_${idx}_${i}(a: number, b: number): number {`);
      lines.push(`  return a + b + ${i};`);
      lines.push(`}`);
    }
    return lines.join("\n");
  },
  py(idx) {
    const lines = [`# module_${idx} — clean helpers`];
    for (let i = 0; i < 10; i++) {
      lines.push(`def helper_${idx}_${i}(a, b):`);
      lines.push(`    return a + b + ${i}`);
    }
    return lines.join("\n");
  },
  go(idx) {
    const lines = [`package main`, ``];
    for (let i = 0; i < 10; i++) {
      lines.push(`func helper_${idx}_${i}(a int, b int) int {`);
      lines.push(`\treturn a + b + ${i}`);
      lines.push(`}`);
    }
    return lines.join("\n");
  },
  rb(idx) {
    const lines = [`# module_${idx} — clean helpers`];
    for (let i = 0; i < 10; i++) {
      lines.push(`def helper_${idx}_${i}(a, b)`);
      lines.push(`  a + b + ${i}`);
      lines.push(`end`);
    }
    return lines.join("\n");
  },
  java(idx) {
    const lines = [`public class Module${idx} {`];
    for (let i = 0; i < 10; i++) {
      lines.push(`  public int helper${idx}_${i}(int a, int b) {`);
      lines.push(`    return a + b + ${i};`);
      lines.push(`  }`);
    }
    lines.push(`}`);
    return lines.join("\n");
  },
};

// File extension per language
const extOf = { ts: ".ts", py: ".py", go: ".go", rb: ".rb", java: ".java" };

function rand(n) {
  const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let out = "";
  for (let i = 0; i < n; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}

// ---------------------------------------------------------------------------
// Injectors — one per category × language. Each returns appended content.
// ---------------------------------------------------------------------------

const injectors = {
  hardcoded_secret: {
    ts: (b) => b + `\nconst apiKey = 'sk-${rand(24)}';\n`,
    py: (b) => b + `\napi_key = "sk-${rand(24)}"\n`,
    go: (b) => b + `\nvar apiKey = "sk-${rand(24)}"\n`,
    rb: (b) => b + `\napi_key = "sk-${rand(24)}"\n`,
    java: (b) => b + `\n  String apiKey = "sk-${rand(24)}";\n`,
  },
  empty_handler: {
    ts: (b) => b + `\ntry {\n  riskyCall();\n} catch {}\n`,
    py: (b) => b + `\ntry:\n    risky_call()\nexcept Exception:\n    pass\n`,
    go: (b) => b + `\nfunc swallow() {\n\t_ = recover()\n}\n`,
    rb: (b) => b + `\ndef swallow\n  begin\n    risky_call\n  rescue\n  end\nend\n`,
    java: (b) => b + `\n  public void swallow() {\n    try {\n      riskyCall();\n    } catch (Exception e) {\n    }\n  }\n`,
  },
  long_function: {
    ts: (b) => {
      const l = [`export function longFn(): number {`];
      for (let i = 0; i < 60; i++) l.push(`  const v${i} = ${i};`);
      l.push(`  return 0;`, `}`);
      return b + `\n` + l.join("\n");
    },
    py: (b) => {
      const l = [`def long_fn():`];
      for (let i = 0; i < 60; i++) l.push(`    step_${i} = work(${i})`);
      l.push(`    return 0`);
      return b + `\n` + l.join("\n");
    },
    go: (b) => {
      const l = [`func longFn() int {`];
      for (let i = 0; i < 60; i++) l.push(`\tv${i} := ${i}`);
      l.push(`\treturn 0`, `}`);
      return b + `\n` + l.join("\n");
    },
    rb: (b) => {
      const l = [`def long_fn`];
      for (let i = 0; i < 60; i++) l.push(`  step_${i} = work(${i})`);
      l.push(`  0`, `end`);
      return b + `\n` + l.join("\n");
    },
    java: (b) => {
      const l = [`  public int longFn() {`];
      for (let i = 0; i < 60; i++) l.push(`    int v${i} = ${i};`);
      l.push(`    return 0;`, `  }`);
      return b + `\n` + l.join("\n");
    },
  },
  deep_nesting: {
    ts: (b) => {
      const l = [`function deep(): void {`];
      for (let i = 0; i < 7; i++) l.push(`${"  ".repeat(i + 1)}if (a${i}) {`);
      for (let i = 7; i >= 1; i--) l.push(`${"  ".repeat(i)}}`);
      l.push(`}`);
      return b + `\n` + l.join("\n");
    },
    py: (b) => {
      const l = [`def deep():`, `    if a0:`];
      for (let i = 1; i < 7; i++) l.push(`${"    ".repeat(i + 1)}if a${i}:`);
      l.push(`${"    ".repeat(8)}pass`);
      return b + `\n` + l.join("\n");
    },
    go: (b) => {
      const l = [`func deep() {`];
      for (let i = 0; i < 7; i++) l.push(`${"\t".repeat(i + 1)}if a${i} {`);
      for (let i = 7; i >= 1; i--) l.push(`${"\t".repeat(i)}}`);
      l.push(`}`);
      return b + `\n` + l.join("\n");
    },
    rb: (b) => {
      const l = [`def deep`];
      for (let i = 0; i < 7; i++) l.push(`${"  ".repeat(i + 1)}if a${i}`);
      for (let i = 7; i >= 1; i--) l.push(`${"  ".repeat(i)}end`);
      l.push(`end`);
      return b + `\n` + l.join("\n");
    },
    java: (b) => {
      const l = [`  public void deep() {`];
      for (let i = 0; i < 7; i++) l.push(`${"  ".repeat(i + 1)}if (a${i}) {`);
      for (let i = 7; i >= 1; i--) l.push(`${"  ".repeat(i)}}`);
      l.push(`  }`);
      return b + `\n` + l.join("\n");
    },
  },
  high_complexity: {
    ts: (b) => {
      const l = [`export function complex(): number {`, `  let y = 0;`];
      for (let i = 0; i < 30; i++) l.push(`  if (x${i} > ${i}) { y += 1; }`);
      l.push(`  return y;`, `}`);
      return b + `\n` + l.join("\n");
    },
    py: (b) => {
      const l = [`def complex():`, `    y = 0`];
      for (let i = 0; i < 30; i++) l.push(`    if x${i} > ${i}:`, `        y += 1`);
      l.push(`    return y`);
      return b + `\n` + l.join("\n");
    },
    go: (b) => {
      const l = [`func complex() int {`, `\ty := 0`];
      for (let i = 0; i < 30; i++) l.push(`\tif x${i} > ${i} {`, `\t\ty += 1`, `\t}`);
      l.push(`\treturn y`, `}`);
      return b + `\n` + l.join("\n");
    },
    rb: (b) => {
      const l = [`def complex`, `  y = 0`];
      for (let i = 0; i < 30; i++) l.push(`  if x${i} > ${i}`, `    y += 1`, `  end`);
      l.push(`  y`, `end`);
      return b + `\n` + l.join("\n");
    },
    java: (b) => {
      const l = [`  public int complex() {`, `    int y = 0;`];
      for (let i = 0; i < 30; i++) l.push(`    if (x${i} > ${i}) { y += 1; }`);
      l.push(`    return y;`, `  }`);
      return b + `\n` + l.join("\n");
    },
  },
  large_file: {
    ts: (b) => {
      const l = [];
      for (let i = 0; i < 650; i++) l.push(`export const v${i}: string = "val_${i}";`);
      return b + `\n` + l.join("\n");
    },
    py: (b) => {
      const l = [];
      for (let i = 0; i < 650; i++) l.push(`v${i}: str = "val_${i}"`);
      return b + `\n` + l.join("\n");
    },
    go: (b) => {
      const l = [];
      for (let i = 0; i < 650; i++) l.push(`var v${i} = "val_${i}"`);
      return b + `\n` + l.join("\n");
    },
    rb: (b) => {
      const l = [];
      for (let i = 0; i < 650; i++) l.push(`v${i} = "val_${i}"`);
      return b + `\n` + l.join("\n");
    },
    java: (b) => {
      const l = [];
      for (let i = 0; i < 650; i++) l.push(`  String v${i} = "val_${i}";`);
      return b + `\n` + l.join("\n");
    },
  },
  command_injection: {
    ts: (b) => b + `\nconst { execSync } = require('child_process');\nexecSync(cmd);\n`,
    py: (b) => b + `\nimport os\nos.system(user_input)\n`,
    go: (b) => b + `\nimport "os/exec"\nexec.Command("sh", "-c", cmd).Run()\n`,
    rb: (b) => b + `\n\`\${cmd}\`\n`,
    java: (b) => b + `\n  Runtime.getRuntime().exec(cmd);\n`,
  },
  weak_crypto: {
    ts: (b) => b + `\nconst crypto = require('crypto');\ncrypto.createHash('md5').update(data);\n`,
    py: (b) => b + `\nimport hashlib\nh = hashlib.md5(data)\n`,
    go: (b) => b + `\nimport "crypto/md5"\n_ = md5.Sum([]byte(data))\n`,
    rb: (b) => b + `\nrequire 'digest'\nDigest::MD5.hexdigest(data)\n`,
    java: (b) => b + `\n  MessageDigest.getInstance("MD5");\n`,
  },
  // ---- New categories (Katman 2) ----
  god_class: {
    ts: (b) => {
      const l = [`export class GodService {`];
      for (let i = 0; i < 25; i++) l.push(`  method${i}() { return ${i}; }`);
      l.push(`}`);
      return b + `\n` + l.join("\n");
    },
    py: (b) => {
      const l = [`class GodService:`];
      for (let i = 0; i < 25; i++) l.push(`    def method_${i}(self):`, `        return ${i}`);
      return b + `\n` + l.join("\n");
    },
    go: (b) => {
      const l = [`type GodService struct {`, `\tvalue int`, `}`];
      for (let i = 0; i < 25; i++) l.push(`func (s *GodService) Method${i}() int {`, `\treturn ${i}`, `}`);
      return b + `\n` + l.join("\n");
    },
    rb: (b) => {
      const l = [`class GodService`];
      for (let i = 0; i < 25; i++) l.push(`  def method_${i}`, `    ${i}`, `  end`);
      l.push(`end`);
      return b + `\n` + l.join("\n");
    },
    java: (b) => {
      const l = [`  class GodService {`];
      for (let i = 0; i < 25; i++) l.push(`    public int method${i}() { return ${i}; }`);
      l.push(`  }`);
      return b + `\n` + l.join("\n");
    },
  },
  circular_dependency: {
    // Two files importing each other — handled specially in the scenario matrix
    ts: null,
    py: null,
    go: null,
    rb: null,
    java: null,
  },
  tight_coupling: {
    ts: (b) => {
      const l = [];
      for (let i = 0; i < 18; i++) l.push(`import { a${i} } from "./mod${i}";`);
      return b + `\n` + l.join("\n");
    },
    py: (b) => {
      const l = [];
      for (let i = 0; i < 18; i++) l.push(`from mod${i} import a${i}`);
      return b + `\n` + l.join("\n");
    },
    go: (b) => {
      const l = [];
      for (let i = 0; i < 18; i++) l.push(`import "mod${i}"`);
      return b + `\n` + l.join("\n");
    },
    rb: (b) => {
      const l = [];
      for (let i = 0; i < 18; i++) l.push(`require_relative 'mod${i}'`);
      return b + `\n` + l.join("\n");
    },
    java: (b) => {
      const l = [];
      for (let i = 0; i < 18; i++) l.push(`import com.example.mod${i}.A${i};`);
      return b + `\n` + l.join("\n");
    },
  },
  magic_number: {
    ts: (b) => b + `\nconst limit = 3600;\n`,
    py: (b) => b + `\nlimit = 3600\n`,
    go: (b) => b + `\nlimit := 3600\n`,
    rb: (b) => b + `\nlimit = 3600\n`,
    java: (b) => b + `\n  int limit = 3600;\n`,
  },
  todo_debt: {
    ts: (b) => b + `\n// TODO: refactor this\nconst x = 1;\n`,
    py: (b) => b + `\n# TODO: refactor this\nx = 1\n`,
    go: (b) => b + `\n// TODO: refactor this\nx := 1\n`,
    rb: (b) => b + `\n# TODO: refactor this\nx = 1\n`,
    java: (b) => b + `\n  // TODO: refactor this\n  int x = 1;\n`,
  },
  missing_tests: {
    // Files exist but NO test files — handled by scenario matrix (needs >5 files)
    ts: null,
    py: null,
    go: null,
    rb: null,
    java: null,
  },
};

// Masum komşu enjeksiyonları (FP tuzağı): benzer desen ama GERÇEK sorun değil.
const innocentTraps = {
  hardcoded_secret: {
    ts: (b) => b + `\n// örnek: const key = 'sk-${rand(20)}' (documentation only)\nconst msg = "format sk-${rand(20)} kullan";\n`,
    py: (b) => b + `\n# örnek: api_key = "sk-${rand(20)}" (belgeleme)\nmsg = "format: sk-${rand(20)}"\n`,
    go: (b) => b + `\n// örnek: var key = "sk-${rand(20)}"\nmsg := "format sk-${rand(20)}"\n`,
    rb: (b) => b + `\n# örnek: api_key = "sk-${rand(20)}"\nmsg = "format sk-${rand(20)}"\n`,
    java: (b) => b + `\n  // örnek: String key = "sk-${rand(20)}"\n  String msg = "format sk-${rand(20)}";\n`,
  },
  command_injection: {
    ts: (b) => b + `\n// execSync(cmd) aslinda burada yorum\nconst doc = "execSync(something) is used";\n`,
    py: (b) => b + `\n# os.system(cmd) yorumda\nmsg = "os.system(bad)"\n`,
    go: (b) => b + `\n// exec.Command yorumda\nmsg := "exec.Command(x)"\n`,
    rb: (b) => b + `\n# ` + "`cmd`" + ` yorumda\nmsg = "` + "`echo`" + `"\n`,
    java: (b) => b + `\n  // Runtime.exec yorumda\n  String msg = "Runtime.exec(x)";\n`,
  },
  weak_crypto: {
    ts: (b) => b + `\n// hashlib md5 kullanimi ornek\nconst msg = "createHash('md5') example";\n`,
    py: (b) => b + `\n# md5 ornegi\nmsg = "hashlib.md5(x)"\n`,
    go: (b) => b + `\n// md5 ornegi\nmsg := "md5.Sum(x)"\n`,
    rb: (b) => b + `\n# md5 ornegi\nmsg = "Digest::MD5(x)"\n`,
    java: (b) => b + `\n  // md5 ornegi\n  String msg = "MessageDigest.getInstance(\\\"MD5\\\")";\n`,
  },
};

// ---------------------------------------------------------------------------
// Boundary threshold variants — one per threshold, just below/above
// ---------------------------------------------------------------------------

function boundaryRepos() {
  const repos = [];
  const push = (name, expected, files) => repos.push({ name, expected, files });

  // long_function: threshold 50 — 49 lines (no) vs 51 (yes)
  const longBody = (n) => {
    const l = [`export function f(): number {`];
    for (let i = 0; i < n; i++) l.push(`  const v${i} = ${i};`);
    l.push(`  return 0;`, `}`);
    return l.join("\n");
  };
  push("b-long-under", [], [{ path: "src/main.ts", content: longBody(49) }]);
  push("b-long-over", ["long_function"], [{ path: "src/main.ts", content: longBody(51) }]);

  // large_file: threshold 600 — 599 (no) vs 601 (yes)
  const bigBody = (n) => {
    const l = [];
    for (let i = 0; i < n; i++) l.push(`export const v${i}: string = "val_${i}";`);
    return l.join("\n");
  };
  push("b-big-under", [], [{ path: "src/main.ts", content: bigBody(599) }]);
  push("b-big-over", ["large_file"], [{ path: "src/main.ts", content: bigBody(601) }]);

  // high_complexity: threshold 25 — 24 (no) vs 26 (yes)
  const complexBody = (n) => {
    const l = [`export function f(): number {`, `  let y = 0;`];
    for (let i = 0; i < n; i++) l.push(`  if (x${i} > ${i}) { y += 1; }`);
    l.push(`  return y;`, `}`);
    return l.join("\n");
  };
  push("b-complex-under", [], [{ path: "src/main.ts", content: complexBody(24) }]);
  push("b-complex-over", ["high_complexity"], [{ path: "src/main.ts", content: complexBody(26) }]);

  // deep_nesting: engine counts function body as level 1 → 6 ifs = 7 levels (≥6)
  // → under: 4 ifs (5 levels, clean) vs over: 6 ifs (7 levels, finding)
  const deepBody = (n) => {
    const l = [`function f(): void {`];
    for (let i = 0; i < n; i++) l.push(`${"  ".repeat(i + 1)}if (a${i}) {`);
    for (let i = n; i >= 1; i--) l.push(`${"  ".repeat(i)}}`);
    l.push(`}`);
    return l.join("\n");
  };
  push("b-depth-under", [], [{ path: "src/main.ts", content: deepBody(4) }]);
  push("b-depth-over", ["deep_nesting"], [{ path: "src/main.ts", content: deepBody(6) }]);

  // god_class: threshold 20 — 19 (no) vs 21 (yes)
  const godBody = (n) => {
    const l = [`export class S {`];
    for (let i = 0; i < n; i++) l.push(`  m${i}() { return ${i}; }`);
    l.push(`}`);
    return l.join("\n");
  };
  push("b-god-under", [], [{ path: "src/main.ts", content: godBody(19) }]);
  push("b-god-over", ["god_class"], [{ path: "src/main.ts", content: godBody(21) }]);

  // tight_coupling: threshold 15 — 14 (no) vs 16 (yes)
  const couplingBody = (n) => {
    const l = [];
    for (let i = 0; i < n; i++) l.push(`import { a${i} } from "./mod${i}";`);
    l.push(`export const hub = 1;`);
    return l.join("\n");
  };
  const mods = (n) => Array.from({ length: n }, (_, i) => ({ path: `src/mod${i}.ts`, content: `export const a${i} = ${i};\n` }));
  // 15+ dosyalık repo'da test dosyası yok → missing_tests de beklenir
  push("b-coupling-under", ["missing_tests"], [{ path: "src/hub.ts", content: couplingBody(14) }, ...mods(14)]);
  push("b-coupling-over", ["tight_coupling", "missing_tests"], [{ path: "src/hub.ts", content: couplingBody(16) }, ...mods(16)]);

  return repos;
}

// ---------------------------------------------------------------------------
// Cross traps — benign lookalikes that must NOT trigger findings
// ---------------------------------------------------------------------------

function trapRepos() {
  const repos = [];
  const push = (name, expected, files) => repos.push({ name, expected, files });

  push("trap-comment-secret", [], [
    { path: "src/main.ts", content: `// secret: sk-${rand(24)} — documentation only\nconst x = 1;\n` },
  ]);
  push("trap-string-secret", [], [
    { path: "src/main.ts", content: `const doc = "password=super_secret_value_1234567890";\nconst x = 1;\n` },
  ]);
  push("trap-regex-crypto", [], [
    { path: "src/main.ts", content: `const re = /\\bhashlib\\.md5\\(/;\nconst x = 1;\n` },
  ]);
  push("trap-task-not-secret", [], [
    { path: "src/main.ts", content: `const taskId = "task-${rand(20)}";\nconst x = 1;\n` },
  ]);
  push("trap-generated-min", [], [
    { path: "dist/app.min.js", content: `const k='sk-${rand(24)}';function x(){}\n` },
  ]);
  push("trap-encrypted", [], [
    { path: "src/data/secret.encrypted.json", content: `{"iv":"abc","data":"${rand(60)}"}\n` },
  ]);
  push("trap-backup-file", [], [
    { path: "src/App.backup.jsx", content: `const k='sk-${rand(24)}';\n` },
  ]);
  push("trap-import-comment", [], [
    { path: "src/a.ts", content: `// import { b } from "./b";\nconst x = 1;\n` },
    { path: "src/b.ts", content: `import { a } from "./a";\nconst y = 2;\n` },
  ]);

  return repos;
}

// ---------------------------------------------------------------------------
// Scenario matrix — 13 categories × languages × 6 variants
// ---------------------------------------------------------------------------

export function generateRepos() {
  const repos = [];
  const categories = Object.keys(injectors).filter((c) => injectors[c].ts !== null); // skip specials

  for (const cat of categories) {
    for (const lang of LANGS) {
      const ext = extOf[lang];
      const clean = cleanBuilders[lang];
      const inj = injectors[cat][lang];
      // tight_coupling enjektörü ./modN dosyalarını import eder — motor yalnızca
      // ÇÖZÜMLENEN importları sayar, o yüzden mod dosyaları gerçekten var olmalı.
      // 18 mod + main = 19 dosya, test dosyası yok → missing_tests de doğal beklenir.
      const couplingMods = cat === "tight_coupling"
        ? Array.from({ length: 18 }, (_, i) => {
            // Java: import com.example.modN.A0 → paket yapısı src/com/example/modN/
            if (lang === "java") {
              return {
                path: `src/com/example/mod${i}/A${i}.java`,
                content: `package com.example.mod${i};\npublic class A${i} {\n  public int value = ${i};\n}\n`,
              };
            }
            return { path: `src/mod${i}${ext}`, content: cleanBuilders[lang](100 + i) };
          })
        : [];
      const withMt = (cats) => (cat === "tight_coupling" ? [...cats, "missing_tests"] : cats);

      // Variant 1: CLEAN — must produce ZERO findings
      repos.push({
        name: `${cat}-${lang}-clean`,
        expected: [],
        files: [{ path: `src/main${ext}`, content: clean(0) }],
      });

      // Variant 2: single issue
      repos.push({
        name: `${cat}-${lang}-single`,
        // 30 dallı fonksiyon Python/Go/Ruby'de satır başı if → uzun da olur
        expected: withMt(cat === "high_complexity" && lang !== "ts" && lang !== "java" ? [cat, "long_function"] : [cat]),
        files: [{ path: `src/main${ext}`, content: inj(clean(1)) }, ...couplingMods],
      });

      // Variant 3: issue + large_file in another file
      repos.push({
        name: `${cat}-${lang}-double`,
        // high_complexity enjeksiyonu Py/Go/Rb'de 60+ satır → long_function doğal
        expected: withMt(cat === "large_file" ? ["large_file"]
          : cat === "high_complexity" && lang !== "ts" && lang !== "java"
            ? [cat, "large_file", "long_function"]
            : [cat, "large_file"]),
        files: [
          { path: `src/main${ext}`, content: inj(clean(2)) },
          { path: `src/big${ext}`, content: injectors.large_file[lang](clean(2)) },
          ...couplingMods,
        ],
      });

      // Variant 4: issue + innocent neighbour (FP trap)
      repos.push({
        name: `${cat}-${lang}-neighbour`,
        expected: withMt(cat === "high_complexity" && lang !== "ts" && lang !== "java" ? [cat, "long_function"] : [cat]),
        files: [
          { path: `src/main${ext}`, content: inj(clean(3)) },
          { path: `src/docs${ext}`, content: (innocentTraps[cat]?.[lang] || ((b) => b))(clean(3)) },
          ...couplingMods,
        ],
      });

      // Variant 5: issue in both languages
      repos.push({
        name: `${cat}-${lang}-multi`,
        // TS/Java 30 if tek satırda (30 satır) → uzun değil; Py/Go/Rb 2 satır/if (60+)
        expected: withMt(cat === "high_complexity" && lang !== "ts" && lang !== "java" ? [cat, "long_function"] : [cat]),
        files: [
          { path: `src/main${ext}`, content: inj(clean(4)) },
          { path: `src/other${ext}`, content: inj(clean(4)) },
          ...couplingMods,
        ],
      });

      // Variant 6: issue + TODO + magic number (noise must not shadow)
      repos.push({
        name: `${cat}-${lang}-noise`,
        expected: withMt(cat === "high_complexity" && lang !== "ts" && lang !== "java" ? [cat, "long_function", "todo_debt", "magic_number"] : [cat, "todo_debt", "magic_number"]),
        files: [
          { path: `src/main${ext}`, content: inj(clean(5)) + `\n// TODO: refactor\nconst limit = 3600;\n` },
          ...couplingMods,
        ],
      });
    }
  }

  // ---- Circular dependency (two-file scenario) ----
  for (const lang of ["ts", "py", "go", "rb", "java"]) {
    const ext = extOf[lang];
    const pair = circularPair(lang);
    // Java import "com.b.B" → dosya paket yolunda: src/com/b/B.java
    const aPath = lang === "java" ? `src/com/a/A.java` : `src/a${ext}`;
    const bPath = lang === "java" ? `src/com/b/B.java` : `src/b${ext}`;
    repos.push({
      name: `circular_dependency-${lang}-single`,
      expected: ["circular_dependency"],
      files: [
        { path: aPath, content: pair.a },
        { path: bPath, content: pair.b },
      ],
    });
    repos.push({
      name: `circular_dependency-${lang}-clean`,
      expected: [],
      files: [{ path: `src/a${ext}`, content: cleanBuilders[lang](0) }],
    });
  }

  // ---- Missing tests (repo without any test file, >5 source files) ----
  for (const lang of ["ts", "py", "go", "rb", "java"]) {
    const ext = extOf[lang];
    const files = [];
    for (let i = 0; i < 8; i++) files.push({ path: `src/mod${i}${ext}`, content: cleanBuilders[lang](i) });
    repos.push({
      name: `missing_tests-${lang}-single`,
      expected: ["missing_tests"],
      files,
    });
  }

  // ---- Boundary thresholds ----
  repos.push(...boundaryRepos());

  // ---- Cross traps ----
  repos.push(...trapRepos());

  return repos;
}

// Circular dependency pair builders
function circularPair(lang) {
  switch (lang) {
    case "ts":
      return { a: `import { b } from "./b";\nexport const a = b;\n`, b: `import { a } from "./a";\nexport const b = a;\n` };
    case "py":
      return { a: `from b import x\nx = 1\n`, b: `from a import y\ny = 2\n` };
    case "go":
      return { a: `package a\nimport "b"\nvar A = b.B\n`, b: `package b\nimport "a"\nvar B = a.A\n` };
    case "rb":
      return { a: `require_relative 'b'\nA = B\n`, b: `require_relative 'a'\nB = A\n` };
    case "java":
      return {
        a: `import com.b.B;\npublic class A { B b; }\n`,
        b: `import com.a.A;\npublic class B { A a; }\n`,
      };
  }
}
