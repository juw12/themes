"""Fetch live facts (stars, licence, last push, description) for candidate design-template repos.

The candidate list is hand-picked by category; this script only keeps what GitHub confirms today.
Writes data/top_repos.json. Read-only.
"""
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CANDIDATES = {
    "App starters you can clone": [
        "shadcn-ui/taxonomy",
        "vercel/next.js",
        "t3-oss/create-t3-app",
        "ixartz/SaaS-Boilerplate",
        "ixartz/Next-js-Boilerplate",
        "satnaing/shadcn-admin",
        "Kiranism/next-shadcn-dashboard-starter",
        "TailAdmin/tailadmin-free-tailwind-dashboard-template",
        "vercel/ai-chatbot",
        "vercel/commerce",
        "shadcn-ui/next-template",
        "coreui/coreui-free-bootstrap-admin-template",
        "ColorlibHQ/AdminLTE",
        "tabler/tabler",
        "akveo/ngx-admin",
        "flatlogic/react-material-admin",
        "themesberg/flowbite-admin-dashboard",
        "cruip/open-react-template",
        "cruip/tailwind-landing-page-template",
        "onwidget/astrowind",
        "withastro/starlight",
        "h5bp/html5-boilerplate",
        "pure-admin/vue-pure-admin",
        "vbenjs/vue-vben-admin",
        "refinedev/refine",
        "marmelab/react-admin",
        "nextjs/saas-starter",
        "tauri-apps/create-tauri-app",
        "expo/expo",
    ],
    "Component systems (copy the parts)": [
        "shadcn-ui/ui",
        "radix-ui/primitives",
        "saadeghi/daisyui",
        "tailwindlabs/tailwindcss",
        "tailwindlabs/headlessui",
        "mui/material-ui",
        "ant-design/ant-design",
        "chakra-ui/chakra-ui",
        "mantinedev/mantine",
        "heroui-inc/heroui",
        "themesberg/flowbite",
        "twbs/bootstrap",
        "picocss/pico",
        "primer/css",
        "adobe/react-spectrum",
        "carbon-design-system/carbon",
        "microsoft/fluentui",
        "shoelace-style/shoelace",
        "ariakit/ariakit",
        "magicuidesign/magicui",
        "ionic-team/ionic-framework",
        "argyleink/open-props",
        "nuxt/ui",
        "kevquirk/simple.css",
        "oxalorg/sakura",
        "andybrewer/mvp",
        "nanostores/nanostores",
    ],
    "Themes and tokens (palettes to learn from)": [
        "catppuccin/catppuccin",
        "dracula/dracula-theme",
        "nordtheme/nord",
        "morhetz/gruvbox",
        "folke/tokyonight.nvim",
        "rose-pine/rose-pine-theme",
        "radix-ui/colors",
        "primer/primitives",
        "style-dictionary/style-dictionary",
        "amzn/style-dictionary",
        "tokens-studio/figma-plugin",
        "design-tokens/community-group",
        "system-ui/theme-ui",
        "material-foundation/material-color-utilities",
        "yeun/open-color",
        "tinted-theming/schemes",
        "altercation/solarized",
        "jln13x/ui.jln.dev",
        "jnsahaj/tweakcn",
    ],
    "Design guidance and lists": [
        "alexpate/awesome-design-systems",
        "gztchan/awesome-design",
        "goabstract/Awesome-Design-Tools",
        "bradtraversy/design-resources-for-developers",
        "brillout/awesome-react-components",
        "birobirobiro/awesome-shadcn-ui",
        "aniftyco/awesome-tailwindcss",
        "sindresorhus/awesome",
        "uswds/uswds",
        "alphagov/govuk-frontend",
        "google/material-design-icons",
        "lucide-icons/lucide",
        "tabler/tabler-icons",
        "phosphor-icons/homepage",
        "rsms/inter",
        "vercel/geist-font",
        "google/fonts",
    ],
}


def fetch(full_name: str) -> dict | None:
    result = None
    for attempt in range(3):
        result = subprocess.run(["gh", "api", f"repos/{full_name}"], capture_output=True, timeout=60)
        if result.returncode == 0:
            break
        if b"Not Found" in result.stdout or b"Not Found" in result.stderr:
            return None
        time.sleep(2 + attempt * 2)
    if result is None or result.returncode != 0:
        print("failed:", full_name, result.stderr.decode("utf-8", "replace").strip()[:120], flush=True)
        return None
    data = json.loads(result.stdout)
    return {
        "full_name": data["full_name"],
        "asked_as": full_name,
        "url": data["html_url"],
        "stars": data["stargazers_count"],
        "licence": (data.get("license") or {}).get("spdx_id") or "none stated",
        "pushed": data["pushed_at"][:10],
        "archived": data["archived"],
        "is_template": data.get("is_template", False),
        "description": (data.get("description") or "").strip(),
        "homepage": data.get("homepage") or "",
    }


def main() -> int:
    output = {}
    missing = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for category, names in CANDIDATES.items():
            found = []
            seen = set()
            for name, facts in zip(names, pool.map(fetch, names)):
                if facts is None:
                    missing.append(name)
                    continue
                if facts["full_name"].lower() in seen:
                    continue
                seen.add(facts["full_name"].lower())
                found.append(facts)
            found.sort(key=lambda item: item["stars"], reverse=True)
            output[category] = found
    Path("data/top_repos.json").write_text(json.dumps(output, indent=1, ensure_ascii=False), encoding="utf-8")
    for category, items in output.items():
        print(f"\n{category}")
        for item in items:
            flags = " ARCHIVED" if item["archived"] else ""
            flags += " TEMPLATE" if item["is_template"] else ""
            print(f"  {item['stars']:>7} {item['full_name']:<52} {item['licence']:<12} {item['pushed']}{flags}")
    print("\nnot found:", ", ".join(missing) or "none")
    print("ALL_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
