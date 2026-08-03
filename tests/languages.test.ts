/**
 * Çok dilli kapsam testleri: her dil × her tarayıcı matrisi.
 * Motorun dil ailelerini (brace / python / ruby) doğru stratejiyle
 * analiz ettiğini kanıtlar.
 */
import { describe, it, expect } from "vitest";
import { scanRepo, evidenceIn } from "./helpers";

// ---------------------------------------------------------------------------
// Uzun fonksiyon: dil ailesi matrisi
// ---------------------------------------------------------------------------
describe("long_function — çok dilli", () => {
  const longBody = (open: string, close: string, prefix = "  ", suffix = "") => {
    const lines = [open];
    for (let i = 0; i < 60; i++) lines.push(`${prefix}step_${i} = work(${i})${suffix}`);
    lines.push(close);
    return lines.join("\n");
  };

  it("Java metodu (public void x()) yakalanır", async () => {
    const scan = await scanRepo([{ path: "src/Service.java", content: longBody("public class S {", "}", "  public void m() {", " }") }]);
    expect(evidenceIn(scan, "long_function").length).toBeGreaterThan(0);
  });

  it("C# metodu (public void x()) yakalanır", async () => {
    const scan = await scanRepo([{ path: "src/S.cs", content: longBody("public class S {", "}", "  public void M() {", " }") }]);
    expect(evidenceIn(scan, "long_function").length).toBeGreaterThan(0);
  });

  it("Kotlin fun yakalanır", async () => {
    const scan = await scanRepo([{ path: "src/S.kt", content: longBody("class S {", "}", "  fun m() {", " }") }]);
    expect(evidenceIn(scan, "long_function").length).toBeGreaterThan(0);
  });

  it("C/C++ metodu yakalanır", async () => {
    const scan = await scanRepo([{ path: "src/s.cpp", content: longBody("void m() {", "}", "", ";") }]);
    expect(evidenceIn(scan, "long_function").length).toBeGreaterThan(0);
  });

  it("Ruby parantezsiz def ... end yakalanır", async () => {
    const lines = ["class X"];
    lines.push("def long_method");
    for (let i = 0; i < 55; i++) lines.push(`  puts ${i}`);
    lines.push("end");
    lines.push("end");
    const scan = await scanRepo([{ path: "src/x.rb", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "long_function").length).toBeGreaterThan(0);
  });

  it("Python gerçek uzun def indentation ile yakalanır", async () => {
    const lines = ["def real_long():"];
    for (let i = 0; i < 60; i++) lines.push(`    step_${i} = work(${i})`);
    lines.push("    return step_59");
    const scan = await scanRepo([{ path: "src/real.py", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "long_function")).toHaveLength(1);
  });

  it("Python modül seviyesindeki büyük dict yanlış pozitif üretmez", async () => {
    const lines = ["def short():", "    return CONFIG[\"k\"]", "", "CONFIG = {"];
    for (let i = 0; i < 60; i++) lines.push(`    "k_${i}": "v",`);
    lines.push("}");
    const scan = await scanRepo([{ path: "src/mod.py", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "long_function")).toHaveLength(0);
  });

  it("Go func yakalanır", async () => {
    const scan = await scanRepo([{ path: "src/main.go", content: longBody("func longFn() {", "}", "\tv := 0", "") }]);
    expect(evidenceIn(scan, "long_function").length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// God Class: Python / Ruby / brace
// ---------------------------------------------------------------------------
describe("god_class — çok dilli", () => {
  it("Python 25 metodlu sınıf yakalanır", async () => {
    const lines = ["class GodService:"];
    for (let i = 0; i < 25; i++) lines.push(`    def method_${i}(self):`);
    lines.push("        return 0");
    const scan = await scanRepo([{ path: "src/god.py", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "god_class")).toHaveLength(1);
  });

  it("Python 5 metodlu sınıf yakalanmaz", async () => {
    const lines = ["class Small:"];
    for (let i = 0; i < 5; i++) lines.push(`    def m_${i}(self):`);
    lines.push("        return 0");
    const scan = await scanRepo([{ path: "src/small.py", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "god_class")).toHaveLength(0);
  });

  it("Ruby 25 metodlu sınıf yakalanır", async () => {
    const lines = ["class GodService"];
    for (let i = 0; i < 25; i++) lines.push(`  def method_${i}`);
    lines.push("    nil");
    lines.push("  end");
    lines.push("end");
    const scan = await scanRepo([{ path: "src/god.rb", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "god_class")).toHaveLength(1);
  });

  it("Java 25 metodlu sınıf yakalanır", async () => {
    const lines = ["public class GodService {"];
    for (let i = 0; i < 25; i++) lines.push(`  public void method${i}() {}`);
    lines.push("}");
    const scan = await scanRepo([{ path: "src/GodService.java", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "god_class")).toHaveLength(1);
  });

  it("TS 25 metodlu sınıf yakalanır", async () => {
    const lines = ["class GodService {"];
    for (let i = 0; i < 25; i++) lines.push(`  method${i}() { return ${i}; }`);
    lines.push("}");
    const scan = await scanRepo([{ path: "src/GodService.ts", content: lines.join("\n") }]);
    expect(evidenceIn(scan, "god_class")).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// Import / döngü: çok dilli
// ---------------------------------------------------------------------------
describe("import çözümleme — çok dilli", () => {
  it("C# using döngüsü yakalanır", async () => {
    const scan = await scanRepo([
      { path: "src/A.cs", content: "using B;\nnamespace A { public class A1 {} }\n" },
      { path: "src/B.cs", content: "using A;\nnamespace B { public class B1 {} }\n" },
    ]);
    expect(evidenceIn(scan, "circular_dependency").length).toBeGreaterThan(0);
  });

  it("Ruby require döngüsü yakalanır", async () => {
    const scan = await scanRepo([
      { path: "src/a.rb", content: "require_relative 'b'\n" },
      { path: "src/b.rb", content: "require_relative 'a'\n" },
    ]);
    expect(evidenceIn(scan, "circular_dependency").length).toBeGreaterThan(0);
  });

  it("Java import döngüsü yakalanır", async () => {
    const scan = await scanRepo([
      { path: "src/com/a/A.java", content: "import com.b.B;\npublic class A {}\n" },
      { path: "src/com/b/B.java", content: "import com.a.A;\npublic class B {}\n" },
    ]);
    expect(evidenceIn(scan, "circular_dependency").length).toBeGreaterThan(0);
  });

  it("PHP use döngüsü yakalanır", async () => {
    const scan = await scanRepo([
      { path: "src/a.php", content: "<?php use Foo\\B; ?>\n" },
      { path: "src/b.php", content: "<?php use Foo\\A; ?>\n" },
    ]);
    expect(evidenceIn(scan, "circular_dependency").length).toBeGreaterThan(0);
  });

  it("TS import döngüsü yakalanır (regresyon)", async () => {
    const scan = await scanRepo([
      { path: "src/a.ts", content: 'import { b } from "./b";\nexport const a = 1;\n' },
      { path: "src/b.ts", content: 'import { a } from "./a";\nexport const b = 2;\n' },
    ]);
    expect(evidenceIn(scan, "circular_dependency")).toHaveLength(2);
  });
});

// ---------------------------------------------------------------------------
// Secret: dil bağımsızlığı (Python / Java / Go / C#)
// ---------------------------------------------------------------------------
describe("hardcoded_secret — çok dilli", () => {
  const SK = "sk-" + "abc1234567890abcdefghijklmnop";

  it("Python dosyasında yakalanır", async () => {
    const scan = await scanRepo([{ path: "src/cfg.py", content: `api_key = "${SK}"\n` }]);
    expect(evidenceIn(scan, "hardcoded_secret")).toHaveLength(1);
  });

  it("Java dosyasında yakalanır", async () => {
    const scan = await scanRepo([{ path: "src/Cfg.java", content: `String key = "${SK}";\n` }]);
    expect(evidenceIn(scan, "hardcoded_secret")).toHaveLength(1);
  });

  it("Go dosyasında yakalanır", async () => {
    const scan = await scanRepo([{ path: "src/cfg.go", content: `key := "${SK}"\n` }]);
    expect(evidenceIn(scan, "hardcoded_secret")).toHaveLength(1);
  });

  it("C# dosyasında yakalanır", async () => {
    const scan = await scanRepo([{ path: "src/Cfg.cs", content: `string key = "${SK}";\n` }]);
    expect(evidenceIn(scan, "hardcoded_secret")).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// hasTests: ek dil konvansiyonları
// ---------------------------------------------------------------------------
describe("hasTests — çok dilli konvansiyonlar", () => {
  it("Java/C#/Kotlin/Go/Rust test konvansiyonlarını tanır", async () => {
    const scan = await scanRepo([
      { path: "src/test/java/com/x/ServiceTest.java", content: "public class ServiceTest {}\n" },
      { path: "src/Tests/ServiceTests.cs", content: "public class ServiceTests {}\n" },
      { path: "src/service_test.go", content: "func TestX(t *testing.T) {}\n" },
      { path: "tests/service_test.rs", content: "#[test] fn x() {}\n" },
      { path: "src/service.spec.kt", content: "class ServiceSpec {}\n" },
    ]);
    expect(scan.hasTests).toBe(true);
  });
});
