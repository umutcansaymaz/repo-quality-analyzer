"""Tests for the dependency manifest parsers."""

from __future__ import annotations

from repo_analyzer.analyzers.dependency.manifests import (
    cargo,
    composer,
    gradle,
    nodejs,
    pom,
    python,
)
from repo_analyzer.analyzers.dependency.manifests import (
    go as go_manifest,
)


class TestPythonManifests:
    def test_parse_requirements(self) -> None:
        content = "requests>=2.0\npyyaml==6.0\n# comment\n-r other.txt\n"
        deps = python.parse_requirements(content)
        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "pyyaml" in names
        assert all(d["ecosystem"] == "pypi" for d in deps)

    def test_parse_requirements_with_extras(self) -> None:
        content = "package[extra]>=1.0\n"
        deps = python.parse_requirements(content)
        assert deps[0]["name"] == "package"

    def test_parse_pyproject(self) -> None:
        content = """
[project]
name = "test"
dependencies = ["requests>=2.0", "pyyaml"]
[project.optional-dependencies]
dev = ["pytest"]
"""
        deps = python.parse_pyproject(content)
        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "pyyaml" in names
        assert "pytest" in names

    def test_parse_pyproject_poetry(self) -> None:
        content = """
[tool.poetry.dependencies]
requests = "^2.0"
pyyaml = "*"
python = "^3.10"
"""
        deps = python.parse_pyproject(content)
        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "pyyaml" in names
        assert "python" not in names

    def test_parse_pyproject_invalid(self) -> None:
        deps = python.parse_pyproject("not valid toml {")
        assert deps == []


class TestNodejsManifest:
    def test_parse_package_json(self) -> None:
        content = '{"dependencies": {"lodash": "^4.0"}, "devDependencies": {"jest": "^29.0"}}'
        deps = nodejs.parse_package_json(content)
        names = [d["name"] for d in deps]
        assert "lodash" in names
        assert "jest" in names
        assert all(d["ecosystem"] == "npm" for d in deps)

    def test_parse_package_json_invalid(self) -> None:
        deps = nodejs.parse_package_json("not json")
        assert deps == []


class TestCargoManifest:
    def test_parse_cargo_toml(self) -> None:
        content = """
[dependencies]
serde = "1.0"
tokio = { version = "1.0", features = ["full"] }

[dev-dependencies]
criterion = "0.5"
"""
        deps = cargo.parse_cargo_toml(content)
        names = [d["name"] for d in deps]
        assert "serde" in names
        assert "tokio" in names
        assert "criterion" in names
        assert all(d["ecosystem"] == "cargo" for d in deps)


class TestGoManifest:
    def test_parse_go_mod(self) -> None:
        content = """
module github.com/test/repo

go 1.21

require (
    github.com/pkg/errors v0.9.1
    golang.org/x/sys v0.0.0
)

require github.com/stretchr/testify v1.8.0
"""
        deps = go_manifest.parse_go_mod(content)
        names = [d["name"] for d in deps]
        assert "github.com/pkg/errors" in names
        assert "github.com/stretchr/testify" in names
        assert all(d["ecosystem"] == "go" for d in deps)


class TestComposerManifest:
    def test_parse_composer_json(self) -> None:
        content = (
            '{"require": {"monolog/monolog": "2.0"}, "require-dev": {"phpunit/phpunit": "9.0"}}'
        )
        deps = composer.parse_composer_json(content)
        names = [d["name"] for d in deps]
        assert "monolog/monolog" in names
        assert "phpunit/phpunit" in names
        assert all(d["ecosystem"] == "composer" for d in deps)

    def test_parse_composer_skips_php(self) -> None:
        content = '{"require": {"php": ">=8.0", "ext-json": "*"}}'
        deps = composer.parse_composer_json(content)
        assert all(d["name"] != "php" for d in deps)


class TestPomManifest:
    def test_parse_pom_xml(self) -> None:
        content = """<dependencies>
<dependency>
  <groupId>org.springframework</groupId>
  <artifactId>spring-core</artifactId>
  <version>6.0.0</version>
</dependency>
<dependency>
  <groupId>junit</groupId>
  <artifactId>junit</artifactId>
</dependency>
</dependencies>"""
        deps = pom.parse_pom_xml(content)
        names = [d["name"] for d in deps]
        assert "org.springframework:spring-core" in names
        assert "junit:junit" in names
        assert all(d["ecosystem"] == "maven" for d in deps)


class TestGradleManifest:
    def test_parse_build_gradle(self) -> None:
        content = """
dependencies {
    implementation 'org.springframework:spring-core:6.0.0'
    testImplementation 'junit:junit:4.13.2'
    api 'com.google.guava:guava:32.0'
}
"""
        deps = gradle.parse_build_gradle(content)
        names = [d["name"] for d in deps]
        assert "org.springframework:spring-core" in names
        assert "junit:junit" in names
        assert "com.google.guava:guava" in names
        assert all(d["ecosystem"] == "gradle" for d in deps)
