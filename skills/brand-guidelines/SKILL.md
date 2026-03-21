---
name: brand-guidelines
description: Applies Ralphify's official brand colors, typography, and visual style to any artifact — landing pages, slides, diagrams, social graphics. Use when Ralphify's look-and-feel should be applied.
license: MIT (see project root LICENSE)
---

# Ralphify Brand Guidelines

Use these rules when generating any visual artifact (HTML pages, CSS, slides, graphics, diagrams) that should carry the Ralphify brand.

## Brand identity

- **Name**: Ralphify (always capitalized, never "RALPHIFY" or "ralphify" in headings/prose)
- **CLI command**: `ralph` (always lowercase, monospace)
- **Tagline**: "Put your AI coding agent in a `while True` loop and let it ship."
- **Positioning**: Minimal CLI harness for autonomous AI coding loops. Inspired by the Ralph Wiggum technique.
- **Logo icon**: Runner emoji (🏃) — represents Ralph running in a loop
- **Copyright**: Computerlove Technologies

## Colors

### Primary palette

| Name           | Hex       | Usage                                      |
|----------------|-----------|---------------------------------------------|
| **Purple**     | `#8B6CF0` | Primary brand color, buttons, headers, icons |
| **Purple Dark**| `#7C5CE0` | Hover states, links (light mode)             |
| **Purple Light**| `#A78BF5`| Dark-mode accent, hover gradients, dark-mode links |
| **Purple Deep**| `#7C4DFF` | Header gradient end                          |

### Accent palette

| Name           | Hex       | Usage                                        |
|----------------|-----------|-----------------------------------------------|
| **Orange**     | `#E06030` | Secondary brand color, gradient endpoints      |
| **Orange Light**| `#E87B4A`| Tagline gradient end, warm accents             |

### Neutral palette

| Name           | Hex       | Usage                             |
|----------------|-----------|-------------------------------------|
| **White**      | `#FFFFFF` | Light-mode backgrounds              |
| **Slate BG**   | `#1E1E2E` | Dark-mode backgrounds (Material Slate) |
| **Text Dark**  | `#2E2E3E` | Primary body text (light mode)      |
| **Text Light** | `#E0E0E0` | Primary body text (dark mode)       |

### Brand gradient

The signature visual is a **purple → orange** gradient used for hero elements and the tagline:

```css
/* Primary brand gradient */
background: linear-gradient(135deg, #8B6CF0 0%, #E87B4A 100%);

/* Button gradient (purple only) */
background: linear-gradient(135deg, #8B6CF0 0%, #A78BF5 100%);

/* Header bar gradient */
background: linear-gradient(90deg, rgba(139, 108, 240, 0.95) 0%, rgba(124, 77, 255, 0.95) 100%);
```

## Typography

- **Headings**: System sans-serif stack — `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`. Bold weight (600–700).
- **Body**: Same system stack, regular weight (400). Line-height 1.6 for readability.
- **Code / CLI output**: Monospace — `"SF Mono", "Fira Code", "JetBrains Mono", Consolas, monospace`.
- No custom web fonts are required. The brand relies on color and gradients, not typography.

## Visual style

### General principles

- **Minimal and clean**. Ralphify is a small, focused tool — the visual style reflects that. No clutter.
- **Purple as the anchor**. Purple (#8B6CF0) is the primary visual element. Orange is the accent that adds warmth.
- **Generous whitespace**. Let content breathe.
- **Dark mode is first-class**. Every element must look good in both light and dark schemes.

### Component patterns

- **Buttons (primary)**: Purple gradient background, white text, 600 weight, rounded corners. Hover: slight lift (`translateY(-1px)`) + purple glow shadow (`box-shadow: 0 4px 12px rgba(139, 108, 240, 0.35)`).
- **Buttons (secondary)**: Transparent background, purple border and text. Hover: subtle purple fill (`rgba(139, 108, 240, 0.08)`).
- **Cards**: White/dark background, 8px border-radius. Hover: lift (`translateY(-3px)`) + soft shadow.
- **Icons in cards**: Tinted purple (#8B6CF0 light, #A78BF5 dark).
- **Code blocks**: 6px border-radius.
- **Section dividers (hr)**: 2px solid, purple-tinted (`rgba(139, 108, 240, 0.15)` light, `rgba(167, 139, 245, 0.2)` dark).
- **Links**: Purple (#7C5CE0 light, #A78BF5 dark). No underline by default; underline on hover.
- **Footer**: Subtle gradient wash (`rgba(139, 108, 240, 0.08)` → `rgba(232, 123, 74, 0.06)`). Dark mode: solid dark.

### Animation

- Transitions are subtle and fast: `0.15s ease` for buttons, `0.2s ease` for cards.
- Only translate and shadow transitions. No rotation, scaling, or opacity fades on interaction.

## Tone of voice (for copy)

- **Direct and concise**. Lead with what the tool does, not what it is.
- **Confident but not hype-y**. "Two commands to start" not "Revolutionary AI framework".
- **Code-first**. Show terminal output and commands before explaining.
- **Conversational**. "That's it. Two commands." is on-brand. "Leveraging cutting-edge paradigms" is not.

## Landing page structure (reference)

When building a landing page for Ralphify, follow this hierarchy:

1. **Hero**: CLI banner image + tagline + CTA buttons (Get Started / View Cookbook)
2. **Install**: Tabbed code blocks (uv / pipx / pip)
3. **Quick demo**: Terminal output showing the loop in action
4. **Primitives**: Card grid showing Checks, Contexts, Ralphs
5. **Requirements**: Short list
6. **Next steps**: Links to docs

## Asset references

- **CLI banner**: `docs/assets/cli-banner.png` — the purple-gradient ASCII art banner used in docs and README
- **Logo icon**: Material Design Icons `run` icon (for use in nav/favicons)
- **Social**: GitHub repo + PyPI badges
