---
name: ui-design
description: UI-design skill — visual craft rules (tokens, hierarchy, spacing, states, accessibility) so generated UIs look professional, not default
metadata:
  type: user
---

# UI Design — Visual Craft Skill

## Why

Smaller models produce "bootstrap-default" UIs: inconsistent spacing, five shades of gray that don't relate, buttons that look different on every screen, and no empty/loading/error states. Professional UI isn't taste — it's a small set of rules applied without exception. This skill encodes those rules. Flows come first — see ux-design; this skill governs the screens inside a mapped flow.

## The Rule

**All visual decisions come from a token system defined once, before the first component.** No hardcoded colors, sizes, or spacing anywhere in component code.

## How to Apply

### 1. Define tokens first

Before any component, create the token file (CSS variables, Tailwind config, or theme object):

- **Spacing**: one scale, 4px base — 4, 8, 12, 16, 24, 32, 48, 64. Nothing else, ever.
- **Type**: max 2 font families; a scale of ~6 sizes (12, 14, 16, 20, 24, 32); weights 400/500/700 only
- **Color**: 1 primary, 1 neutral ramp (5–7 steps), 1 each semantic (success/warning/error/info). Every color has a light- and dark-mode value from day one.
- **Radius & shadow**: one radius per component class (e.g. 6px controls, 12px cards); 2–3 shadow levels

### 2. Hierarchy per screen

Every screen has exactly one primary action, styled uniquely (filled primary color). Everything else is secondary (outline) or tertiary (text). If two things look most important, neither is.

### 3. Every component ships with all five states

Default, hover/focus, active, disabled, and — for anything that loads data — **loading, empty, and error**. The empty state is designed (icon, one line of copy, a CTA), not a blank div. This is the single most common gap; check it explicitly.

### 4. Accessibility floor (non-negotiable)

- Text contrast ≥ 4.5:1 (3:1 for ≥24px text); check semantic colors against their backgrounds too
- Focus visible on every interactive element — never `outline: none` without a replacement
- Hit targets ≥ 44×44px on touch
- Never color as the only signal (pair with icon/text)
- Real `<button>`/`<a>`/`<label>` elements, alt text, form inputs with associated labels

### 5. Layout discipline

- Content max-width ~1200px, centered; text measure 45–75 characters
- Align to the grid — mixed margins on siblings is the #1 amateur tell
- Whitespace scales with hierarchy: more space *between* sections than *within* them

## Review Checklist

Before calling a UI done, walk the screen and check:
- [ ] Zero hardcoded colors/sizes/spacing in component code — grep for `px` and hex literals
- [ ] One primary action per screen
- [ ] Loading, empty, and error states exist for every data-driven view
- [ ] Keyboard-only walkthrough works: tab order sane, focus visible, Enter/Escape behave
- [ ] Dark mode (if the token file defines it) — actually rendered, not just defined
- [ ] Squint test: blur your eyes; hierarchy should still read

Record the checklist result in the task's verify artifact (`.claude/plans/{task-name}-verify.md`) — one line stating which items passed and which failed.

## Anti-Patterns

- Introducing a new gray because the existing ones "didn't look right" — fix the ramp, not the instance
- Spacing chosen per-component ("this one felt like 14px")
- Disabled buttons with no explanation of how to enable them
- Icon-only buttons without labels or tooltips
- Designing only the populated, mid-sized, happy state — real data is empty, huge, or broken
