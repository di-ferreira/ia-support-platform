# EMSoft Intelligent Support Platform — Brand Spec

Extracted from ERP EMSoft screenshots, institutional site (emsoft.com.br), and design brief.

---

## Brand DNA

Confiança · Estabilidade · Especialização · Tecnologia · Produtividade

A marca EMSoft é um ERP consolidado no mercado brasileiro. O novo SaaS de suporte inteligente deve **modernizar a experiência visual** mantendo a **familiaridade** para os usuários atuais do ERP. O tom é de ferramenta profissional de alta densidade, não de startup.

**Referências de postura:** Linear, Atlassian, Zendesk, Notion, Intercom.

---

## Core palette (OKLch)

Extracted from brand favicon SVG (`favicon_blue.svg` — #063778 navy, #f17318 orange) and logo.

```css
:root {
  /* Neutrals — clean, high-contrast, desktop-first */
  --bg:        oklch(98.5% 0.002 260);
  --surface:   oklch(100% 0 0);
  --fg:        oklch(18% 0.015 260);
  --muted:     oklch(52% 0.01 260);
  --border:    oklch(91% 0.004 260);

  /* Primary — EMSoft brand navy (#063778) */
  --primary:   oklch(34.9% 0.122 258);
  --primary-hover: oklch(28% 0.122 258);
  --primary-light: oklch(87% 0.03 258);

  /* Accent — EMSoft brand orange (#f17318) */
  --accent:    oklch(69.3% 0.179 49);

  /* Semantic — ERP-rooted */
  --success:   oklch(62% 0.18 150);
  --warning:   oklch(72% 0.16 75);
  --danger:    oklch(55% 0.20 29);
  --info:      oklch(60% 0.12 240);

  /* ERP-specific surface tokens for high-density tables/grids */
  --table-stripe: oklch(97% 0.003 260);
  --table-hover:  oklch(95% 0.005 260);
  --sidebar-bg:   oklch(22% 0.02 258);
  --sidebar-fg:   oklch(85% 0.01 258);

  /* Fonts */
  --font-display: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  --font-body:    'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', 'IBM Plex Mono', ui-monospace, Menlo, monospace;
}
```

---

## Full color scale (OKLch)

### Primary Blue (#063778 — extracted from favicon SVG)

| Step | OKLch |
|------|-------|
| 50   | oklch(95.0% 0.043 255) |
| 100  | oklch(88.0% 0.052 255) |
| 200  | oklch(78.0% 0.065 256) |
| 300  | oklch(65.0% 0.082 256) |
| 400  | oklch(50.0% 0.102 257) |
| 500  | oklch(34.9% 0.122 258) |
| 600  | oklch(28.0% 0.098 258) |
| 700  | oklch(22.0% 0.077 257) |
| 800  | oklch(17.0% 0.059 257) |
| 900  | oklch(12.0% 0.042 257) |

### Semantic colors

| Role | 500 OKLch | 100 (light) | 800 (dark) |
|------|-----------|-------------|------------|
| Danger | oklch(55% 0.20 29) | oklch(93% 0.04 29) | oklch(30% 0.18 29) |
| Warning | oklch(72% 0.16 75) | oklch(95% 0.04 75) | oklch(35% 0.14 75) |
| Success | oklch(62% 0.18 150) | oklch(93% 0.04 150) | oklch(30% 0.16 150) |
| Info | oklch(60% 0.12 240) | oklch(93% 0.03 240) | oklch(30% 0.10 240) |

---

## Typography

- **Display/Body:** Inter (system sans-serif fallback)
- **Mono:** JetBrains Mono (code, IDs, tabular data)
- **Scale:** 1.25 (major third)
- **Weights:** 400 (body), 500 (labels/nav), 600 (headings)

### Type scale

| Token | Size | Weight | Line Height | Letter Spacing |
|-------|------|--------|-------------|----------------|
| h1 | 40px | 600 | 1.2 | -0.02em |
| h2 | 32px | 600 | 1.25 | -0.015em |
| h3 | 24px | 600 | 1.3 | -0.01em |
| h4 | 20px | 600 | 1.35 | 0 |
| body | 15px | 400 | 1.5 | 0 |
| small | 13px | 400 | 1.5 | 0.01em |
| caption | 12px | 500 | 1.4 | 0.015em |
| label | 14px | 500 | 1.4 | 0.02em |
| overline | 11px | 600 | 1.3 | 0.08em |

---

## Spacing scale

4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 · 64 · 80 · 96

---

## Border radius

| Token | Value |
|-------|-------|
| xs | 3px |
| sm | 5px |
| md | 8px |
| lg | 12px |
| xl | 16px |

---

## Shadow scale

| Token | Value |
|-------|-------|
| sm | 0 1px 2px rgba(0,0,0,0.05) |
| md | 0 2px 8px rgba(0,0,0,0.08) |
| lg | 0 4px 16px rgba(0,0,0,0.10) |
| xl | 0 8px 32px rgba(0,0,0,0.12) |

---

## Posture rules

1. **ERP-rooted**: high-density layouts, robust grids, extensive data tables, desktop-first
2. **One accent color** used at most 2x per view — brand orange (#f17318) for highlights
3. **No decorative gradients** — flat surfaces with precise borders do the work
4. **Sidebar navigation** in deep navy (like the current ERP) — the user's muscle memory lives here
5. **Tabular numerics** on all data — `font-variant-numeric: tabular-nums`
6. **Hairline borders** (1px) between rows — no row striping without alternating color
7. **Status pills** for Kanban columns — tinted backgrounds, no icons needed
8. **Atendimento/WhatsApp** components use the same design language — chat bubbles, timeline, IA summary cards
9. **Dark mode ready** — all tokens have dark variants (future phase)
10. **Tailwind/Shadcn compatible** — token naming follows CSS custom property convention
