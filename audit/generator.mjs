/**
 * Audit generator — creates miniature repos with known content.
 *
 * Each repo is either CLEAN (no issues) or has KNOWN issues injected.
 * The injection log is the ground truth: whatever the engine reports
 * beyond what we injected is a FALSE POSITIVE; whatever we injected but
 * the engine missed is a FALSE NEGATIVE.
 *
 * No manual benchmark authoring — everything is generated here.
 */

// ---------------------------------------------------------------------------
// Clean template builders (stay below engine thresholds)
// ---------------------------------------------------------------------------

/** Clean TS file: 20 small functions, no issues. */
function cleanTsFile(idx) {
  const lines = [`// module_${idx} — clean helpers`];
  for (let i = 0; i < 20; i++) {
    lines.push(`export function helper_${idx}_${i}(a: number, b: number): number {`);
    lines.push(`  return a + b + ${i};`);
    lines.push(`}`);
  }
  return lines.join("\n");
}

/** Clean Python file: 15 small functions, 1 import. */
function cleanPyFile(idx) {
  const lines = [`# module_${idx} — clean helpers`, `import math`];
  for (let i = 0; i < 15; i++) {
    lines.push(`def helper_${idx}_${i}(a, b):`);
    lines.push(`    return a + b + ${i}`);
  }
  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Injectors — one per category. Each returns { content, note }.
// ---------------------------------------------------------------------------

const injectors = {
  hardcoded_secret: {
    ts: (base) => base + `\nconst apiKey = 'sk-${rand(24)}';\n`,
    py: (base) => base + `\napi_key = "sk-${rand(24)}"\n`,
  },
  empty_handler: {
    ts: (base) => base + `\ntry {\n  riskyCall();\n} catch {}\n`,
    py: (base) => base + `\ntry:\n    risky_call()\nexcept Exception:\n    pass\n`,
  },
  long_function: {
    ts: (base) => {
      const lines = [`export function longFn(): number {`];
      for (let i = 0; i < 60; i++) lines.push(`  const v${i} = ${i};`);
      lines.push(`  return 0;`, `}`);
      return base + `\n` + lines.join("\n");
    },
    py: (base) => {
      const lines = [`def long_fn():`];
      for (let i = 0; i < 60; i++) lines.push(`    step_${i} = work(${i})`);
      lines.push(`    return 0`);
      return base + `\n` + lines.join("\n");
    },
  },
  deep_nesting: {
    ts: (base) => {
      const lines = [`function deep(): void {`];
      for (let i = 0; i < 7; i++) lines.push(`${"  ".repeat(i + 1)}if (a${i}) {`);
      for (let i = 7; i >= 1; i--) lines.push(`${"  ".repeat(i)}}`);
      lines.push(`}`);
      return base + `\n` + lines.join("\n");
    },
    py: (base) => {
      const lines = [`def deep():`, `    if a0:`];
      for (let i = 1; i < 7; i++) lines.push(`${"    ".repeat(i + 1)}if a${i}:`);
      lines.push(`${"    ".repeat(8)}pass`);
      return base + `\n` + lines.join("\n");
    },
  },
  high_complexity: {
    ts: (base) => {
      const lines = [`export function complex(): number {`, `  let y = 0;`];
      for (let i = 0; i < 30; i++) lines.push(`  if (x${i} > ${i}) { y += 1; }`);
      lines.push(`  return y;`, `}`);
      return base + `\n` + lines.join("\n");
    },
    py: (base) => {
      const lines = [`def complex():`, `    y = 0`];
      for (let i = 0; i < 30; i++) lines.push(`    if x${i} > ${i}:`, `        y += 1`);
      lines.push(`    return y`);
      return base + `\n` + lines.join("\n");
    },
  },
  large_file: {
    ts: (base) => {
      const lines = [];
      for (let i = 0; i < 650; i++) lines.push(`export const v${i}: string = "val_${i}";`);
      return base + `\n` + lines.join("\n");
    },
    py: (base) => {
      const lines = [];
      for (let i = 0; i < 650; i++) lines.push(`v${i}: str = "val_${i}"`);
      return base + `\n` + lines.join("\n");
    },
  },
  command_injection: {
    ts: (base) => base + `\nconst { execSync } = require('child_process');\nexecSync(cmd);\n`,
    py: (base) => base + `\nimport os\nos.system(user_input)\n`,
  },
  weak_crypto: {
    ts: (base) => base + `\nconst crypto = require('crypto');\ncrypto.createHash('md5').update(data);\n`,
    py: (base) => base + `\nimport hashlib\nh = hashlib.md5(data)\n`,
  },
};

// Masum komşu enjeksiyonları (FP tuzağı): benzer desen ama GERÇEK sorun değil.
const innocentTraps = {
  hardcoded_secret: {
    ts: (base) => base + `\n// örnek: const key = 'sk-${rand(20)}' (documentation only)\nconst msg = "format sk-${rand(20)} kullan";\n`,
    py: (base) => base + `\n# örnek: api_key = "sk-${rand(20)}" (belgeleme)\nmsg = "format: sk-${rand(20)}"\n`,
  },
  command_injection: {
    ts: (base) => base + `\n// execSync(cmd) aslinda burada yorum\nconst doc = "execSync(something) is used";\n`,
    py: (base) => base + `\n# os.system(cmd) yorumda\nmsg = "os.system(bad)"\n`,
  },
};

function rand(n) {
  const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let out = "";
  for (let i = 0; i < n; i++) out += chars[Math.floor(Math.random() * chars.length)];
  return out;
}

// ---------------------------------------------------------------------------
// Scenario matrix — 8 categories × 6 variants
// ---------------------------------------------------------------------------

export function generateRepos() {
  const repos = [];
  let repoIdx = 0;
  const categories = Object.keys(injectors);

  for (const cat of categories) {
    // Variant 1: CLEAN — must produce ZERO findings
    repos.push({
      name: `${cat}-clean`,
      expected: [],
      files: [
        { path: "src/main.ts", content: cleanTsFile(0) },
        { path: "src/util.py", content: cleanPyFile(0) },
      ],
    });

    // Variant 2: single issue
    repos.push({
      name: `${cat}-single`,
      expected: [cat],
      files: [
        { path: "src/main.ts", content: injectors[cat].ts(cleanTsFile(1)) },
        { path: "src/util.py", content: cleanPyFile(1) },
      ],
    });

    // Variant 3: two issues (same category in another file + a second category)
    repos.push({
      name: `${cat}-double`,
      expected: [cat, "large_file"],
      files: [
        { path: "src/main.ts", content: injectors[cat].ts(cleanTsFile(2)) },
        { path: "src/big.py", content: injectors.large_file.py(cleanPyFile(2)) },
      ],
    });

    // Variant 4: issue + innocent neighbour (FP trap — comment/string mention)
    repos.push({
      name: `${cat}-neighbour`,
      expected: [cat],
      files: [
        { path: "src/main.ts", content: injectors[cat].ts(cleanTsFile(3)) },
        { path: "src/docs.ts", content: (innocentTraps[cat]?.ts || ((b) => b))(cleanTsFile(3)) },
      ],
    });

    // Variant 5: issue + same category in both files
    repos.push({
      name: `${cat}-multi`,
      // 30 dallı fonksiyon doğal olarak uzun da olur → long_function beklenir
      expected: cat === "high_complexity" ? [cat, "long_function"] : [cat],
      files: [
        { path: "src/main.ts", content: injectors[cat].ts(cleanTsFile(4)) },
        { path: "src/other.py", content: injectors[cat].py(cleanPyFile(4)) },
      ],
    });

    // Variant 6: issue + TODO + magic number (low-severity noise — should not shadow)
    repos.push({
      name: `${cat}-noise`,
      expected: [cat, "todo_debt", "magic_number"],
      files: [
        { path: "src/main.ts", content: injectors[cat].ts(cleanTsFile(5)) + `\n// TODO: refactor this\nconst limit = 3600;\n` },
        { path: "src/util.py", content: cleanPyFile(5) },
      ],
    });
    repoIdx += 6;
  }

  return repos;
}
