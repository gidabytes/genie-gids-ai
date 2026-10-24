# Genie — GIDS AI Assistant · website

The public website for **Genie — GIDS AI Assistant**, a personal, privacy-first AI assistant that is part of the GIDS (Global Infrastructure Detection System) initiative. It has three pages, a homepage, the Terms of Service and the Privacy Statement, published with GitHub Pages.

This is a documentation and branding site only. The Genie app, its settings, models, databases and credentials never live here.

| Page | Address |
|---|---|
| Homepage | https://gidabytes.github.io/genie-gids-ai/ |
| Terms of Service | https://gidabytes.github.io/genie-gids-ai/terms-of-service.html |
| Privacy Statement | https://gidabytes.github.io/genie-gids-ai/privacy-statement.html |

## Important notes

> [!IMPORTANT]
> **Strategic Initiative: Digitization and AI Adoption**
>
> Genie — GIDS AI is a strategic initiative designed to accelerate digital transformation through intelligent automation, AI-assisted decision-making, workflow optimization, and improved digital productivity. The initiative aims to reduce repetitive manual tasks, streamline operational processes, strengthen system visibility, and enable scalable, data-informed decision-making.
>
> The solution prioritizes responsible AI adoption, privacy-by-design, cybersecurity, data governance, human oversight, and controlled integration with existing systems. Its development follows a phased implementation approach, with measurable business value, operational reliability, security validation, and user adoption serving as key success criteria.
>
> The long-term vision is to establish a secure, adaptable AI-enabled ecosystem that supports continuous improvement, operational excellence, knowledge accessibility, and sustainable digital transformation while preserving user control and protecting organizational and personal data.

## What is in this repository

```text
index.html                              homepage
terms-of-service.html                   Terms of Service
privacy-statement.html                  Privacy Statement
assets/site.css                         the only stylesheet
assets/genie-gidsai-logo.svg            supplied logo (unchanged)
assets/genie-gidsai-logo.png            supplied logo, 512x512 (unchanged)
assets/genie-gidsai-logo-entra-215.png  logo for Microsoft Entra: 215x215, no transparency
assets/favicon.svg                      the logo's G mark, for browser tabs
assets/favicon-32.png                   32x32 tab icon for browsers without SVG icons
assets/apple-touch-icon.png             180x180 icon for phones
robots.txt, sitemap.xml                 hints for search engines
.nojekyll                               turns off Jekyll (only matters if publishing from a branch)
scripts/check-site.py                   checks the site before every publish (Python standard library only)
scripts/publish-gh-pages.sh             publishes to the gh-pages branch (used while Actions is unavailable)
.github/workflows/pages.yml             checks, then publishes to GitHub Pages (once Actions is available)
SECURITY.md                             how to report a security problem
```

## Design rules

- No JavaScript, cookies, analytics, web fonts or third-party resources. Every page has a Content-Security-Policy that allows only this site's own stylesheet and images.
- Relative links only, so the same files work on GitHub Pages and in a local preview.
- Accessibility basics: one `<h1>` per page, a skip link, visible focus outlines, alt text, readable contrast, and layouts that work from phone to desktop.
- Verified claims only. The Privacy Statement describes what Genie's code and settings actually do, so update it whenever they change.

## Preview locally

```bash
python3 scripts/check-site.py
python3 -m http.server 8000 --bind 127.0.0.1
```

Open http://127.0.0.1:8000/ in a browser, and stop the server with Ctrl+C.

## How publishing works

GitHub Actions is currently disabled on the owner's GitHub account (GitHub answers "Actions has been disabled for this user"), so the workflow cannot run. Until that is resolved, the site is published from the **`gh-pages` branch**, which holds only the public files. Settings → Pages is set to **Deploy from a branch: `gh-pages` / (root)**.

From a clean checkout of `main`:

```bash
scripts/publish-gh-pages.sh --dry-run   # check, assemble and show what would change
scripts/publish-gh-pages.sh             # the same, then push to gh-pages
```

The script runs `python3 scripts/check-site.py --assemble _site` first, so nothing is published unless every check passes, and it refuses to run with uncommitted changes, so the live site always matches a commit.

**Once Actions is available again**, switch to the workflow: Settings → Pages → Build and deployment → Source: **GitHub Actions**. From then on every push to `main` runs **Publish website** (`.github/workflows/pages.yml`): it checks the whole repository, copies only the public files into `_site`, checks that copy, and deploys it. Pull requests run the check without publishing. The workflow uses GitHub's built-in token with read-only repository access; only the deploy job gets the two Pages permissions it needs.

## Updating the branding

Replace `assets/genie-gidsai-logo.svg` and `assets/genie-gidsai-logo.png`, then rebuild the derived images. This needs ImageMagick 7, Inkscape and optipng:

```bash
magick -size 512x512 -define gradient:direction=SouthEast gradient:'#080B12-#101B32' \
  assets/genie-gidsai-logo.png -composite -filter Lanczos -resize 215x215 -alpha off -strip \
  PNG24:assets/genie-gidsai-logo-entra-215.png
magick -size 512x512 -define gradient:direction=SouthEast gradient:'#080B12-#101B32' \
  assets/genie-gidsai-logo.png -composite -filter Lanczos -resize 180x180 -alpha off -strip \
  PNG24:assets/apple-touch-icon.png
inkscape assets/favicon.svg --export-type=png --export-filename=assets/favicon-32.png -w 32 -h 32
optipng -quiet -o5 assets/genie-gidsai-logo-entra-215.png assets/apple-touch-icon.png assets/favicon-32.png
python3 scripts/check-site.py
```

`assets/favicon.svg` is the logo's G mark copied by hand; if the mark changes, update it to match. The check script confirms the Entra logo is still exactly 215x215, opaque and under 100 KB.

## Updating the policies

1. Edit the page, keeping every statement true for the current Genie code and settings.
2. Update the effective date (the `<time datetime="...">` element) and the version at the top of the page.
3. Remove an "Owner review" flag only once that decision has been made.
4. Run `python3 scripts/check-site.py` and push. Earlier versions stay in this repository's history.

## Checking the live site

```bash
for page in "" terms-of-service.html privacy-statement.html; do
  curl -sS -o /dev/null -w "%{http_code}  %{url_effective}\n" "https://gidabytes.github.io/genie-gids-ai/$page"
done
```

Each line should start with `200`.

## If a deployment fails

| What you see | What to do |
|---|---|
| `publish-gh-pages.sh` stops with check errors | Fix the file and line it names, commit, and run it again. |
| The live page has not changed a few minutes after publishing | Check the latest Pages build: `gh api repos/{owner}/genie-gids-ai/pages/builds/latest`. |
| "Actions has been disabled for this user" | GitHub has turned off Actions for the account. Keep publishing with the script, or ask GitHub Support to re-enable Actions. |
| With the workflow: an error from the check step | Open the **Actions** tab, read the failed run's annotations, fix the file and line it names, then push again. |
| With the workflow: the deploy step fails with status 404 | Pages is not set to use GitHub Actions: Settings → Pages → Source: GitHub Actions. |

## Rolling back

- **Undo a change:** revert the commit on `main` (through a pull request), then run `scripts/publish-gh-pages.sh` again. Once the workflow is in use, merging the revert republishes automatically.
- **Take the site offline:** Settings → Pages → Unpublish site, or `gh api -X DELETE repos/{owner}/genie-gids-ai/pages`.
- None of this affects the Genie app on the computer.

## Microsoft Entra branding values

| Field | Value |
|---|---|
| Name | Genie — GIDS AI Assistant |
| Logo | `assets/genie-gidsai-logo-entra-215.png` (upload the file) |
| Home page URL | https://gidabytes.github.io/genie-gids-ai/ |
| Terms of service URL | https://gidabytes.github.io/genie-gids-ai/terms-of-service.html |
| Privacy statement URL | https://gidabytes.github.io/genie-gids-ai/privacy-statement.html |

## Security

See [SECURITY.md](SECURITY.md).

## License

No license has been chosen for this site's content yet. That is the owner's decision.
