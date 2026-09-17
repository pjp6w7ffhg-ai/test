# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A static PWA (Progressive Web App) that displays a mobile-optimized digital transit ticket with a live countdown timer. No build step, no framework, no dependencies — just HTML, CSS, and vanilla JavaScript deployed to GitHub Pages.

## Development

**Local preview:** Open HTML files directly in a browser:
```
open index.html
```

**Deploy:** Push to `main` — GitHub Actions automatically deploys to GitHub Pages via `.github/workflows/static.yml`. There is also a convenience script:
```
bash gitpush.sh
```

**Repo topology:** the GitHub remote (`pjp6w7ffhg-ai/test`, deployed at https://pjp6w7ffhg-ai.github.io/test/) is only pushable from the `myhp` box (`ssh myhp`, working copy at `~/joncena` — it holds the GitHub PAT). A Mac clone (e.g. `/Users/rackner/code/joncena`) has `origin` pointed at `myhp:joncena`, not GitHub — committing and pushing from the Mac only updates myhp's copy, not the live site. To actually deploy from the Mac: `scp` the changed file(s) to `myhp:~/joncena/`, then `ssh myhp` and commit + `git push origin main` from there.

**GitHub Pages caching:** every response has `Cache-Control: max-age=600` (10 min), hardcoded by GitHub Pages — there's no way to override it (no custom headers support on GH Pages static hosting). A page reload within ~10 minutes of a push can still serve the old version, and an installed iOS Home Screen web clip can hold onto a stale copy even longer since it doesn't always revalidate on relaunch. If a just-pushed fix "isn't showing up," check `curl -sI <url>` for `age:`/`x-cache:` before assuming the code is wrong — and on iOS, force-quit (swipe away) the Home Screen app before reopening rather than just backgrounding/reopening it.

## Architecture

**Two pages:**
- `index.html` — compact mobile ticket view with QR code, color strips, progress bar, and "Tap to enlarge" link
- `static-details.html` — full-size view; zone number is clickable and cycles 1–11; has an adult count updater

**Timer logic (in both HTML files):**
- 60-minute countdown stored in `localStorage` (`deadlineDate`, `deadlineStart`)
- Auto-resets if 10 minutes have elapsed since the deadline
- Updates every second via `setInterval`

**Styling:**
- `static/style.css` — all layout and component styles
- `static/color.css` — CSS custom properties for theming; this is the only file that needs editing to change the color scheme:
  - `--first` — QR code border color (can be any color — pink, blue, etc.)
  - `--stripone` — leftmost color block in the bottom strip bar
  - `--striptwo` — middle color block in the bottom strip bar
  - `--stripthree` — rightmost color block in the bottom strip bar

## Updating Colors from an Image

When the user provides a screenshot or image and says to match colors, **do not read color.css first** — go straight to editing it. The file always has exactly these four variables.

**Visual map of where each variable appears in the ticket screenshot:**
```
┌─────────────────────────────┐
│        [header bar]         │  ← NOT controlled by color.css
│  ┌──────────────────────┐   │
│  │  [QR code border]    │   │  ← --first
│  └──────────────────────┘   │
│                             │
│  [stripone][striptwo][stripthree]  ← bottom strip bar, left to right
└─────────────────────────────┘
```

**Workflow:**
1. Look at the image. For each region above, identify its color.
2. Derive an accurate hex value — study hue, saturation, and brightness precisely. Do not default to generic approximations (e.g. "green" → `#008000`).
3. Edit `static/color.css` — update all four `--variable` values.
4. All four variables must be updated every time, even if some look similar — confirm each one independently.
5. **Verify with Playwright screenshot:**
   - Run `python3 verify-colors.py` — it starts the server if needed and saves screenshots to `/tmp/ticket-index.png` and `/tmp/static-details.png`
   - Read both screenshots and visually confirm QR border and strip bar colors match the target image
   - If colors look wrong, re-examine the image, correct `color.css`, and run the script again
6. Once colors are verified, commit and push:
   ```
   bash gitpush.sh
   ```

**Note:** The header bar color is NOT in color.css and does not need to change.

**Fonts:** SF Pro Display Bold and Medium loaded from `static/` as local `.otf` files via `@font-face`.

## Mobile viewport & iOS PWA rendering (learned 2026-09-16)

`index.html` is a fixed 402×874 CSS-px design canvas (measured from an iPhone 16 Pro screenshot), every element absolutely positioned within it. Getting this to render correctly on arbitrary real phones — especially as an "Add to Home Screen" standalone app — took several rounds. Notes so the next session doesn't relitigate these:

- **Scaling to fit any screen width:** don't use `width=device-width`. Use `<meta name="viewport" content="width=402, user-scalable=0, viewport-fit=cover">` instead — this locks the layout viewport to the design's own 402px width and lets iOS Safari auto-zoom the whole fixed canvas to fit any real screen, no JS scaling hacks needed. `static-details.html` already used this same no-`device-width` trick (it never had the device-width meta at all) — that's why it always rendered correctly while `index.html` (which originally had `width=device-width, initial-scale=1.0`) didn't.
- **`viewport-fit=cover`** is required so the page can paint under the status bar/notch instead of leaving Safari's own chrome above it.
- **Don't set `apple-mobile-web-app-status-bar-style: black-translucent`.** Combined with `viewport-fit=cover`, it hits a confirmed iOS 26.1 WebKit regression (bug 301108) that forces a white/opaque status bar and miscomputes window height. Set it to `default` explicitly (matching `static-details.html`) instead of omitting it, so the intent survives a re-add of the Home Screen icon.
- **`html,body { background: #1C87D8 }`** (matching the header blue), not white — Safari 26 samples the actual body background for its own chrome tinting rather than reliably honoring `theme-color`.
- **The header's `top:91px`/`88px` (title/back-arrow) are correct as originally measured — don't touch them.** They were measured against a screenshot of the *entire* 874px-tall screen, status bar included (874 = 59px status bar + 815px content). Those coordinates only land correctly if the page actually renders *underneath* the status bar (`black-translucent` mode, `env(safe-area-inset-top)` = 59px). Since `black-translucent` is broken (previous bullet), the page instead renders *below* the status bar (`env(safe-area-inset-top)` = 0), which — left unaddressed — shifts the entire header 59px too low and clips the bottom ~59px of the canvas (page dot, card's bottom edge) against `overflow:hidden`. Fix the canvas's position, not the header's: `.main-bg { margin-top: calc(env(safe-area-inset-top, 0px) - 59px) }`. In default mode that's `-59px` (shifts the whole canvas up so the original coordinates land correctly, 815px of canvas fits the 815px of usable view); in a hypothetical working translucent mode it's `0px` (unchanged). A previous attempt fixed this by changing the header's own `top` to `calc(env(safe-area-inset-top, 20px) + 8px)` — don't do that; it resolves to a too-small ~8px in default mode (detaching the header from the card, which stays fixed at `top:122px`) and doesn't address the bottom-clipping at all.
- **No iOS Simulator on this Mac** — only Xcode Command Line Tools are installed, not full Xcode.app (needed for `simctl`). Playwright (Python, both chromium and webkit) is set up in a scratch venv for layout/overflow sanity checks, but headless engines report `env(safe-area-inset-top)` as `0` and can't reproduce the real on-device status-bar/safe-area behavior — treat headless screenshots as necessary but not sufficient; real fixes in this area need actual on-device (or real Simulator) confirmation.
