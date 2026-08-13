#!/usr/bin/env python3
"""VERSION / RELEASES helpers for ontology repositories.

VERSION file format (repo root):
  version: 1.2.3
  doc-only: 2026-07-27   # optional

RELEASES file format (repo root), one record per line:
  <semver> <YYYY-MM-DD> <ontology|doc-only>

Ontology TTL stamping (docs/**/*.ttl) on ontology releases:
  * Main ontology files (declare owl:versionInfo): always ensure versionInfo,
    versionIRI, and dcterms:modified (insert if missing). priorVersion is
    ensured when a prior ontology release exists; removed when it does not.
    Full releases point priorVersion at the latest prior *full* release;
    pre-releases point at the immediately prior ontology SemVer.
  * Component files (no owl:versionInfo): if the file is new or changed since
    the previous ontology git tag, update dcterms:modified or insert it.
    Unchanged existing files without dcterms:modified are left alone.
  Ontology namespace for versionIRI is derived per file from
  vann:preferredNamespaceUri, owl:Ontology IRI, BASE, or PREFIX :.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple

def _repo_root() -> Path:
    """Ontology repository root (VERSION, RELEASES, docs/).

    In GitHub Actions the script is checked out under
    ``.ontology-shared-scripts/scripts/``; ontology files live at
    ``GITHUB_WORKSPACE``. Locally the script usually lives at ``<repo>/scripts/``.
    """
    ws = os.environ.get("GITHUB_WORKSPACE")
    if ws:
        return Path(ws)
    return Path(__file__).resolve().parents[1]


ROOT = _repo_root()
VERSION_PATH = ROOT / "VERSION"
RELEASES_PATH = ROOT / "RELEASES"
DOCS_DIR = ROOT / "docs"

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))"
    r"?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _ident_key(part: str) -> Tuple:
    """SemVer pre-release identifier comparison key."""
    if part.isdigit():
        return (0, int(part))
    return (1, part)


@total_ordering
@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int
    prerelease: Tuple[str, ...] = ()
    build: str = ""

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        text = value.strip()
        if text.startswith(("v", "V")) and SEMVER_RE.match(text[1:]):
            text = text[1:]
        m = SEMVER_RE.match(text)
        if not m:
            raise ValueError(f"Invalid SemVer: {value!r}")
        pre = tuple(m.group(4).split(".")) if m.group(4) else ()
        build = m.group(5) or ""
        return cls(int(m.group(1)), int(m.group(2)), int(m.group(3)), pre, build)

    @property
    def text(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += "-" + ".".join(self.prerelease)
        if self.build:
            base += "+" + self.build
        return base

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        return (
            self.major,
            self.minor,
            self.patch,
            self.prerelease,
        ) == (other.major, other.minor, other.patch, other.prerelease)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemVer):
            return NotImplemented
        core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if core != other_core:
            return core < other_core
        # Pre-release has lower precedence than release
        if self.prerelease and not other.prerelease:
            return True
        if not self.prerelease and other.prerelease:
            return False
        for a, b in zip(self.prerelease, other.prerelease):
            if a == b:
                continue
            return _ident_key(a) < _ident_key(b)
        return len(self.prerelease) < len(other.prerelease)


@dataclass(frozen=True)
class VersionFile:
    version: str
    doc_only: Optional[dt.date] = None

    @property
    def is_doc_only(self) -> bool:
        return self.doc_only is not None

    @property
    def semver(self) -> SemVer:
        return SemVer.parse(self.version)

    @property
    def is_prerelease(self) -> bool:
        return bool(self.semver.prerelease)

    @property
    def release_type(self) -> str:
        return "doc-only" if self.is_doc_only else "ontology"


@dataclass(frozen=True)
class ReleaseRecord:
    version: str
    date: dt.date
    kind: str  # ontology | doc-only


def normalize_semver(value: str) -> str:
    return SemVer.parse(value).text


def discover_ttl_files(docs_dir: Path = DOCS_DIR) -> list[Path]:
    """All Turtle files under docs/ (recursive)."""
    if not docs_dir.is_dir():
        return []
    return sorted(p for p in docs_dir.rglob("*.ttl") if p.is_file())


def _has_ttl_field(text: str, field: str) -> bool:
    return bool(re.search(rf"^\s*{re.escape(field)}\s+", text, flags=re.MULTILINE))


def _normalize_ontology_ns(ns: str) -> str:
    """Ensure a path-style namespace base suitable for versionIRI concatenation."""
    ns = ns.strip()
    if ns.endswith("#"):
        ns = ns[:-1]
    if not ns.endswith("/"):
        ns += "/"
    return ns


def ontology_ns_from_ttl(text: str) -> str:
    """Derive ontology namespace from vann:preferredNamespaceUri, owl:Ontology IRI, BASE, or default PREFIX."""
    m = re.search(
        r'^\s*vann:preferredNamespaceUri\s+(?:"([^"]+)"|<([^>]+)>)',
        text,
        flags=re.MULTILINE,
    )
    if m:
        return _normalize_ontology_ns(m.group(1) or m.group(2))

    m = re.search(
        r"<(https?://[^>\s]+)>\s+(?:a|rdf:type)\s+owl:Ontology\b",
        text,
    )
    if m:
        return _normalize_ontology_ns(m.group(1))

    # Common RITSO style: BASE / default PREFIX declare the topic-area namespace.
    m = re.search(
        r"^(?:BASE|@base)\s+<(https?://[^>\s]+)>\s*\.?\s*$",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if m:
        return _normalize_ontology_ns(m.group(1))

    m = re.search(
        r"^(?:PREFIX|@prefix)\s+:\s+<(https?://[^>\s]+)>\s*\.?\s*$",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if m:
        return _normalize_ontology_ns(m.group(1))

    raise ValueError(
        "Could not derive ontology namespace from vann:preferredNamespaceUri, "
        "owl:Ontology IRI, BASE, or PREFIX :"
    )


def version_iri(version: str, ontology_ns: str) -> str:
    return f"{_normalize_ontology_ns(ontology_ns)}{normalize_semver(version)}"


def parse_version_file(path: Path = VERSION_PATH) -> VersionFile:
    if not path.is_file():
        raise ValueError(f"VERSION file not found: {path}")
    version: Optional[str] = None
    doc_only: Optional[dt.date] = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid VERSION line (expected key: value): {raw!r}")
        key, val = line.split(":", 1)
        key = key.strip().lower()
        val = val.strip()
        if key == "version":
            version = normalize_semver(val)
        elif key == "doc-only":
            if not DATE_RE.match(val):
                raise ValueError(f"Invalid doc-only date (YYYY-MM-DD): {val!r}")
            doc_only = dt.date.fromisoformat(val)
        else:
            raise ValueError(f"Unknown VERSION key: {key!r}")
    if not version:
        raise ValueError("VERSION must contain a 'version:' line")
    return VersionFile(version=version, doc_only=doc_only)


def parse_releases(path: Path = RELEASES_PATH) -> list[ReleaseRecord]:
    if not path.is_file():
        return []
    records: list[ReleaseRecord] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(
                "Invalid RELEASES line "
                "(expected '<semver> <YYYY-MM-DD> <ontology|doc-only>'): "
                f"{raw!r}"
            )
        version, date_s, kind = parts
        version = normalize_semver(version)
        if not DATE_RE.match(date_s):
            raise ValueError(f"Invalid RELEASES date: {date_s!r}")
        if kind not in ("ontology", "doc-only"):
            raise ValueError(f"Invalid RELEASES type: {kind!r}")
        records.append(
            ReleaseRecord(
                version=version,
                date=dt.date.fromisoformat(date_s),
                kind=kind,
            )
        )
    return records


def latest_semver(records: Iterable[ReleaseRecord]) -> Optional[str]:
    best: Optional[SemVer] = None
    best_text: Optional[str] = None
    for rec in records:
        cur = SemVer.parse(rec.version)
        if best is None or cur > best:
            best = cur
            best_text = normalize_semver(rec.version)
    return best_text


def latest_full_ontology_version(records: Iterable[ReleaseRecord]) -> Optional[str]:
    """Latest ontology release with no pre-release label."""
    best: Optional[SemVer] = None
    best_text: Optional[str] = None
    for rec in records:
        if rec.kind != "ontology":
            continue
        ver = SemVer.parse(rec.version)
        if ver.prerelease:
            continue
        if best is None or ver > best:
            best = ver
            best_text = normalize_semver(rec.version)
    return best_text


def latest_ontology_version(records: Iterable[ReleaseRecord]) -> Optional[str]:
    """Latest ontology SemVer in RELEASES (includes pre-releases)."""
    best: Optional[SemVer] = None
    best_text: Optional[str] = None
    for rec in records:
        if rec.kind != "ontology":
            continue
        ver = SemVer.parse(rec.version)
        if best is None or ver > best:
            best = ver
            best_text = normalize_semver(rec.version)
    return best_text


def prior_version_for(
    records: list[ReleaseRecord], *, for_prerelease: bool
) -> Optional[str]:
    """Choose owl:priorVersion target for the release being stamped.

    Pre-releases reference the immediately prior ontology SemVer (full or pre).
    Full releases reference the latest prior *full* ontology release only, so
    retired pre-release tags are not left as priorVersion.
    """
    if for_prerelease:
        return latest_ontology_version(records)
    return latest_full_ontology_version(records)


def max_release_date(records: Iterable[ReleaseRecord]) -> Optional[dt.date]:
    dates = [r.date for r in records]
    return max(dates) if dates else None


def suggest_next_semver(latest: Optional[str], *, prerelease: bool = True) -> str:
    """Suggest the next SemVer after latest (default: bump pre-release or patch-pre)."""
    if not latest:
        return "0.0.1-alpha.1" if prerelease else "0.0.1"
    cur = SemVer.parse(latest)
    if prerelease:
        if cur.prerelease:
            # bump last numeric id if present, else append .1
            pre = list(cur.prerelease)
            if pre and pre[-1].isdigit():
                pre[-1] = str(int(pre[-1]) + 1)
            else:
                pre.append("1")
            return SemVer(cur.major, cur.minor, cur.patch, tuple(pre)).text
        # turn 1.2.3 into 1.2.4-alpha.1
        return SemVer(cur.major, cur.minor, cur.patch + 1, ("alpha", "1")).text
    if cur.prerelease:
        # next full release of same X.Y.Z
        return SemVer(cur.major, cur.minor, cur.patch).text
    return SemVer(cur.major, cur.minor, cur.patch + 1).text


def validate(
    version_path: Path = VERSION_PATH, releases_path: Path = RELEASES_PATH
) -> VersionFile:
    vf = parse_version_file(version_path)
    records = parse_releases(releases_path)
    latest = latest_semver(records)
    max_date = max_release_date(records)

    if vf.is_doc_only:
        assert vf.doc_only is not None
        if latest is None:
            raise ValueError(
                "doc-only releases require a prior ontology SemVer in RELEASES"
            )
        if normalize_semver(vf.version) != normalize_semver(latest):
            raise ValueError(
                f"doc-only PR must keep version: {latest} (VERSION has {vf.version}). "
                f"Do not bump SemVer for documentation-only changes."
            )
        if max_date is not None and vf.doc_only < max_date:
            raise ValueError(
                f"doc-only date {vf.doc_only.isoformat()} must be >= latest "
                f"RELEASES date {max_date.isoformat()}"
            )
        print(
            f"OK: doc-only release for ontology {vf.version} "
            f"on {vf.doc_only.isoformat()}"
        )
        return vf

    if latest is not None and not (vf.semver > SemVer.parse(latest)):
        suggested = suggest_next_semver(latest, prerelease=True)
        raise ValueError(
            f"VERSION {vf.version} must be > latest release {latest} "
            f"(from the PR base RELEASES). Suggested next line:\n"
            f"  version: {suggested}"
        )
    kind = "pre-release" if vf.is_prerelease else "full release"
    print(f"OK: ontology {kind} {vf.version} (latest on base was {latest or 'none'})")
    return vf


def _field_terminator_after(text: str, field: str) -> str:
    """Return '.' or ';' currently used after the given owl/dcterms field."""
    m = re.search(
        rf"^\s*{re.escape(field)}\s+\S+.*?([;.])\s*$",
        text,
        flags=re.MULTILINE,
    )
    return m.group(1) if m else ";"


def _ttl_label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _sub_ttl_field(
    text: str, field: str, new_value: str, term: Optional[str] = None
) -> str:
    terminator = term if term is not None else _field_terminator_after(text, field)
    pattern = rf"^(\s*{re.escape(field)}\s+)\S+.*$"
    replacement = rf"\1{new_value} {terminator}"
    new_body, n = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if n != 1:
        raise ValueError(f"Expected one match for field {field}")
    return new_body


def _insert_ttl_field_after(
    text: str, field: str, new_value: str, after_field: str
) -> str:
    """Insert field after after_field; after_field keeps ';' and new field takes old terminator."""
    term = _field_terminator_after(text, after_field)
    padded = f"{field:<30}"
    pattern = rf"^(\s*{re.escape(after_field)}\s+\S+.*?)\s*[;.]\s*$"
    new_text, n = re.subn(
        pattern,
        rf"\1 ;\n    {padded} {new_value} {term}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise ValueError(f"Could not insert {field} after {after_field}")
    return new_text


def _upsert_ttl_field(
    text: str, field: str, new_value: str, *, after_field: str
) -> str:
    if _has_ttl_field(text, field):
        return _sub_ttl_field(text, field, new_value)
    return _insert_ttl_field_after(text, field, new_value, after_field)


def _remove_ttl_field(text: str, field: str) -> str:
    """Remove a predicate line; if it ended the block with '.', give '.' to a prior field."""
    m = re.search(
        rf"^\s*{re.escape(field)}\s+\S+.*?([;.])\s*$",
        text,
        flags=re.MULTILINE,
    )
    if not m:
        return text
    term = m.group(1)
    start, end = m.start(), m.end()
    if end < len(text) and text[end] == "\n":
        end += 1
    elif start > 0 and text[start - 1] == "\n":
        start -= 1
    text = text[:start] + text[end:]
    if term == ".":
        for prev in ("owl:versionIRI", "owl:versionInfo", "dcterms:modified"):
            if _has_ttl_field(text, prev):
                text = re.sub(
                    rf"^(\s*{re.escape(prev)}\s+\S+.*?)\s*[;.]\s*$",
                    r"\1 .",
                    text,
                    count=1,
                    flags=re.MULTILINE,
                )
                break
    return text


def _ensure_modified_date(text: str, modified: str) -> str:
    """Update dcterms:modified, or insert it after the owl:Ontology declaration."""
    value = f'"{modified}"^^xsd:date'
    if _has_ttl_field(text, "dcterms:modified"):
        return _sub_ttl_field(text, "dcterms:modified", value)

    pattern = r"^(\s*.*?\b(?:a|rdf:type)\s+owl:Ontology)\s*([;.])\s*$"
    m = re.search(pattern, text, flags=re.MULTILINE)
    if m:
        old_term = m.group(2)
        new_line = (
            f"{m.group(1)} ;\n"
            f"    dcterms:modified               {value} {old_term}"
        )
        return text[: m.start()] + new_line + text[m.end() :]

    # Main ontologies always have versionInfo; insert immediately before it.
    m = re.search(r"^(\s*)owl:versionInfo\s+", text, flags=re.MULTILINE)
    if m:
        insertion = f"{m.group(1)}dcterms:modified               {value} ;\n"
        return text[: m.start()] + insertion + text[m.start() :]

    raise ValueError(
        "Cannot insert dcterms:modified: no owl:Ontology declaration "
        "or owl:versionInfo found"
    )


def _ensure_main_ontology_metadata(
    text: str,
    *,
    modified: str,
    version: str,
    prior: Optional[str],
    ontology_ns: str,
) -> str:
    """Ensure main-ontology version metadata fields are present and current.

    Always writes versionInfo, versionIRI, and dcterms:modified. Writes
    priorVersion only when a prior release exists (removes a stale one otherwise).
    """
    if not _has_ttl_field(text, "owl:versionInfo"):
        raise ValueError("Expected owl:versionInfo in TTL")

    ver = normalize_semver(version)
    iri = version_iri(ver, ontology_ns)

    text = _ensure_modified_date(text, modified)
    text = _sub_ttl_field(text, "owl:versionInfo", f'"{ver}"')
    text = _upsert_ttl_field(
        text, "owl:versionIRI", f"<{iri}>", after_field="owl:versionInfo"
    )

    if prior:
        text = _upsert_ttl_field(
            text,
            "owl:priorVersion",
            f"<{version_iri(prior, ontology_ns)}>",
            after_field="owl:versionIRI",
        )
    else:
        text = _remove_ttl_field(text, "owl:priorVersion")
    return text


def ttl_paths_changed_since(prior_tag: Optional[str]) -> Set[Path]:
    """docs/**/*.ttl whose tree content differs from prior_tag (or all, if none).

    Includes newly added files. When there is no prior tag, every TTL is treated
    as new/changed.
    """
    all_ttl = discover_ttl_files()
    if not prior_tag:
        return set(all_ttl)

    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", prior_tag],
        cwd=ROOT,
        capture_output=True,
    )
    if probe.returncode != 0:
        print(
            f"Prior tag {prior_tag} not found; treating all docs/**/*.ttl as changed"
        )
        return set(all_ttl)

    # Compare prior release tree to the working tree (HEAD in CI).
    result = subprocess.run(
        ["git", "diff", "--name-only", prior_tag, "--", "docs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"git diff against {prior_tag} failed; "
            "treating all docs/**/*.ttl as changed",
            file=sys.stderr,
        )
        print(result.stderr.strip(), file=sys.stderr)
        return set(all_ttl)

    changed: Set[Path] = set()
    for line in result.stdout.splitlines():
        rel = line.strip()
        if not rel.endswith(".ttl"):
            continue
        path = (ROOT / rel).resolve()
        if path.is_file():
            changed.add(path)
    return changed


def stamp_ttl(
    vf: VersionFile,
    records: list[ReleaseRecord],
    today: Optional[dt.date] = None,
) -> list[Path]:
    """Update ontology TTL metadata for an ontology release. No-op for doc-only.

    Main ontologies (owl:versionInfo): ensure SemVer + modified metadata.
    Components (no versionInfo): ensure dcterms:modified when new or changed.
    """
    if vf.is_doc_only:
        return []
    today = today or dt.date.today()
    # Exclude the version we are stamping if it somehow already appears
    prior_records = [
        r
        for r in records
        if not (
            r.kind == "ontology"
            and normalize_semver(r.version) == normalize_semver(vf.version)
        )
    ]
    prior = prior_version_for(prior_records, for_prerelease=vf.is_prerelease)
    # Change detection uses the immediately prior ontology tag (including
    # pre-releases), not the priorVersion IRI target.
    immediate_prior = latest_ontology_version(prior_records)
    prior_tag = ontology_tag(immediate_prior) if immediate_prior else None
    changed_since_prior = {p.resolve() for p in ttl_paths_changed_since(prior_tag)}
    modified = today.isoformat()
    stamped: list[Path] = []

    for path in discover_ttl_files():
        original = path.read_text(encoding="utf-8")
        label = _ttl_label(path)
        is_main = _has_ttl_field(original, "owl:versionInfo")

        if is_main:
            try:
                ontology_ns = ontology_ns_from_ttl(original)
            except ValueError as e:
                raise ValueError(f"{label}: {e}") from e
            updated = _ensure_main_ontology_metadata(
                original,
                modified=modified,
                version=vf.version,
                prior=prior,
                ontology_ns=ontology_ns,
            )
            action = f"Stamped main ontology {label}"
        else:
            if path.resolve() not in changed_since_prior:
                print(
                    f"Skipping {label} (component unchanged since "
                    f"{prior_tag or 'start'})"
                )
                continue
            updated = _ensure_modified_date(original, modified)
            action = f"Updated modified on component {label}"

        if updated != original:
            path.write_text(updated, encoding="utf-8")
            stamped.append(path)
            print(action)
    return stamped


def append_release(
    vf: VersionFile,
    releases_path: Path = RELEASES_PATH,
    release_date: Optional[dt.date] = None,
) -> ReleaseRecord:
    release_date = release_date or (vf.doc_only if vf.is_doc_only else dt.date.today())
    assert release_date is not None
    rec = ReleaseRecord(
        version=normalize_semver(vf.version),
        date=release_date,
        kind=vf.release_type,
    )
    line = f"{rec.version} {rec.date.isoformat()} {rec.kind}\n"
    if releases_path.is_file():
        existing = releases_path.read_text(encoding="utf-8")
    else:
        existing = (
            "# version date type\n"
            "# type is 'ontology' or 'doc-only'\n"
        )
    if not existing.endswith("\n"):
        existing += "\n"
    releases_path.write_text(existing + line, encoding="utf-8")
    print(f"Appended to RELEASES: {line.strip()}")
    return rec


def already_recorded(vf: VersionFile, records: list[ReleaseRecord]) -> bool:
    date = vf.doc_only if vf.is_doc_only else None
    for rec in reversed(records):
        if rec.version != normalize_semver(vf.version):
            continue
        if rec.kind != vf.release_type:
            continue
        if vf.is_doc_only:
            if date and rec.date == date:
                return True
        else:
            return True
    return False


def choose_doc_tag(
    version: str, doc_date: dt.date, existing_tags: Iterable[str]
) -> str:
    """vX.Y.Z-docs-YYYY-MM-DD (Mike-friendly), with UTC time if that tag exists."""
    tags = set(existing_tags)
    ver = ontology_tag(version)
    base = f"{ver}-docs-{doc_date.isoformat()}"
    if base not in tags:
        return base
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    return f"{ver}-docs-{stamp}"


def ontology_tag(version: str) -> str:
    return f"v{normalize_semver(version)}"


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        releases = Path(args.releases) if getattr(args, "releases", "") else RELEASES_PATH
        validate(version_path=VERSION_PATH, releases_path=releases)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    try:
        releases = Path(args.releases) if args.releases else RELEASES_PATH
        records = parse_releases(releases)
        latest = latest_semver(records)
        print(suggest_next_semver(latest, prerelease=not args.full))
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def _tag_for(vf: VersionFile, existing_tags: Iterable[str]) -> str:
    if vf.is_doc_only:
        assert vf.doc_only is not None
        return choose_doc_tag(vf.version, vf.doc_only, existing_tags)
    return ontology_tag(vf.version)


def cmd_apply(args: argparse.Namespace) -> int:
    """Stamp TTL (ontology only), append RELEASES if not already recorded.

    Always emits the git tag for the current VERSION so the workflow can create
    a GitHub Release even when metadata was already written (retry / race).
    """
    try:
        vf = parse_version_file()
        records = parse_releases()
        existing = [
            t.strip() for t in (args.existing_tags or "").split(",") if t.strip()
        ]
        tag = _tag_for(vf, existing)
        prerelease = (not vf.is_doc_only) and vf.is_prerelease

        if already_recorded(vf, records):
            print(
                "RELEASES already has this version; ensuring GitHub Release can be published."
            )
            _emit_outputs(
                vf, tag=tag, prerelease=prerelease, changed=False, publish=True
            )
            return 0

        # Only enforce bump/date rules when this VERSION is not yet recorded
        validate()

        if not vf.is_doc_only:
            stamp_ttl(vf, records)

        release_date = vf.doc_only if vf.is_doc_only else dt.date.today()
        append_release(vf, release_date=release_date)

        _emit_outputs(vf, tag=tag, prerelease=prerelease, changed=True, publish=True)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


def _emit_outputs(
    vf: VersionFile,
    *,
    tag: str,
    prerelease: bool,
    changed: bool,
    publish: bool = True,
) -> None:
    lines = [
        f"kind={vf.release_type}",
        f"version={vf.version}",
        f"tag={tag}",
        f"prerelease={'true' if prerelease else 'false'}",
        f"changed={'true' if changed else 'false'}",
        f"publish={'true' if publish else 'false'}",
    ]
    for line in lines:
        print(line)
    gh_out = Path(os.environ["GITHUB_OUTPUT"]) if os.environ.get("GITHUB_OUTPUT") else None
    if gh_out:
        with gh_out.open("a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")


def cmd_print_tag(args: argparse.Namespace) -> int:
    vf = parse_version_file()
    if vf.is_doc_only:
        assert vf.doc_only is not None
        existing = [
            t.strip() for t in (args.existing_tags or "").split(",") if t.strip()
        ]
        print(choose_doc_tag(vf.version, vf.doc_only, existing))
    else:
        print(ontology_tag(vf.version))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser(
        "validate",
        help="Validate VERSION against RELEASES (use --releases for the PR base copy)",
    )
    p_val.add_argument(
        "--releases",
        default="",
        help="Path to RELEASES to compare against (default: ./RELEASES)",
    )
    p_val.set_defaults(func=cmd_validate)

    p_sug = sub.add_parser(
        "suggest",
        help="Print a suggested next SemVer based on RELEASES",
    )
    p_sug.add_argument("--releases", default="")
    p_sug.add_argument(
        "--full",
        action="store_true",
        help="Suggest a full release instead of a pre-release",
    )
    p_sug.set_defaults(func=cmd_suggest)

    p_apply = sub.add_parser(
        "apply",
        help="Stamp TTL (ontology) and append RELEASES; print release outputs",
    )
    p_apply.add_argument(
        "--existing-tags",
        default="",
        help="Comma-separated existing git tags (for v*-docs-* tag collision)",
    )
    p_apply.set_defaults(func=cmd_apply)

    p_tag = sub.add_parser("print-tag", help="Print the git tag for current VERSION")
    p_tag.add_argument("--existing-tags", default="")
    p_tag.set_defaults(func=cmd_print_tag)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
