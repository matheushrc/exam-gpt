---
name: Exam GPT — Manuscrito
description: >-
  Default theme (Manuscrito, light). The system ships three interchangeable
  variants × light/dark — see §2 Theming and the palette tables in §3. These
  front-matter tokens are the DEFAULT look; in code every value is a CSS custom
  property: --color-<token>, --font-<role>, --radius-<size>, --transition-<name>.
colors:
  bg: "#f7f2e9"
  surface: "#efe7d8"
  card: "#fffdf8"
  border: "#e4d9c5"
  hover: "#fffdf8"
  text: "#2c2620"
  text-muted: "#706655"
  accent: "#8a2b2b"
  accent-light: "#f1e0da"
  on-accent: "#fff7f2"
  user-bg: "#8a2b2b"
  user-text: "#fdf3ee"
  error: "#b3261e"
  success: "#2f6d3c"
typography:
  display:
    fontFamily: Spectral
    fontSize: 32px
    fontWeight: "600"
    letterSpacing: -0.4px
  body:
    fontFamily: Spectral
    fontSize: 14.5px
    fontWeight: "400"
    lineHeight: 1.6
  control:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: "500"
  label-caps:
    fontFamily: IBM Plex Sans
    fontSize: 11px
    fontWeight: "600"
    letterSpacing: 1.5px
rounded:
  sm: 7px
  md: 10px
  lg: 16px
transitions:
  fast: 0.15s ease
  med: 0.22s ease
---

# Exam GPT — Design System

This document is the source of truth for the project's visual and interaction
design. It describes the tokens, typography, layout, and component patterns the
UI is built from, and the conventions to follow when adding new screens.

**This file and the live token files are the source of truth.** The design began
as a static mockup (`design/Exam GPT.dc.html`), which has since been
**retired** — the implementation diverged from it, so it was removed to stop it
misleading new work (see [`design/README.md`](design/README.md)). The front
matter and prose here are the contract; `staticfiles/css/tokens.css` is the
implementation of record.

This file follows the [DESIGN.md convention](https://github.com/google-labs-code/design.md)
(YAML token front matter + prose). Because the product is **multi-theme**, the
front matter encodes the **default** variant (Manuscrito, light); the full
variant matrix lives in the palette tables under §3.

---

## 1. Principles

- **One identity, three skins.** The product has a single point of view — a
  scholarly, paper-like "exam bank" — expressed through three interchangeable
  visual variants. New UI must read correctly in all of them, which means
  **always style with tokens, never hard-coded colors or fonts.**
- **Read-first, edit-on-demand.** Content (questions, answers, math) is meant to
  be read like a printed exam. Editing affordances stay quiet until the user
  engages them (e.g. the Markdown _Escrever / Visualizar_ tabs default to the
  rendered view).
- **Serif for substance, sans for chrome.** Display/content uses a serif; UI
  labels, controls, and data use a sans. This split carries the personality.
- **Restraint.** Spend boldness in one place per screen (the signature element);
  keep everything around it disciplined. Cut decoration that doesn't help the
  user understand or act.
- **Quality floor, unannounced.** Responsive to mobile, visible keyboard focus,
  tabular numerals for grades, native controls where they serve (date pickers,
  `title` tooltips).

---

## 2. Theming architecture

Themes are pure CSS custom properties scoped by two attributes on `<html>`:

```html
<html data-variant="manuscrito" data-theme="light"></html>
```

- **`data-variant`** → `manuscrito` | `periodico` | `academico` (palette + fonts)
- **`data-theme`** → `light` | `dark` (resolved value; `system` is resolved to one
  of these at runtime)

Switching is handled by [`staticfiles/js/theme.js`](staticfiles/js/theme.js),
loaded **synchronously in `<head>`** (before paint, to avoid a flash):

| Concern | localStorage key  | Values                             | Default      |
| ------- | ----------------- | ---------------------------------- | ------------ |
| Variant | `pg.themeVariant` | manuscrito / periodico / academico | `manuscrito` |
| Mode    | `pg.themeMode`    | light / dark / system              | `system`     |

`system` mode follows `prefers-color-scheme` live via `matchMedia`. The default
look is **Manuscrito, light** (cream paper / maroon ink). Tokens live in
[`staticfiles/css/tokens.css`](staticfiles/css/tokens.css).

### Adding a screen

Any new template extends `base.html`, which already wires `tokens.css`,
`base.css`, `theme.js`, and the shared shell scripts (`shell-core.js`,
`sidebar-toggle.js`, `settings-modal.js`, `user-menu.js`). You only add your
page-specific CSS in `{% block extra_css %}`. Never re-declare colors/fonts —
consume the variables below.

---

## 3. Color tokens

Every color is a CSS variable. The semantic roles are stable across variants;
only the values change.

| Token                  | Role                                                |
| ---------------------- | --------------------------------------------------- |
| `--color-bg`           | App background (the "paper")                        |
| `--color-surface`      | Recessed surfaces (sidebar, inset rows, menus base) |
| `--color-card`         | Raised surfaces (cards, inputs, dropdowns)          |
| `--color-border`       | Hairlines, input borders, dividers                  |
| `--color-hover`        | Hover background for quiet controls                 |
| `--color-text`         | Primary text ("ink")                                |
| `--color-text-muted`   | Secondary text, labels, captions                    |
| `--color-accent`       | Brand accent — primary actions, links, active state |
| `--color-accent-light` | Accent wash (chips, badges, selected backgrounds)   |
| `--color-on-accent`    | Text/icon on an accent fill                         |
| `--color-user-bg`      | Chat: user bubble background                        |
| `--color-user-text`    | Chat: user bubble text                              |
| `--color-error`        | Errors, destructive hover                           |
| `--color-success`      | Success / confirmation                              |

Derived: `--color-tooltip-bg` / `--color-tooltip-text` (computed from text/bg).
Use `color-mix(in srgb, var(--color-…) N%, …)` for translucent states rather
than new hex values (see error-hover and chat-error patterns in CSS).

### Palettes

**Manuscrito** — warm cream paper, maroon ink. _Spectral / IBM Plex Sans._

| Token        | Light     | Dark      |
| ------------ | --------- | --------- |
| bg           | `#f7f2e9` | `#1b1713` |
| surface      | `#efe7d8` | `#211c16` |
| card         | `#fffdf8` | `#272018` |
| border       | `#e4d9c5` | `#3a3026` |
| text         | `#2c2620` | `#ece2d3` |
| text-muted   | `#706655` | `#a89379` |
| accent       | `#8a2b2b` | `#cf8a6f` |
| accent-light | `#f1e0da` | `#352019` |

**Periódico** — cool newsprint, ink-blue. _Newsreader / Public Sans._

| Token        | Light     | Dark      |
| ------------ | --------- | --------- |
| bg           | `#f5f4ef` | `#13161c` |
| surface      | `#ecebe4` | `#181c23` |
| card         | `#ffffff` | `#1e232c` |
| border       | `#dcdbd1` | `#2d323d` |
| text         | `#1c2230` | `#e7e9ee` |
| text-muted   | `#646a75` | `#99a0ac` |
| accent       | `#27406f` | `#8ba6e0` |
| accent-light | `#e6ebf4` | `#222a3a` |

**Acadêmico** — soft sage paper, forest-green. _Source Serif 4 / Work Sans._

| Token        | Light     | Dark      |
| ------------ | --------- | --------- |
| bg           | `#f2f3f0` | `#121512` |
| surface      | `#e8eae4` | `#171b16` |
| card         | `#ffffff` | `#1c211b` |
| border       | `#d8dbd2` | `#2b302a` |
| text         | `#202620` | `#e6e9e1` |
| text-muted   | `#656a60` | `#98a092` |
| accent       | `#2f5d4e` | `#74b095` |
| accent-light | `#e1ebe4` | `#1e2a23` |

Shared across all variants: `error #b3261e` (light) / `#e0796a` (dark),
`success #2f6d3c` / `#7fb88a`.

---

## 4. Typography

Two roles, swapped per variant. Both are tokens — use the role, not the family.

| Token          | Role                                           | Manuscrito    | Periódico   | Acadêmico      |
| -------------- | ---------------------------------------------- | ------------- | ----------- | -------------- |
| `--font-serif` | Display, headings, question/answer **content** | Spectral      | Newsreader  | Source Serif 4 |
| `--font-sans`  | UI chrome: labels, buttons, inputs, captions   | IBM Plex Sans | Public Sans | Work Sans      |
| `--font-mono`  | Code, raw Markdown editor textareas            | system mono   | system mono | system mono    |

Fonts are loaded once in `base.html` via a single Google Fonts `<link>`
(`display=swap`, all six families). Weights in use: 400/500/600 (serif also 700
for some displays; italics where the family provides them).

**Scale & usage conventions** (not tokenized — applied per component, see CSS):

- Page hero `h1`: serif, ~32px, weight 600, `letter-spacing: -0.4px`.
- Section eyebrow: sans, 11px, `letter-spacing: 2.5px`, uppercase, accent color.
- Field/section labels: sans, 10–11px, `letter-spacing: 1.1–1.5px`, uppercase,
  muted.
- Body / question content: serif, ~14.5px, `line-height: 1.6`.
- Controls & data: sans, 13–15px.
- Grade numbers: `font-variant-numeric: tabular-nums`.

---

## 5. Spacing, radius, motion

Non-color tokens (variant-independent), from `tokens.css`:

```css.
--sidebar-width: 270px;          --radius-sm: 7px;
--sidebar-collapsed-width: 76px; --radius-md: 10px;
--right-panel-width: 320px;      --radius-lg: 16px;
--transition-fast: 0.15s ease;
--transition-med: 0.22s ease;
```

- **Radius:** `sm` for inputs/inner chips, `md` for buttons, larger bespoke radii
  (11–18px) for cards, dropzones, and dropdowns.
- **Transitions:** animate `border-color`, `background`, `color`, `box-shadow`
  with `--transition-fast`. Don't animate layout width with CSS transitions —
  the one exception is the sidebar/right-panel collapse, which uses a damped-
  spring `width` animator (`springWidth` in `shell-core.js`) for a snappier
  feel than a CSS ease. Content inside an animated-width container (labels,
  headers, controls) must be pinned to a fixed width/position based on the
  container's *static* expanded or collapsed size — never `inset: 0` or
  `margin: auto` against the live animated box, or it reflows/drifts mid-fade
  instead of just fading in place (see §11).
- **Spacing:** ad-hoc rem/px per component; content columns cap at ~740px
  (`.upload-inner`) for readability.

---

## 6. Layout

The app is a persistent **sidebar + main** shell, shared by every screen via
partials in `templates/partials/` and the shared shell scripts
(`staticfiles/js/shell-core.js`, `sidebar-toggle.js`, `settings-modal.js`,
`user-menu.js`).

```
┌────────────┬───────────────────────────────────────────┐
│  sidebar   │  chat-main                                 │
│  (270px /  │  ┌───────────────────────────────────────┐│
│   76px     │  │ chat-header (title + subtitle)        ││
│   collapsed)  ├───────────────────────────────────────┤│
│            │  │ chat-body › chat-column › chat-scroll  ││  ← inner scroll
│  brand     │  │   (page content, max ~740px column)   ││
│  nav       │  ├───────────────────────────────────────┤│
│  history   │  │ footer (sticky actions)               ││
│  settings  │  └───────────────────────────────────────┘│
└────────────┴───────────────────────────────────────────┘
```

- The sidebar collapses to icon-only (76px); the chat screen's right-hand
  settings panel collapses to 0 (320px expanded). Both use the same spring
  width animator — see §5. Tooltips use native `title` attributes (do **not**
  reintroduce CSS `::after` tooltips — they get clipped by the sidebar's
  `overflow: hidden`).
- Content scrolls in `.chat-scroll` (an **inner** scroll container), not the
  window — keep this in mind when scripting scroll/scroll-into-view.
- **Mobile (`max-width: 640px`):** the sidebar drops to a bottom tab bar and the
  metadata grid collapses to one column (see `base.css` and
  `apps/upload/static/upload/css/responsive.css` media queries).

---

## 7. Component patterns

Shared primitives live in [`staticfiles/css/base.css`](staticfiles/css/base.css)
and the chat shell, split by concern under
[`apps/chat/static/chat/css/`](apps/chat/static/chat/css/) (`sidebar.css`,
`user-menu.css`, `settings-modal.css`, `chat-area.css`, `right-panel.css`,
`layout.css`, `responsive.css`). Screen-specific components live beside their
app, split by concern under
[`apps/upload/static/upload/css/`](apps/upload/static/upload/css/)
(`upload-intro.css`, `upload-review.css`, `multiselect.css`,
`markdown-editor.css`, `question-editor.css`, `responsive.css`).

- **Buttons** — `.btn-primary` (accent fill, `--color-on-accent` text) and
  `.btn-secondary` (card surface, bordered). Min height 44px; disabled states use
  muted text on border-gray. Icon + label allowed.
- **Inputs** — card background, 1px border, focus → `border-color: accent`, no
  outline. 44px tall for primary fields, 40px for compact (grades). Native
  `type="date"` / `type="number"` are used directly.
- **Chip multiselect** (`.ms*`) — bordered control holding removable chips
  (accent-light) plus a filter input, with an absolutely-positioned dropdown
  (`.ms-menu`). Supports validated custom entries (e.g. professor `@uffs.edu.br`
  emails). Used for professores and cursos.
- **Markdown editor field** (`.mdf*`) — a _Escrever / Visualizar_ segmented tab
  over a mono textarea and a rendered preview. Defaults to preview when content
  exists. This is the standard way to edit any LaTeX/Markdown text.
- **Toggle switch** (`.toggle-switch` + `.toggle-knob`) — accessible
  `role="switch"`, `aria-checked`, `.checked` class drives the knob.
- **Cards** — `--color-card` surface, hairline border, generous radius. Editable
  question cards grow a **maroon left "spine" on `:focus-within`** (the signature
  detail of the review screen — editing feels like marking up an exam).
- **Chat bubbles** — `.chat-bubble.user` (accent fill, right-aligned) /
  `.assistant` (card, bordered) / `.loading` / `.error`.
- **Loading** — `.dot-pulse` three-dot pulse in the accent color.
- **Badges/tags** — accent-light pill for question numbers/points; inline accent
  text + check icon for status ("com gabarito").

---

## 8. Markdown & math rendering

Question enunciados and answers are **Markdown with inline/display LaTeX**.
Rendering uses [marked](https://marked.js.org) + [KaTeX](https://katex.org)
(auto-render), both loaded in `base.html`. Delimiters: `$…$` (inline),
`$$…$$` (display), with `throwOnError: false`. Rendered output goes into an
`.md-content` container. Always render user-editable math through the
`markdownField` preview rather than rolling a one-off.

---

## 9. Voice & copy

- **Language: Brazilian Portuguese.** Sentence case, plain verbs, no filler.
- Name things by what the user controls ("Adicionar ao banco", "Enviar prova"),
  not by system internals.
- An action keeps its name across the flow (button "Adicionar ao banco" →
  resulting state matches).
- Errors state what happened and how to fix it, in the interface's voice; they
  don't apologize and aren't vague. Empty states invite the next action
  (the dropzone, the "Adicionar questão manualmente" button).
- Labels label, captions explain — one job each.

---

## 10. File map

| Path                                                  | Contains                                                       |
| ------------------------------------------------------ | --------------------------------------------------------------- |
| `design/README.md`                                    | Why the original mockup was retired (pointer note)             |
| `staticfiles/css/tokens.css`                          | All design tokens (variants × modes)                            |
| `staticfiles/css/base.css`                            | Resets, buttons, forms, chat-bubble defaults, utils             |
| `staticfiles/js/theme.js`                             | Variant/mode switching, persistence, system sync                |
| `staticfiles/js/shell-core.js`                        | Settings store, CSRF helper, `springWidth` (`window.PGShell`)   |
| `staticfiles/js/sidebar-toggle.js`                    | Sidebar collapse/expand                                         |
| `staticfiles/js/settings-modal.js`                    | Model-settings modal                                            |
| `staticfiles/js/user-menu.js`                         | Sidebar-footer appearance menu                                  |
| `templates/base.html`                                 | Document shell, fonts, token/script wiring, blocks              |
| `templates/partials/_sidebar.html` etc.               | Shared shell markup (sidebar, user menu, settings)              |
| `apps/chat/static/chat/css/sidebar.css`               | Sidebar shell + collapse                                        |
| `apps/chat/static/chat/css/right-panel.css`           | Chat right-hand settings panel + collapse                       |
| `apps/chat/static/chat/css/chat-area.css`             | Chat header/body/bubbles/markdown/sources                       |
| `apps/chat/static/chat/css/user-menu.css`             | Sidebar-footer appearance menu                                  |
| `apps/chat/static/chat/css/settings-modal.css`        | Model-settings modal                                            |
| `apps/chat/static/chat/css/layout.css`                | `.chat-layout` flex shell                                       |
| `apps/chat/static/chat/css/responsive.css`            | ≤640px mobile overrides                                         |
| `apps/chat/static/chat/js/right-panel.js`             | Right-panel settings + collapse                                 |
| `apps/chat/static/chat/js/transcript.js`              | Chat transcript render + streaming send                         |
| `apps/upload/static/upload/css/upload-intro.css`      | Upload intro, dropzone, processing card                         |
| `apps/upload/static/upload/css/upload-review.css`     | Review file card, metadata, recuperação, questions, footer      |
| `apps/upload/static/upload/css/multiselect.css`       | Chip multiselect (professores, cursos)                          |
| `apps/upload/static/upload/css/markdown-editor.css`   | Review markdown field tabs/textarea/preview                     |
| `apps/upload/static/upload/css/question-editor.css`   | Question editor, grades, subquestions, add buttons              |
| `apps/upload/static/upload/css/responsive.css`        | ≤640px mobile overrides (upload screen)                         |

> Note: `staticfiles/` holds the **source** static assets served by Django's
> staticfiles finders in `DEBUG`. `static_collected/` is `collectstatic` output
> (production, WhiteNoise) — never edit it by hand.

---

## 11. Don'ts

Concrete failure modes from real generations and prior bugs. Each is a hard rule
— if a change does any of these, it's wrong.

- **Don't hard-code colors, fonts, or radii.** Use `var(--color-*)`,
  `var(--font-*)`, `var(--radius-*)`. A literal hex or font name breaks the three
  variants and dark mode instantly.
- **Don't add CSS `::after` / `::before` tooltips.** They get clipped by the
  sidebar's `overflow: hidden` (this caused a real artifact bug). Use the native
  `title` attribute.
- **Don't edit anything in `static_collected/`.** It's `collectstatic` output;
  edit the source under `staticfiles/` or the app's `static/` dir.
- **Don't assume the window scrolls.** Page content scrolls inside
  `.chat-scroll`; script that container, not `window`.
- **Don't re-declare `@font-face` or re-import fonts.** They load once in
  `base.html`; just reference the `--font-*` role.
- **Don't ship a screen tested in only one variant/mode.** Verify all three
  variants in both light and dark before calling it done.
- **Don't use sans for question/answer content or serif for UI chrome.** Content
  is serif, chrome is sans — that split is the identity.
- **Don't roll a one-off Markdown/LaTeX renderer.** Use the `markdownField`
  pattern (marked + KaTeX) so math renders consistently.
- **Don't introduce a new accent or status color.** Derive translucent states
  with `color-mix(...)` from existing tokens.
- **Don't size or center content inside an animated-width container with
  `inset: 0` / `margin: auto`.** It recalculates against the container's live
  width every frame, so the content reflows (text wraps) or drifts sideways
  mid-fade instead of just fading in place (the sidebar brand text, the
  collapsed-logo button, and the right-panel settings all hit this). Pin a
  fixed width/position derived from the container's static expanded or
  collapsed size instead.

---

## 12. Maintenance

- Treat this file like a **release note**: when tokens, components, or patterns
  change, update DESIGN.md in the same commit. A stale design doc is worse than
  none — that's exactly what got the original mockup retired.
- The front-matter tokens must stay in sync with `staticfiles/css/tokens.css`
  (front matter = Manuscrito light); §3's tables cover the other variants/modes.
- Optional: validate the token block with the reference linter —
  `npx @google/design.md lint DESIGN.md` (flags broken token refs + WCAG
  contrast).
- When prompting an agent, point it here explicitly: _"use @DESIGN.md for all
  styling decisions."_

---

## 13. Checklist for new UI

1. Extend `base.html`; add page CSS in `{% block extra_css %}`.
2. Use **only** tokens for color, font, radius, and transition.
3. Serif for content, sans for chrome; tabular nums for numbers.
4. Verify it reads in all three variants and both light/dark.
5. Native focus states preserved; controls reach 44px where they're primary.
6. Responsive at ≤640px (sidebar → bottom tabs, grids → single column).
7. Copy in pt-BR, sentence case, action-named.
8. Markdown/LaTeX text edited via the `markdownField` pattern.
