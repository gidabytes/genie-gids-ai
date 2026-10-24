# Genie — GIDS AI Assistant · website

The public website for **Genie — GIDS AI Assistant**, a personal, privacy-first AI assistant that is part of the GIDS (Global Infrastructure Detection System) initiative. It has three pages, a homepage, the Terms of Service and the Privacy Statement, published with GitHub Pages.

This is a documentation and branding site only. The Genie app, its settings, models, databases and credentials never live here.

| Page | Address |
|---|---|
| Homepage | https://gidabytes.github.io/genie-gids-ai-site/ |
| Terms of Service | https://gidabytes.github.io/genie-gids-ai-site/terms-of-service.html |
| Privacy Statement | https://gidabytes.github.io/genie-gids-ai-site/privacy-statement.html |

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
.github/workflows/pages.yml             checks, then publishes to GitHub Pages
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

Every push to `main` runs the **Publish website** workflow:

1. `python3 scripts/check-site.py --assemble _site` checks the whole repository, then copies only the public files into `_site` and checks that copy.
2. The upload step packages `_site`, and the deploy step publishes it to GitHub Pages.

Pull requests run the check without publishing. The workflow uses GitHub's built-in token with read-only repository access; only the deploy job gets the two Pages permissions it needs.

One-time repository setting: **Settings → Pages → Build and deployment → Source: GitHub Actions**.

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
  curl -sS -o /dev/null -w "%{http_code}  %{url_effective}\n" "https://gidabytes.github.io/genie-gids-ai-site/$page"
done
```

Each line should start with `200`.

## If a deployment fails

Open the **Actions** tab, select the failed **Publish website** run, and read its annotations and summary.

| What you see | What to do |
|---|---|
| An error from the check step | Fix the file and line it names, then push again. |
| The deploy step fails with status 404 | Pages is not set to use GitHub Actions: Settings → Pages → Source: GitHub Actions. |
| "Branch is not allowed to deploy to github-pages" | Publish from `main`; the `github-pages` environment only accepts the default branch. |

## Rolling back

- **Undo a change:** `git revert <commit>` and push. The workflow republishes the earlier content.
- **Take the site offline:** Settings → Pages → Unpublish site, or `gh api -X DELETE repos/{owner}/genie-gids-ai-site/pages`.
- Neither affects the Genie app on the computer.

## Microsoft Entra branding values

| Field | Value |
|---|---|
| Name | Genie — GIDS AI Assistant |
| Logo | `assets/genie-gidsai-logo-entra-215.png` (upload the file) |
| Home page URL | https://gidabytes.github.io/genie-gids-ai-site/ |
| Terms of service URL | https://gidabytes.github.io/genie-gids-ai-site/terms-of-service.html |
| Privacy statement URL | https://gidabytes.github.io/genie-gids-ai-site/privacy-statement.html |

## Security

See [SECURITY.md](SECURITY.md).

## License

No license has been chosen for this site's content yet. That is the owner's decision.
