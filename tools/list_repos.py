"""List every juw12 repository with the fields needed to plan the theme scan."""
import json
import subprocess
import sys
from pathlib import Path

FIELDS = "name,visibility,isFork,isArchived,pushedAt,description,homepageUrl,primaryLanguage,defaultBranchRef"


def main() -> int:
    result = subprocess.run(
        ["gh", "repo", "list", "juw12", "--limit", "300", "--json", FIELDS],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=50,
    )
    if result.returncode != 0:
        print("gh failed:", result.stderr.strip()[:500])
        return 1

    repos = json.loads(result.stdout)
    repos.sort(key=lambda repo: repo["pushedAt"], reverse=True)
    Path("data").mkdir(exist_ok=True)
    Path("data/repos.json").write_text(json.dumps(repos, indent=1), encoding="utf-8")

    public_count = sum(1 for repo in repos if repo["visibility"] == "PUBLIC")
    print(f"{len(repos)} repos, {public_count} public")
    for repo in repos:
        language = (repo.get("primaryLanguage") or {}).get("name", "-")
        flags = ""
        if repo["isFork"]:
            flags += " fork"
        if repo["isArchived"]:
            flags += " archived"
        print(
            f"{repo['name']:<34} {repo['visibility'][:4]:<5} {repo['pushedAt'][:10]} "
            f"{language:<11}{flags} {repo.get('homepageUrl') or ''}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
