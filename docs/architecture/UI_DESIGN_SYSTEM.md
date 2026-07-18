# SpatialForge UI Design System

## Brand direction

SpatialForge is precise, private spatial-computing software. The interface uses a restrained cube /
point-center mark, a dark engineered workspace, cyan for primary spatial actions, and emerald for
local privacy and successful states. Segoe UI Variable falls back to Segoe UI; Segoe Fluent Icons
falls back to Segoe MDL2 Assets. No fonts or icons are fetched at runtime.

## Semantic colors

Tokens live in `apps/desktop/src/SpatialForge.Desktop/Resources/DesignTokens.xaml`.

| Token | Value | Purpose |
| --- | --- | --- |
| `AppBackground` | `#0B1118` | Main workspace |
| `SidebarBackground` | `#080D13` | Navigation and inset regions |
| `SurfacePrimary` | `#121A24` | Cards and controls |
| `SurfaceSecondary` | `#17222E` | Hero/readiness surfaces |
| `SurfaceElevated` | `#1D2A38` | Popup and elevated surfaces |
| `AccentPrimary` | `#3ABFF8` | Primary action and focus emphasis |
| `TextPrimary` | `#F4F8FC` | Primary content |
| `TextSecondary` | `#B4C2CF` | Supporting content |
| `TextMuted` | `#8595A5` | Metadata |
| `StatusSuccess` | `#59D49A` | Completed/local/safe |
| `StatusWarning` | `#F2BC66` | Advisory action |
| `StatusError` | `#FF8796` | Error/destructive action |

Do not add view-specific colors when a semantic token exists. Status always includes text or an
icon, never color alone.

## Typography and layout

- Page title: 30 px semibold; section: 20 px semibold; card: 16 px semibold.
- Body: 14 px; supporting metadata: 11–12 px.
- Logs and technical output only: Cascadia Mono with Consolas fallback.
- Layout follows a 4/8 px grid. Default page margin is 32 px, card padding is 20 px, and common gaps
  are 8, 12, 16, 18, 24, and 32 px.
- Radii are 6, 10, and 14 px. Shadows are reserved for transient elevated content.

## Controls and interaction

Primary actions use cyan fill and dark text. Secondary actions use a neutral surface and strong
outline. Tertiary actions are quiet; destructive actions use error surface plus explicit wording.
Interactive controls target at least 40 px height. Keyboard focus uses a two-pixel light-cyan ring.
Hover, pressed, selected, focused, disabled, and popup states are explicitly themed.

Motion timings are tokenized at 120 ms and 200 ms. The initial WPF refresh avoids nonessential
motion, so Windows reduced-motion users do not receive decorative animations.

## Accessibility

Automated tests parse token values and enforce WCAG AA contrast for primary/secondary text and the
accent on their common surfaces. Every major page and important interactive region exposes an
automation name. Labels remain visible above inputs, disabled text remains legible, error content
includes an icon and explanation, and all navigation/control templates include keyboard focus.

## Icon usage

Use the installed Windows Segoe Fluent icon family consistently. Every glyph must have adjacent
visible text or an automation name when interactive. Do not communicate status using a glyph alone.
