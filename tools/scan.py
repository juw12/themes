"""Download the files that define each juw12 project's look (design.md, CSS, index.html).

Reads data/repos.json (from list_repos.py). Writes data/raw/<repo>/<flattened path> and
data/scan.json (what was fetched per repo). Read-only against GitHub.
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OWNER = "juw12"
RAW_DIR = Path("data/raw")
MAX_FILE_BYTES = 600_000
SKIP_PARTS = re.compile(
    r"(^|/)(node_modules|vendor|vendors|dist|build|\.github|tests?|fixtures|history|hone|bracket|"
    r"dir-[a-z]|archive|old|backup|_backups|third_party|site-packages|coverage|examples?)(/|$)",
    re.IGNORECASE,
)
CSS_PRIORITY = [
    "tokens.css",
    "theme.css",
    "styles.css",
    "style.css",
    "app.css",
    "main.css",
    "index.css",
    "base.css",
    "global.css",
    "globals.css",
]
SKIP_FILE = Path("data/skip_repos.txt")
# Repos that are not apps (notes, profile). One name per line in data/skip_repos.txt, kept out of git.
SKIP_REPOS = {".github", OWNER} | (
    set(SKIP_FILE.read_text(encoding="utf-8").split()) if SKIP_FILE.exists() else set()
)


def gh_api(endpoint: str, raw: bool = False) -> tuple[int, bytes]:
    command = ["gh", "api", endpoint]
    if raw:
        command += ["-H", "Accept: application/vnd.github.raw"]
    result = subprocess.run(command, capture_output=True, timeout=60)
    return result.returncode, result.stdout


def depth(path: str) -> int:
    return path.count("/")


def pick_files(tree: list[dict]) -> list[str]:
    blobs = [
        entry
        for entry in tree
        if entry["type"] == "blob"
        and entry.get("size", 0) <= MAX_FILE_BYTES
        and not SKIP_PARTS.search(entry["path"])
        and ".min." not in entry["path"]
    ]
    design_docs = sorted(
        (entry["path"] for entry in blobs if entry["path"].lower().endswith("design.md")),
        key=lambda path: (depth(path), len(path)),
    )[:2]

    html_files = sorted(
        (entry["path"] for entry in blobs if entry["path"].lower().endswith("index.html")),
        key=lambda path: (depth(path), len(path)),
    )[:2]

    def css_rank(path: str) -> tuple[int, int, int]:
        name = path.rsplit("/", 1)[-1].lower()
        priority = CSS_PRIORITY.index(name) if name in CSS_PRIORITY else len(CSS_PRIORITY)
        return (depth(path), priority, len(path))

    css_files = sorted(
        (entry["path"] for entry in blobs if entry["path"].lower().endswith(".css")),
        key=css_rank,
    )[:4]

    # Desktop apps keep the page inside the package (e.g. cairn/web/index.html): allow one more level.
    return design_docs + html_files + css_files


def scan_repo(repo: dict) -> dict:
    name = repo["name"]
    branch = (repo.get("defaultBranchRef") or {}).get("name") or "main"
    record = {
        "repo": name,
        "visibility": repo["visibility"],
        "archived": repo["isArchived"],
        "homepage": repo.get("homepageUrl") or "",
        "description": repo.get("description") or "",
        "pushed": repo["pushedAt"][:10],
        "files": [],
        "error": "",
    }
    code, body = gh_api(f"repos/{OWNER}/{name}/git/trees/{branch}?recursive=1")
    if code != 0:
        record["error"] = "tree failed"
        return record
    tree = json.loads(body).get("tree", [])
    record["tree_size"] = len(tree)

    for path in pick_files(tree):
        code, content = gh_api(f"repos/{OWNER}/{name}/contents/{path}?ref={branch}", raw=True)
        if code != 0 or not content:
            continue
        target = RAW_DIR / name / path.replace("/", "__")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        record["files"].append(path)
    return record


def main() -> int:
    repos = json.loads(Path("data/repos.json").read_text(encoding="utf-8"))
    own_repos = [repo for repo in repos if not repo["isFork"] and repo["name"] not in SKIP_REPOS]
    print(f"scanning {len(own_repos)} own repos", flush=True)

    records = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for index, record in enumerate(pool.map(scan_repo, own_repos), start=1):
            records.append(record)
            print(
                f"{index:>3}/{len(own_repos)} {record['repo']:<28} files={len(record['files'])} {record['error']}",
                flush=True,
            )

    Path("data/scan.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    with_files = sum(1 for record in records if record["files"])
    print(f"ALL_DONE repos={len(records)} with_theme_files={with_files}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
