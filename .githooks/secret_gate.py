"""Pre-commit secret gate (installed by repo-kickoff). Scans staged content."""
import re, subprocess, sys
NAME = re.compile(r"(^|/)(\.env(\..+)?|[^/]+\.env|[^/]*secrets?(\.[^/]*)?\.(json|ya?ml|toml|ini|cfg|txt|env|bat|ps1|sh)"
                  r"|client_secret[^/]*\.json|\.?credentials?(\.[^/]*)?\.(json|ya?ml|toml|ini)|[^/]*\.(pem|key|p12|pfx)"
                  r"|id_rsa[^/]*|\.netrc|\.npmrc|\.pypirc)$", re.I)
TEMPLATE = re.compile(r"\.example$|\.sample$|\.template$", re.I)  # exempt from the NAME check only; content is still scanned
SELF = ".githooks/secret_gate.py"  # the gate itself (it holds the patterns), at the repo root only
TEXT = re.compile(
    r"(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-(ant-)?[A-Za-z0-9_-]{24,}"
    r"|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(password|passwd|pwd|token|api_key|apikey|secret)\s*[=:]\s*['\"](?![$%{<])[^'\"\s]{6,}['\"])", re.I)
ENV = re.compile(r"^\s*(export\s+)?[A-Z][A-Z0-9_]*(API_KEY|TOKEN|SECRET|PASSWORD)\s*=\s*[^\s\x27\x22$]{16,}")  # unquoted env-style value; case-sensitive, so it needs no ignorecase
def git(*a):  # fail closed: a git error must never look like "no staged files"
    r = subprocess.run(["git", *a], capture_output=True)
    if r.returncode != 0:
        print(f"secret gate: `git {a[0]}` failed - commit refused (fail-closed)", file=sys.stderr)
        sys.exit(1)
    return r.stdout
hits = []
# A C M R T: added, copied, modified, renamed (new path), type-changed. Only deletions are left out.
for path in git("diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z").decode().split("\0"):
    if not path or path == SELF:
        continue
    if NAME.search(path) and not TEMPLATE.search(path):
        hits.append(f"{path}: file name looks like a secret")
        continue
    text = git("show", f":{path}").decode("utf-8", errors="replace")  # not UTF-8 is scanned too, never skipped
    for i, line in enumerate(text.splitlines(), 1):
        if (TEXT.search(line) or ENV.search(line)) and not line.rstrip().endswith("secret-gate: allow"):
            hits.append(f"{path}:{i}: looks like a secret (value not shown)")
if hits:
    print("secret gate: commit REFUSED", *hits, "Move the value to an ignored file or env var.", sep="\n  ", file=sys.stderr)
    sys.exit(1)
