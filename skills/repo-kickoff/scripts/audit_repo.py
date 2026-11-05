"""Audit a git repo's README, requirements and .gitignore against the code. Read-only.

Usage: python audit_repo.py <repo-path> [--json]
Exit code: 0 = no findings, 1 = findings, 2 = usage error.

Checks
  REQ  third-party imports (AST) vs requirements.txt: missing, unused, unpinned
  DOC  README references `path` and `path:LINE[-LINE]`: file exists, line in range
  IGN  tracked files that .gitignore says to ignore; secret-looking tracked files
       and contents; tracked files over 5 MB
"""
import ast
import importlib.metadata as md
import json
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # python -I ignores PYTHONIOENCODING

# Keep NAME/TEXT/ENV identical to the gate in install_secret_gate.py (test_secret_gate.py checks both agree).
SECRET_NAME = re.compile(r"(^|/)(\.env(\..+)?|[^/]+\.env|[^/]*secrets?(\.[^/]*)?\.(json|ya?ml|toml|ini|cfg|txt|env|bat|ps1|sh)"
                         r"|client_secret[^/]*\.json|\.?credentials?(\.[^/]*)?\.(json|ya?ml|toml|ini)|[^/]*\.(pem|key|p12|pfx)"
                         r"|id_rsa[^/]*|\.netrc|\.npmrc|\.pypirc)$", re.I)
SECRET_TEXT = re.compile(
    r"(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-(ant-)?[A-Za-z0-9_-]{24,}"
    r"|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(password|passwd|pwd|token|api_key|apikey|secret)\s*[=:]\s*['\"](?![$%{<])[^'\"\s]{6,}['\"])", re.I)  # "$VAR", "%VAR%", "{x}", "<x>" are references
SECRET_ENV = re.compile(r"^\s*(export\s+)?[A-Z][A-Z0-9_]*(API_KEY|TOKEN|SECRET|PASSWORD)\s*=\s*[^\s\x27\x22$]{16,}")  # unquoted env-style value; case-sensitive, so it needs no ignorecase
# Same exemptions as the installed gate: templates and the gate's own source are not secrets.
SAFE_NAME = re.compile(r"\.example$|\.sample$|\.template$|(^|/)\.githooks/secret_gate\.py$", re.I)
BIG = 5 * 1024 * 1024
# import name -> distribution name where they differ and the package may not be installed here
KNOWN = {"sklearn": "scikit-learn", "cv2": "opencv-python", "PIL": "pillow", "yaml": "pyyaml",
         "bs4": "beautifulsoup4", "dotenv": "python-dotenv", "psycopg2": "psycopg2-binary",
         "docx": "python-docx", "fpdf": "fpdf2", "webview": "pywebview", "googleapiclient": "google-api-python-client"}
# namespace packages: several distributions share one top-level name, so map by the longest module prefix
NAMESPACE = {"google.oauth2": "google-auth", "google.auth": "google-auth", "google.protobuf": "protobuf",
             "google.cloud.storage": "google-cloud-storage", "google.cloud.bigquery": "google-cloud-bigquery",
             "google.generativeai": "google-generativeai", "google.genai": "google-genai"}


def import_key(module):
    """The name a requirement is checked under: the namespace distribution for google.*, else the top-level name."""
    for prefix in sorted(NAMESPACE, key=len, reverse=True):
        if module == prefix or module.startswith(prefix + "."):
            return NAMESPACE[prefix]
    return module.split(".")[0]


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def tracked(repo):
    return [p for p in git(repo, "ls-files", "-z").split("\0") if p]


def check_requirements(repo, files):
    findings = []
    # Every folder that holds Python code is first-party, so the project's own package in a
    # src/ layout (src/<pkg>/) is not reported as a missing dependency.
    local = {Path(f).parts[0].removesuffix(".py") for f in files} | {Path(f).stem for f in files if f.endswith(".py")} \
        | {d for f in files if f.endswith(".py") for d in Path(f).parent.parts}
    imports = {}
    for f in files:
        if not f.endswith(".py"):
            continue
        try:
            tree = ast.parse((repo / f).read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as e:
            findings.append(("REQ", "high", f"{f}:{e.lineno}", f"does not parse: {e.msg}"))
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for n in names:
                top = n.split(".")[0]
                if top in sys.stdlib_module_names or top in local or top == "__future__":
                    continue
                imports.setdefault(import_key(n), f"{f}:{node.lineno}")
    dist_of = {k: v[0] for k, v in md.packages_distributions().items() if v}
    wanted = {norm(KNOWN.get(t, t if t in NAMESPACE.values() else dist_of.get(t, t))): (t, where)
              for t, where in imports.items()}

    # Dependencies may live in requirements*.txt anywhere in the repo (runtime, dev, optional, or a
    # second environment such as worker/requirements.txt for a container) and/or pyproject.toml.
    req_files = sorted(repo / f for f in files if Path(f).name.startswith("requirements") and f.endswith(".txt"))
    listed = {}  # dist -> (where, version spec)
    for rf in req_files:
        rel = rf.relative_to(repo).as_posix()
        for i, line in enumerate(rf.read_text(encoding="utf-8").splitlines(), 1):
            line = line.split("#")[0].strip()
            if not line or line.startswith("-"):
                continue
            m = re.match(r"([A-Za-z0-9_.\-]+)(\[.*\])?\s*(.*)", line)
            if m:
                listed.setdefault(norm(m.group(1)), (f"{rel}:{i}", m.group(3)))
    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        import tomllib
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        specs = list(data.get("project", {}).get("dependencies", []))
        for group in list(data.get("project", {}).get("optional-dependencies", {}).values()) + \
                list(data.get("dependency-groups", {}).values()):
            specs += [s for s in group if isinstance(s, str)]
        for s in specs:
            m = re.match(r"([A-Za-z0-9_.\-]+)(\[.*\])?\s*(.*)", s)
            if m:
                listed.setdefault(norm(m.group(1)), ("pyproject.toml", m.group(3).split(";")[0].strip()))
    if not req_files and not pyproject.exists():
        if wanted:
            findings.append(("REQ", "high", "requirements.txt", f"missing, but code imports {len(wanted)} third-party packages"))
        return findings, wanted
    for dist, (top, where) in sorted(wanted.items()):
        if dist not in listed:
            findings.append(("REQ", "high", where, f"imports `{top}` but no requirements file or pyproject lists `{dist}`"))
    for dist, (where, spec) in sorted(listed.items()):
        if dist not in wanted:
            findings.append(("REQ", "low", where, f"`{dist}` is listed but never imported (unused, or a plugin/engine — check)"))
        elif not spec.startswith("=="):
            findings.append(("REQ", "info", where, f"`{dist}` not pinned (`{spec or 'no version'}`); apps usually pin with ==, libraries use ranges — check the file states the choice"))
    if not re.search(r"python_requires|requires-python|^python\s*[=<>]", "\n".join(
            p.read_text(encoding="utf-8", errors="replace") for p in [*req_files, pyproject] if p.exists()), re.I | re.M) \
            and not (repo / ".python-version").exists():
        findings.append(("REQ", "medium", "repo", "no Python version stated (.python-version or requires-python) — installs can fail on an older Python"))
    return findings, wanted


REF = re.compile(r"`([A-Za-z0-9_./\\-]+\.[A-Za-z0-9]{1,5})(?::(\d+)(?:-(\d+))?)?`")
LINK = re.compile(r"\]\((?!https?://|#|mailto:)([^)\s#]+)")


def check_readme(repo, files):
    findings = []
    readme = next((repo / f for f in ("README.md", "readme.md", "README.MD") if (repo / f).exists()), None)
    if readme is None:
        return [("DOC", "high", "README.md", "missing")]
    known = set(files) | {str(Path(f).as_posix()) for f in files}
    names = {Path(f).name: f for f in files}
    for i, line in enumerate(readme.read_text(encoding="utf-8").splitlines(), 1):
        for m in REF.finditer(line):
            ref, a, b = m.group(1).replace("\\", "/"), m.group(2), m.group(3)
            target = ref if ref in known else names.get(ref) if "/" not in ref else None
            if target is None:
                if a or "/" in ref:
                    findings.append(("DOC", "info", f"{readme.name}:{i}", f"refers to `{ref}`, not in the repo — fine only if the README says it is absent"))
                continue
            if a:
                n = len((repo / target).read_text(encoding="utf-8", errors="replace").splitlines())
                last = int(b or a)
                if last > n:
                    findings.append(("DOC", "high", f"{readme.name}:{i}", f"`{ref}:{a}{'-' + b if b else ''}` but the file has {n} lines"))
                else:
                    findings.append(("DOC", "verify", f"{readme.name}:{i}", f"`{target}:{a}{'-' + b if b else ''}` exists — open those lines and confirm they show what this README line claims"))
        for m in LINK.finditer(line):
            ref = m.group(1).replace("\\", "/")
            if not (repo / ref).exists():
                findings.append(("DOC", "medium", f"{readme.name}:{i}", f"link to `{ref}` which does not exist"))
    return findings


def check_ignore(repo, files):
    findings = []
    for f in [p for p in git(repo, "ls-files", "-z", "-i", "-c", "--exclude-standard").split("\0") if p]:
        findings.append(("IGN", "medium", f, "tracked although .gitignore ignores it (git rm --cached?)"))
    if not (repo / ".gitignore").exists():
        findings.append(("IGN", "high", ".gitignore", "missing"))
    for f in files:
        p = repo / f
        if SAFE_NAME.search(f):
            continue
        if SECRET_NAME.search(f):
            findings.append(("IGN", "high", f, "tracked file name looks like a secret"))
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > BIG:
            findings.append(("IGN", "medium", f, f"tracked file is {size / 1048576:.1f} MB"))
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if (SECRET_TEXT.search(line) or SECRET_ENV.search(line)) and not line.rstrip().endswith("secret-gate: allow"):
                findings.append(("IGN", "high", f"{f}:{i}", "line looks like a secret (value not printed)"))
    return findings


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    repo = Path(args[0]).resolve()
    files = tracked(repo)
    req, wanted = check_requirements(repo, files)
    findings = req + check_readme(repo, files) + check_ignore(repo, files)
    order = {"high": 0, "medium": 1, "verify": 2, "low": 3, "info": 4}
    findings.sort(key=lambda x: (order[x[1]], x[0], x[2]))
    if "--json" in sys.argv:
        print(json.dumps([dict(zip(("check", "severity", "where", "what"), f)) for f in findings], ensure_ascii=False, indent=1))
    else:
        print(f"repo {repo} | {len(files)} tracked files | {len(wanted)} third-party imports")
        for c, s, w, t in findings:
            print(f"[{s:6}] {c}  {w}  {t}")
        counts = {s: sum(1 for f in findings if f[1] == s) for s in order}
        print("findings: " + ", ".join(f"{s} {counts[s]}" for s in order))
    sys.exit(1 if any(f[1] in ("high", "medium") for f in findings) else 0)


if __name__ == "__main__":
    main()
