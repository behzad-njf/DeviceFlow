# DeviceFlow Landing

Production marketing site for [DeviceFlow](https://github.com/behzad-njf/DeviceFlow) — an open-source, self-hosted Android SMS gateway and device automation platform.

Built with **Astro** (`output: 'static'`), self-hosted fonts, `astro:assets` image optimization, sitemap, JSON-LD, and near-zero JS on first paint.

## Quick start

```bash
cd landing
cp .env.example .env   # optional; defaults match production URLs
npm install
npm run dev            # http://localhost:4321
```

## Scripts

| Command           | Description                      |
|-------------------|----------------------------------|
| `npm run dev`     | Local dev server with HMR        |
| `npm run build`   | Static production build → `dist/`|
| `npm run preview` | Preview the production build     |

## Environment

See `.env.example`:

| Variable | Purpose |
|----------|---------|
| `PUBLIC_SITE_URL` | Canonical origin (sitemap, OG, JSON-LD) |
| `PUBLIC_GITHUB_URL` | Product repository |
| `PUBLIC_GITHUB_PROFILE_URL` | Author GitHub profile |
| `PUBLIC_LINKEDIN_URL` | Author LinkedIn |
| `PUBLIC_LICENSE_URL` | License link |
| `PUBLIC_NOTICE_URL` | NOTICE attribution link |

All `PUBLIC_*` values are inlined at **build** time.

## Architecture (landing)

```
src/
  assets/images/     # Icon, Banner, Dashboard (astro:assets)
  components/        # Sections + SVG illustrations
  data/content.ts    # Features, guide, use cases (i18n-ready)
  layouts/           # BaseLayout (SEO, fonts, JSON-LD)
  pages/index.astro  # Single long landing page
  styles/global.css  # Tokens, reveal, reduced-motion
public/robots.txt
```

- **English primary**; content lives in `src/data/content.ts` for a future `fa` locale.
- **Partial hydration**: no React islands. Tiny inline `<script>` for IntersectionObserver reveals + pausing the hero path animation offscreen.
- **Animations**: hero entrance, scroll reveals, signature message-path SVG motion. Honors `prefers-reduced-motion`.

## Deploy

Build static files and serve `dist/` from any CDN/static host:

```bash
npm run build
# deploy dist/
```

Set `PUBLIC_SITE_URL` to the public origin before building so sitemap, canonical, and Open Graph URLs are correct.

Suggested Nginx/Caddy: cache hashed `/_astro/*` aggressively; serve `index.html` with a short TTL.

## Attribution

DeviceFlow is licensed under **Apache License 2.0**. Redistribution and derivative works must retain attribution per `NOTICE`:

> Based on DeviceFlow — https://github.com/behzad-njf/DeviceFlow

This landing credits the repo in the footer and CTA.

## Lighthouse checklist

Targets (desktop): **Performance ≥ 95 · SEO ≥ 95 · Accessibility ≥ 95**

Before measuring, run `npm run build && npm run preview` and audit the preview URL (not `astro dev`).

### Performance
- [ ] LCP is brand text or optimized hero visual (not a huge unoptimized PNG)
- [ ] Banner/Dashboard served as AVIF/WebP via `astro:assets` with width/height
- [ ] Below-fold images use `loading="lazy"`
- [ ] Almost no JS on first paint (check Network → JS)
- [ ] Fonts self-hosted with `font-display: swap` (Syne + Figtree variable)
- [ ] CSS inlined/critical via Astro `inlineStylesheets: 'auto'`
- [ ] No layout shift from images or late fonts (CLS)

### SEO
- [ ] Title + meta description (~155 chars)
- [ ] Canonical URL matches `PUBLIC_SITE_URL`
- [ ] `robots.txt` + `sitemap-index.xml` present
- [ ] Open Graph + Twitter cards use Banner
- [ ] JSON-LD: WebSite, Organization, SoftwareApplication
- [ ] Single H1; logical H2/H3; internal anchors `#features` `#guide` `#use-cases` `#cta`
- [ ] Meaningful `alt` on images / `aria-label` on SVG art

### Accessibility
- [ ] Skip link works
- [ ] Focus visible on links/buttons
- [ ] Contrast teal/slate on canvas passes AA
- [ ] `prefers-reduced-motion` disables non-essential motion
- [ ] Landmark regions: `header`, `main`, `footer`, labelled sections

### Manual spot checks
- [ ] Mobile: hero stacks, CTAs tappable, mosaic becomes 1 column
- [ ] GitHub / LinkedIn / License / NOTICE links resolve
- [ ] Message-path animation pauses when scrolled away

## Phases

See [PHASES.md](./PHASES.md) for the build plan and deliverable checklist.
