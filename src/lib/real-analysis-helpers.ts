/**
 * Real Analysis Helpers — Language-aware static analysis primitives.
 *
 * Offline (no API) static code analysis. Used by real-analysis-engine.ts.
 *
 * Design:
 *  - All functions are pure — they take file content + language, return metrics.
 *  - Language-aware: Python (indent), C-family ({}), Ruby (def...end), etc.
 *  - Deterministic: same input → same output.
 *  - Robust: never throws; returns zeros on parse errors.
 */

export type SupportedLanguage =
  | "Python" | "TypeScript" | "JavaScript" | "Java" | "Go"
  | "Rust" | "C#" | "Kotlin" | "PHP" | "Ruby" | "Swift"
  | "Scala" | "C";


/** Per-language configuration: extensions, comment-styles, scope rules. */
interface LangConfig {
  extensions: string[];
  lineComments: string[];
  blockCommentStart: string | null;
  blockCommentEnd: string | null;
  /** "brace" for C-family, "indent" for Python, "keyword_end" for Ruby. */
  scopeStyle: "brace" | "indent" | "keyword_end";
  classKeywords: string[];        // e.g. ["class", "struct", "interface"]
  functionKeywords: string[];     // e.g. ["def", "function", "func", "fn"]
  importRegex: RegExp;             // First capture group = imported path
  modifierKeywords: string[];      // keywords that may prefix a function but are NOT functions
}

const CONFIGS: Record<SupportedLanguage, LangConfig> = {
  Python: {
    extensions: [".py"],
    lineComments: ["#"],
    blockCommentStart: null,
    blockCommentEnd: null,
    scopeStyle: "indent",
    classKeywords: ["class"],
    functionKeywords: ["def"],
    modifierKeywords: ["async"],
    importRegex: /^\s*(?:from\s+(\S+)\s+import|import\s+(\S+))/m,
  },
  TypeScript: {
    extensions: [".ts", ".tsx"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["class", "interface", "enum", "namespace", "object"],
    functionKeywords: ["function", "fn"],
    modifierKeywords: ["async", "static", "public", "private", "protected", "get", "set", "export", "default"],
    importRegex:
      /(?:^|\n)\s*(?:import\s+(?:.+\s+from\s+)?[\"']([^\"']+)[\"']|import\s+(\w+))|\brequire\s*\(\s*[\"']([^\"']+)[\"']\s*\)/,
  },
  JavaScript: {
    extensions: [".js", ".jsx"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["class", "interface", "enum", "namespace", "object"],
    functionKeywords: ["function", "fn"],
    modifierKeywords: ["async", "static", "public", "private", "protected", "get", "set", "export", "default"],
    importRegex:
      /(?:^|\n)\s*(?:import\s+(?:.+\s+from\s+)?[\"']([^\"']+)[\"']|import\s+(\w+))|\brequire\s*\(\s*[\"']([^\"']+)[\"']\s*\)/,
  },
  Java: {
    extensions: [".java"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["class", "interface", "enum"],
    functionKeywords: [],
    modifierKeywords: ["public", "private", "protected", "static", "final", "abstract", "synchronized", "native", "default"],
    importRegex: /^\s*import\s+(?:static\s+)?([^;]+)/m,
  },
  Go: {
    extensions: [".go"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["struct", "interface"],
    functionKeywords: ["func"],
    modifierKeywords: [],
    importRegex: /^\s*import\s+(?:\(\s*([\s\S]*?)\s*\)|[\"']([^\"']+)[\"'])/m,
  },
  Rust: {
    extensions: [".rs"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["struct", "enum", "trait"],
    functionKeywords: ["fn"],
    modifierKeywords: ["pub", "async", "unsafe", "extern"],
    importRegex: /^\s*use\s+([^;]+)/m,
  },
  "C#": {
    extensions: [".cs"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["class", "interface", "struct", "enum"],
    functionKeywords: [],
    modifierKeywords: ["public", "private", "protected", "internal", "static", "virtual", "override", "abstract", "async", "unsafe"],
    importRegex: /^\s*using\s+([^;]+)/m,
  },
  Kotlin: {
    extensions: [".kt"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["class", "interface", "object", "enum", "data"],
    functionKeywords: ["fun"],
    modifierKeywords: ["public", "private", "protected", "internal", "suspend", "inline", "operator", "infix", "tailrec"],
    importRegex: /^\s*import\s+([^;]+)/m,
  },
  PHP: {
    extensions: [".php"],
    lineComments: ["//", "#"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["class", "interface", "trait"],
    functionKeywords: ["function"],
    modifierKeywords: ["public", "private", "protected", "static", "final", "abstract", "async"],
    importRegex: /^\s*(?:use|require|include)(_once)?\s+([^;]+)/m,
  },
  Ruby: {
    extensions: [".rb"],
    lineComments: ["#"],
    blockCommentStart: null,
    blockCommentEnd: null,
    scopeStyle: "keyword_end",
    classKeywords: ["class", "module"],
    functionKeywords: ["def"],
    modifierKeywords: [],
    importRegex: /^\s*(?:require|require_relative|load)\s+[\"']([^\"']+)[\"']/m,
  },
  Swift: {
    extensions: [".swift"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["class", "struct", "enum", "protocol", "actor"],
    functionKeywords: ["func"],
    modifierKeywords: ["public", "private", "internal", "fileprivate", "static", "final", "override", "mutating", "async", "throws"],
    importRegex: /^\s*import\s+(\w+)/m,
  },
  Scala: {
    extensions: [".scala"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["class", "object", "trait", "enum"],
    functionKeywords: ["def"],
    modifierKeywords: ["private", "protected", "final", "override", "abstract", "implicit", "inline"],
    importRegex: /^\s*import\s+([^;]+)/m,
  },
  C: {
    extensions: [".c", ".h"],
    lineComments: ["//"],
    blockCommentStart: "/*",
    blockCommentEnd: "*/",
    scopeStyle: "brace",
    classKeywords: ["struct", "union", "enum"],
    functionKeywords: [],
    modifierKeywords: ["static", "inline", "extern", "const", "register", "volatile"],
    importRegex: /^\s*#include\s+[\"<]([^\">]+)[\">]/m,
  },
};

export function getLangConfig(lang: string): LangConfig | null {
  return CONFIGS[lang as SupportedLanguage] || null;
}

export function getExtensions(lang: string): string[] {
  return CONFIGS[lang as SupportedLanguage]?.extensions || [".py"];
}

// ===================== STRIP COMMENTS / STRINGS =====================

/** Strips comments and string/char literals — preserves LOC but makes token analysis safe. */
function stripCommentsAndStrings(content: string, cfg: LangConfig): string {
  let result = "";
  let i = 0;
  const n = content.length;
  let line = 1;

  while (i < n) {
    const ch = content[i];
    const nx = content[i + 1];

    // Newline preserved (keeps line numbering for scope analysis)
    if (ch === "\n") {
      result += "\n";
      line++;
      i++;
      continue;
    }

    // Line comment
    let hitLineComment = false;
    for (const lc of cfg.lineComments) {
      if (content.startsWith(lc, i)) {
        // Skip to end of line
        const eol = content.indexOf("\n", i);
        result += "\n";
        i = eol === -1 ? n : eol;
        hitLineComment = true;
        break;
      }
    }
    if (hitLineComment) continue;

    // Block comment
    if (cfg.blockCommentStart && cfg.blockCommentEnd && content.startsWith(cfg.blockCommentStart, i)) {
      const end = content.indexOf(cfg.blockCommentEnd, i + cfg.blockCommentStart.length);
      const stop = end === -1 ? n : end + cfg.blockCommentEnd.length;
      // Preserve newlines inside comment for line numbering
      for (let k = i; k < stop; k++) if (content[k] === "\n") result += "\n";
      i = stop;
      continue;
    }

    // String literals (double or single quote) — common to most langs
    if (ch === "\"" || ch === "'") {
      // Skip to closing quote, respecting backslash escapes
      let j = i + 1;
      while (j < n) {
        if (content[j] === "\\") { j += 2; continue; }
        if (content[j] === ch) { j++; break; }
        if (content[j] === "\n") { result += "\n"; }
        j++;
      }
      result += " "; // placeholder so token boundaries remain
      i = j;
      continue;
    }

    // Template strings (backtick) — TS/JS
    if (ch === "`") {
      let j = i + 1;
      while (j < n) {
        if (content[j] === "\\") { j += 2; continue; }
        if (content[j] === "`") { j++; break; }
        if (content[j] === "\n") { result += "\n"; }
        j++;
      }
      result += " ";
      i = j;
      continue;
    }

    result += ch;
    i++;
  }

  return result;
}

// ===================== LOC =====================

/** Counts physical lines of code (any line with non-whitespace after stripping comments). */
export function countLoc(content: string, lang: string): number {
  const cfg = getLangConfig(lang);
  if (!cfg) return 0;
  const cleaned = stripCommentsAndStrings(content, cfg);
  let loc = 0;
  for (const line of cleaned.split("\n")) {
    if (line.trim().length > 0) loc++;
  }
  return loc;
}

/** Counts total lines including blanks/comments. */
export function countTotalLines(content: string): number {
  return content.split("\n").length;
}

// ===================== CLASS & FUNCTION DETECTION =====================

interface Match {
  startIdx: number;
  startLine: number;
}

/** Find start indices of all class/interface/struct/etc declarations. */
function findClassDeclarations(cleaned: string, cfg: LangConfig): Match[] {
  const results: Match[] = [];
  if (cfg.classKeywords.length === 0) return results;

  // \b ensures we don't match substrings; \s+ ensures it's a declaration, not "classVar".
  const pattern = new RegExp(
    `\\b(?:${cfg.classKeywords.join("|")})\\s+[A-Za-z_][A-Za-z0-9_]*`,
    "g"
  );

  let m: RegExpExecArray | null;
  let offset = 0;
  while ((m = pattern.exec(cleaned)) !== null) {
    // Compute line number by counting newlines before this index.
    const startIdx = m.index;
    let line = 1;
    for (let k = 0; k < startIdx; k++) if (cleaned[k] === "\n") line++;
    results.push({ startIdx, startLine: line });
    if (pattern.lastIndex === m.index) pattern.lastIndex++;
    offset++;
  }
  void offset;
  return results;
}

/** Find start indices of all function/method declarations, after handling modifier keywords. */
function findFunctionDeclarations(cleaned: string, cfg: LangConfig): Match[] {
  const results: Match[] = [];
  if (cfg.functionKeywords.length === 0) {
    // For Java/C#/C etc., functions are recognized by a "type name (args)" or "name (args)" pattern
    // without a class keyword. To keep it robust + simple, we use a heuristic:
    //   identifier followed by parens, preceded by a modifier or return-type word and not by a `.` or `new`.
    // Get class declarations first so we don't double-count constructors/init blocks.
    const classMatches = findClassDeclarations(cleaned, cfg);

    // Pattern: word(s) space identifier(...). Replace constructor bodies.
    // Use a tolerant regex: capture words before `(` and after a class keyword boundary.
    const pattern = /\b([A-Za-z_][A-Za-z0-9_<>,\s\*&]*?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(/g;
    let m: RegExpExecArray | null;
    while ((m = pattern.exec(cleaned)) !== null) {
      const startIdx = m.index;
      // Skip if previous non-space char is `.` (method call) or `new` (constructor call).
      let k = startIdx - 1;
      while (k >= 0 && /\s/.test(cleaned[k])) k--;
      if (k >= 0 && (cleaned[k] === "." || cleaned[k] === ">")) continue;
      // Skip if it looks like a control-flow keyword.
      const retType = m[1].trim();
      if (["if", "for", "while", "switch", "catch", "return", "sizeof", "typeof", "using", "lock", "fixed", "checked", "unchecked"].includes(retType)) continue;

      // Skip if this index is inside a class declaration match (overlap).
      const insideClass = classMatches.some((cm) => cm.startIdx === startIdx);
      if (insideClass) continue;

      let line = 1;
      for (let k2 = 0; k2 < startIdx; k2++) if (cleaned[k2] === "\n") line++;
      results.push({ startIdx, startLine: line });
      if (pattern.lastIndex === m.index) pattern.lastIndex++;
    }

    // For C-family brace languages that use function keywords (TS/JS/PHP),
    // also collect class method definitions: `identifier(...)` followed by `{`
    // inside a class scope but without `function` keyword (TS shorthand methods).
    if (cfg.scopeStyle === "brace" && cfg.functionKeywords.length > 0) {
      appendClassMethods(cleaned, cfg, classMatches, results);
    }

    return results;
  }

  // Languages with explicit function keywords (def/function/fun/fn/func).
  // We must NOT match `modifierKeywords` alone — only the function keyword.
  const pattern = new RegExp(
    `\\b(${cfg.functionKeywords.join("|")})\\s+([A-Za-z_][A-Za-z0-9_]*)`,
    "g"
  );
  let m: RegExpExecArray | null;
  while ((m = pattern.exec(cleaned)) !== null) {
    const startIdx = m.index;
    let line = 1;
    for (let k = 0; k < startIdx; k++) if (cleaned[k] === "\n") line++;
    results.push({ startIdx, startLine: line });
    if (pattern.lastIndex === m.index) pattern.lastIndex++;
  }

  // Also collect class method definitions for TS/JS/PHP (no `function` keyword):
  // `methodName(args) { ... }` inside class bodies.
  if (cfg.scopeStyle === "brace") {
    const classMatches = findClassDeclarations(cleaned, cfg);
    appendClassMethods(cleaned, cfg, classMatches, results);
  }

  return results;
}

/** Append class-body method definitions (TS/JS/PHP/C# shorthand) to results. */
function appendClassMethods(
  cleaned: string,
  cfg: LangConfig,
  classMatches: Match[],
  results: Match[]
): void {
  if (cfg.scopeStyle !== "brace") return;
  // For each class scope, find `identifier(...)` followed by `{`, but exclude:
  //  - assignments `=` (arrow fn / function expr)
  //  - colon `:` (TS type annotation)
  //  - arrow functions `=>`
  //  - calls preceded by `.`
  //  - control-flow keywords
  for (const cm of classMatches) {
    const openIdx = cleaned.indexOf("{", cm.startIdx);
    if (openIdx === -1) continue;
    // Find matching close brace of class body
    let depth = 1;
    let i = openIdx + 1;
    let closeIdx = -1;
    while (i < cleaned.length && depth > 0) {
      if (cleaned[i] === "{") depth++;
      else if (cleaned[i] === "}") depth--;
      if (depth === 0) { closeIdx = i; break; }
      i++;
    }
    if (closeIdx === -1) continue;

    // Scan inside [openIdx+1, closeIdx) for method declarations:
    // Pattern line-anchored: ^\s*(modifiers)*\s*name\s*\([^)]*\)\s*(:\s*[A-Za-z<>|]+)?\s*{
    // We process line by line, since class methods are typically on their own line.
    const body = cleaned.slice(openIdx + 1, closeIdx);
    const lines = body.split("\n");
    let bodyIdx = openIdx + 1;
    for (const line of lines) {
      // Skip lines that begin with comment-only or empty (already stripped, but safety).
      const trimmed = line.trim();
      if (trimmed.length === 0) { bodyIdx += line.length + 1; continue; }

      // Method declaration heuristic: starts with optional modifiers, then identifier(args), then optional `: retType`, then `{`.
      // Match must NOT have `=` (assignment) or `=>` (arrow) or `;` (call statement) before the `(`.
      const m = new RegExp(
        `^\\s*(?:${cfg.modifierKeywords.join("|")})?\\s*([A-Za-z_][A-Za-z0-9_]*)\\s*\\(([^)]*)\\)(?:\\s*:\\s*[A-Za-z][\\w<>\\[\\]|,\\s]*)?\\s*\\{`
      ).exec(line);
      if (m) {
        const name = m[1];
        if (["if", "for", "while", "switch", "catch", "return", "function", "constructor", "get", "set"]
          .includes(name) && name !== "constructor") {
          bodyIdx += line.length + 1;
          continue;
        }
        // Compute absolute idx of the method name (approximate by bodyIdx + position of name in line).
        const namePos = line.indexOf(name);
        const absIdx = bodyIdx + Math.max(0, namePos);
        // Avoid duplicate with already-recorded function declarations:
        const dup = results.some((r) => Math.abs(r.startIdx - absIdx) < 5);
        if (!dup) {
          let lineNo = 1;
          for (let k = 0; k < absIdx; k++) if (cleaned[k] === "\n") lineNo++;
          results.push({ startIdx: absIdx, startLine: lineNo });
        }
      }
      bodyIdx += line.length + 1;
    }
  }
}

// ===================== SCOPE EXTRACTION =====================

/** Extracts scope body length (in LOC) starting after a declaration. Handles brace / indent / keyword_end. */
function extractScopeLength(cleaned: string, declIdx: number, lang: string): number {
  const cfg = getLangConfig(lang)!; // Caller guarantees LangConfig exists.

  if (cfg.scopeStyle === "brace") {
    // Find the first `{` after declIdx.
    const openIdx = cleaned.indexOf("{", declIdx);
    if (openIdx === -1) return 0;

    let depth = 1;
    let i = openIdx + 1;
    let lines = 1; // include the brace's own line
    while (i < cleaned.length && depth > 0) {
      const c = cleaned[i];
      if (c === "\n") lines++;
      else if (c === "{") depth++;
      else if (c === "}") depth--;
      if (depth === 0) break;
      i++;
    }
    return lines;
  }

  if (cfg.scopeStyle === "indent") {
    // Python: scope is determined by indentation level.
    // Walk forward until we find a line whose indentation is <= the declaration's.
    const matchDecl = findIndent(cleaned, declIdx);
    if (matchDecl === null) return 0;
    const declIndent = matchDecl;

    // Find the line where the definition actually starts (we want body, which is the next line).
    let i = declIdx;
    // Move to end of declaration line (find newline after declIdx)
    while (i < cleaned.length && cleaned[i] !== "\n") i++;
    i++; // skip newline

    let bodyLines = 0;
    let prevBlank = 0;
    while (i < cleaned.length) {
      // Look at start of this line
      let lineStart = i;
      let indent = 0;
      while (lineStart < cleaned.length && (cleaned[lineStart] === " " || cleaned[lineStart] === "\t")) {
        indent++;
        lineStart++;
      }

      if (cleaned[lineStart] === "\n" || lineStart >= cleaned.length) {
        // blank line — allow up to 2 consecutive blanks inside body
        prevBlank++;
        if (prevBlank > 2 && bodyLines > 0) break;
        i = lineStart + 1;
        continue;
      } else {
        prevBlank = 0;
      }

      if (indent <= declIndent && bodyLines > 0) {
        // exited scope
        break;
      }
      bodyLines++;
      // move to next line
      while (i < cleaned.length && cleaned[i] !== "\n") i++;
      i++;
    }
    return bodyLines;
  }

  if (cfg.scopeStyle === "keyword_end") {
    // Ruby: scope ends at matching `end`. Track nesting.
    // EXCLUDE postfix modifiers (if/unless/while/until/for) — they don't open blocks.
    let depth = 0;
    const openersRegex = /\b(def|class|module|begin|case|do)\b/;
    const endersRegex = /\bend\b/;
    // Find opener at declIdx (we know decl is `def name` — push 1)
    depth = 1;

    // Start after the declaration line
    let i = declIdx;
    while (i < cleaned.length && cleaned[i] !== "\n") i++;
    i++;

    let lines = 1;
    while (i < cleaned.length) {
      // Match next token on this line
      const lineEnd = cleaned.indexOf("\n", i);
      const line = cleaned.slice(i, lineEnd === -1 ? undefined : lineEnd);

      let m: RegExpExecArray | null;
      const openerRe = new RegExp(openersRegex);
      if ((m = openerRe.exec(line))) depth++;
      const enderRe = new RegExp(endersRegex);
      if (enderRe.test(line)) {
        depth--;
        if (depth === 0) {
          lines++;
          break;
        }
      }
      lines++;
      i = lineEnd === -1 ? cleaned.length : lineEnd + 1;
    }
    return lines;
  }

  return 0;
}

function findIndent(cleaned: string, idx: number): number {
  // find the start of the line containing idx
  let i = idx;
  while (i > 0 && cleaned[i - 1] !== "\n") i--;
  let indent = 0;
  while (i < cleaned.length && (cleaned[i] === " " || cleaned[i] === "\t")) {
    indent++;
    i++;
  }
  return indent;
}

// ===================== PUBLIC API =====================

export interface FileMetrics {
  loc: number;
  totalLines: number;
  classCount: number;
  functionCount: number;
  importCount: number;
  largeFile: boolean;          // loc > 500
  complexFunctions: number;
  longFunctions: number;       // functions > 50 LOC
  godClassCandidates: number;  // classes with > 20 functions inside their scope
  avgFunctionLength: number;
  maxFunctionLength: number;
}

/** Analyze a single file content. Never throws — all errors → zeros. */
export function analyzeFile(content: string, lang: string): FileMetrics {
  const cfg = getLangConfig(lang);
  const empty: FileMetrics = {
    loc: 0, totalLines: 0, classCount: 0, functionCount: 0, importCount: 0,
    largeFile: false, complexFunctions: 0, longFunctions: 0,
    godClassCandidates: 0, avgFunctionLength: 0, maxFunctionLength: 0,
  };
  if (!cfg) return empty;

  try {
    const cleaned = stripCommentsAndStrings(content, cfg);
    const loc = countLoc(content, lang);
    const totalLines = countTotalLines(content);

    const classMatches = findClassDeclarations(cleaned, cfg);
    const funcMatches = findFunctionDeclarations(cleaned, cfg);

    // Imports — count lines that match the import regex.
    // Use raw content (not stripped) so that quoted module paths aren't erased.
    let importCount = 0;
    const importRe = new RegExp(cfg.importRegex);
    for (const line of content.split("\n")) {
      // Strip leading line comment first so `import foo // not really` doesn't double-count.
      let stripped = line;
      for (const lc of cfg.lineComments) {
        const idx = stripped.indexOf(lc);
        if (idx >= 0) stripped = stripped.slice(0, idx);
      }
      const m = importRe.exec(stripped);
      if (m && m.some((g) => g !== undefined && g.length > 0)) importCount++;
    }

    // Function lengths
    const functionLengths: number[] = [];
    let complexFunctions = 0;
    for (const fn of funcMatches) {
      const len = extractScopeLength(cleaned, fn.startIdx, lang);
      functionLengths.push(len);
      if (len > 50) complexFunctions++;
    }
    const longFunctions = functionLengths.filter((l) => l > 50).length;
    const avgFunctionLength = functionLengths.length > 0
      ? Math.round(functionLengths.reduce((a, b) => a + b, 0) / functionLengths.length)
      : 0;
    const maxFunctionLength = functionLengths.length > 0 ? Math.max(...functionLengths) : 0;

    // God Class: classes containing > 20 functions within their scope.
    let godClassCandidates = 0;
    if (cfg.scopeStyle === "brace") {
      // For each class decl, find scope, count functions whose decl range falls within [classOpen, classClose].
      for (const cm of classMatches) {
        const openIdx = cleaned.indexOf("{", cm.startIdx);
        if (openIdx === -1) continue;
        let depth = 1;
        let i = openIdx + 1;
        let closeIdx = -1;
        while (i < cleaned.length && depth > 0) {
          if (cleaned[i] === "{") depth++;
          else if (cleaned[i] === "}") depth--;
          if (depth === 0) { closeIdx = i; break; }
          i++;
        }
        if (closeIdx === -1) continue;
        const methods = funcMatches.filter((fn) => fn.startIdx > openIdx && fn.startIdx < closeIdx);
        if (methods.length > 20) godClassCandidates++;
      }
    } else {
      // Python / Ruby: use indent/keyword_end scope lengths.
      for (const cm of classMatches) {
        // Approx: count function declarations that come AFTER the class decl and BEFORE the next class decl
        // and whose indentation is greater than the class's indentation.
        const classIndent = findIndent(cleaned, cm.startIdx);
        const nextClassIdx = classMatches.find((cm2) => cm2.startIdx > cm.startIdx)?.startIdx || cleaned.length;
        const methods = funcMatches.filter((fn) =>
          fn.startIdx > cm.startIdx &&
          fn.startIdx < nextClassIdx &&
          findIndent(cleaned, fn.startIdx) > classIndent
        );
        if (methods.length > 20) godClassCandidates++;
      }
    }

    const result: FileMetrics = {
      loc,
      totalLines,
      classCount: classMatches.length,
      functionCount: funcMatches.length,
      importCount,
      largeFile: loc > 500,
      complexFunctions,
      longFunctions,
      godClassCandidates,
      avgFunctionLength,
      maxFunctionLength,
    };

    return result;
  } catch {
    return empty;
  }
}

// ===================== IMPORT GRAPH + CYCLE DETECTION =====================

export interface ImportGraph {
  // Normalized module id (e.g. "pkg.sub.module") → file path
  nodes: Map<string, string>;
  edges: Map<string, Set<string>>;
}

/** Extracts normalized import targets from a single file. */
export function extractImports(content: string, lang: string): string[] {
  const cfg = getLangConfig(lang);
  if (!cfg) return [];
  try {
    // Do NOT use stripCommentsAndStrings here — it would erase the quoted module paths.
    // Instead strip line comments manually, and skip obvious strings-on-import-line cases.
    const out: string[] = [];
    const lines = content.split("\n");
    for (const line of lines) {
      // Strip leading // or # line comment portion (only at line start, to preserve in-body strings).
      let stripped = line;
      for (const lc of cfg.lineComments) {
        const idx = stripped.indexOf(lc);
        if (idx >= 0) stripped = stripped.slice(0, idx);
      }
      if (stripped.trim().length === 0) continue;

      const m = new RegExp(cfg.importRegex).exec(stripped);
      if (!m) continue;
      const target = m.slice(1).find((g) => g !== undefined && g.length > 0);
      if (!target) continue;
      // Normalize: strip quotes/angle brackets, strip file extension.
      const norm = target
        .replace(/^[\"'<]/, "")
        .replace(/[\"'>]$/, "")
        .replace(/\.(py|ts|tsx|js|jsx|java|go|rs|cs|kt|php|rb|swift|scala|c|h)$/, "");
      if (norm.length > 0) out.push(norm);
    }
    return out;
  } catch {
    return [];
  }
}

/** Builds a directed import graph and finds strongly connected components (cycles). */
export function findCycles(graph: Map<string, Set<string>>): number {
  // Iterative Tarjan SCC to avoid stack overflow on large graphs.
  let index = 0;
  const indices = new Map<string, number>();
  const lowlinks = new Map<string, number>();
  const onStack = new Set<string>();
  const stack: string[] = [];
  let cycleCount = 0;

  // Iterator state per node
  const iterState = new Map<string, Iterator<string>>();
  const callStack: { v: string; w: string | null; state: "enter" | "afterChild" }[] = [];

  for (const startV of graph.keys()) {
    if (indices.has(startV)) continue;

    callStack.push({ v: startV, w: null, state: "enter" });

    while (callStack.length > 0) {
      const frame = callStack[callStack.length - 1];

      if (frame.state === "enter") {
        const v = frame.v;
        indices.set(v, index);
        lowlinks.set(v, index);
        index++;
        stack.push(v);
        onStack.add(v);

        const neighbors = graph.get(v);
        if (!neighbors || neighbors.size === 0) {
          // No children — process SCC root
          callStack.pop();
          // Check SCC
          if (lowlinks.get(v) === indices.get(v)) {
            const scc: string[] = [];
            let w: string;
            do {
              w = stack.pop()!;
              onStack.delete(w);
              scc.push(w);
            } while (w !== v);
            const sccNeighbors = graph.get(v) || new Set();
            if (scc.length >= 2) cycleCount++;
            else if (scc.length === 1 && sccNeighbors.has(scc[0])) cycleCount++;
          }
        } else {
          const it = neighbors.values();
          iterState.set(v, it);
          frame.state = "afterChild";
          // push first child
          const next = it.next();
          if (!next.done) {
            frame.w = next.value;
            callStack.push({ v: next.value, w: null, state: "enter" });
          } else {
            callStack.pop();
            // No children — process SCC root (same as above)
            if (lowlinks.get(v) === indices.get(v)) {
              const scc: string[] = [];
              let w: string;
              do {
                w = stack.pop()!;
                onStack.delete(w);
                scc.push(w);
              } while (w !== v);
              const sccNeighbors = graph.get(v) || new Set();
              if (scc.length >= 2) cycleCount++;
              else if (scc.length === 1 && sccNeighbors.has(scc[0])) cycleCount++;
            }
          }
        }
        continue;
      }

      // state === "afterChild"
      const v = frame.v;
      const childW = frame.w!;
      lowlinks.set(v, Math.min(lowlinks.get(v)!, lowlinks.get(childW)!));

      const it = iterState.get(v)!;
      const next = it.next();
      if (!next.done) {
        // Next child exists — check if already visited or on stack
        const w = next.value;
        frame.w = w;
        if (!indices.has(w)) {
          callStack.push({ v: w, w: null, state: "enter" });
        } else if (onStack.has(w)) {
          lowlinks.set(v, Math.min(lowlinks.get(v)!, indices.get(w)!));
          // Continue with next child
        }
        // else: already visited but not on stack → cross-edge, skip
      } else {
        // All children visited — pop and process SCC
        callStack.pop();
        iterState.delete(v);

        if (lowlinks.get(v) === indices.get(v)) {
          const scc: string[] = [];
          let w: string;
          do {
            w = stack.pop()!;
            onStack.delete(w);
            scc.push(w);
          } while (w !== v);
          const sccNeighbors = graph.get(v) || new Set();
          if (scc.length >= 2) cycleCount++;
          else if (scc.length === 1 && sccNeighbors.has(scc[0])) cycleCount++;
        }

        // Update parent lowlink if we're returning from a child
        if (callStack.length > 0) {
          const parent = callStack[callStack.length - 1];
          if (parent.v !== v) {
            lowlinks.set(parent.v, Math.min(lowlinks.get(parent.v)!, lowlinks.get(v)!));
          }
        }
      }
    }
  }

  return cycleCount;
}

// ===================== ARCHITECTURE PATTERN DETECTION =====================

export interface DetectedPattern {
  pattern: string;
  compatibility: number;  // 0-100
}

function dirExists(dirs: string[], pattern: string): boolean {
  const p = pattern.toLowerCase();
  return dirs.some((d) => d.toLowerCase().split("/").some((seg) => seg === p || seg.startsWith(p)));
}

/**
 * Detects architecture patterns from directory structure.
 * Stricter: requires multiple matching directories AND uses scoring.
 */
export function detectPatterns(directoryList: string[]): DetectedPattern[] {
  const patterns: DetectedPattern[] = [];

  const has = (p: string) => dirExists(directoryList, p);

  // MVC: requires all three of controller/model/view (or views)
  if ((has("controller") || has("controllers")) &&
      (has("model") || has("models")) &&
      (has("view") || has("views") || has("template") || has("templates"))) {
    patterns.push({ pattern: "MVC", compatibility: 85 });
  }

  // Layered: requires presentation + business + data layers
  if (has("api") && has("service") && has("model")) {
    patterns.push({ pattern: "Layered", compatibility: 70 });
  }
  if (has("controller") && has("service") && has("repository")) {
    patterns.push({ pattern: "Layered (Repository)", compatibility: 80 });
  }

  // DDD: all of domain/application/infrastructure
  if (has("domain") && has("application") && has("infrastructure")) {
    patterns.push({ pattern: "DDD", compatibility: 80 });
  }

  // Hexagonal: both ports AND adapters (not just one)
  if (has("ports") && has("adapters")) {
    patterns.push({ pattern: "Hexagonal", compatibility: 75 });
  } else if (has("ports")) {
    patterns.push({ pattern: "Ports (incomplete Hexagonal)", compatibility: 40 });
  } else if (has("adapters")) {
    patterns.push({ pattern: "Adapters (incomplete Hexagonal)", compatibility: 40 });
  }

  // Modular Monolith: multiple module-prefixed directories (e.g. modules/X, modules/Y)
  const moduleLike = directoryList.filter((d) => {
    const segs = d.toLowerCase().split("/");
    return segs.includes("modules") || segs.includes("module");
  });
  // Heuristic: there should be more than 2 distinct module subdirs to call it modular monolith
  const subdirs = new Set<string>();
  for (const d of moduleLike) {
    const segs = d.split("/");
    const idx = segs.findIndex((s) => s.toLowerCase() === "modules" || s.toLowerCase() === "module");
    if (idx !== -1 && idx + 1 < segs.length) subdirs.add(segs[idx + 1]);
  }
  if (subdirs.size >= 2) {
    patterns.push({ pattern: "Modular Monolith", compatibility: 65 });
  }

  // Microservices: presence of explicit `microservices/` directory, OR
  // `services/` with >=3 subdirs AND deployment-scoped sibling dirs (deploy/, docker/, k8s/, helm/).
  const hasDeploySibling = directoryList.some((d) => {
    const segs = d.toLowerCase().split("/");
    return segs.some((s) => ["deploy", "docker", "k8s", "helm", "kubernetes", "charts"].includes(s));
  });
  const servicesLike = directoryList.filter((d) => {
    const segs = d.toLowerCase().split("/");
    return segs.includes("microservices") || segs.includes("services") || segs.includes("service");
  });
  const svcSubdirs = new Set<string>();
  for (const d of servicesLike) {
    const segs = d.split("/");
    const idx = segs.findIndex((s) => s.toLowerCase() === "microservices" || s.toLowerCase() === "services" || s.toLowerCase() === "service");
    if (idx !== -1 && idx + 1 < segs.length) svcSubdirs.add(segs[idx + 1]);
  }
  // Strong indicator: explicit `microservices/` with >=2 service subdirs
  const hasMicroservicesDir = directoryList.some((d) => d.toLowerCase().split("/").includes("microservices"));
  if ((hasMicroservicesDir && svcSubdirs.size >= 2) ||
      (svcSubdirs.size >= 3 && hasDeploySibling)) {
    patterns.push({ pattern: "Microservices (heuristic)", compatibility: 55 });
  }

  return patterns;
}
