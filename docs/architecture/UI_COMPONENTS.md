# SpatialForge UI Components

Shared resources are split into design tokens, control templates, and component styles under
`apps/desktop/src/SpatialForge.Desktop/Resources/`.

## Foundational styles

- `PageTitle`, `PageSubtitle`, `SectionTitle`, `CardTitle`, `Eyebrow`, `BodySecondary`
- `Card`, `InsetCard`
- `PrimaryButton`, `SecondaryButton`, `TertiaryButton`, `DangerButton`, `IconButton`
- `NavButton`, `SelectableCardItem`
- `SuccessBadge`, `InfoBadge`, `WarningBadge`

Implicit templates cover `Button`, `TextBox`, `ComboBox` and its popup/items, `CheckBox`,
`RadioButton`, `ListBox`, `ProgressBar`, `ToolTip`, menus, data grids, scroll affordances, and
disabled/focus behavior.

## Composite components

The current WPF implementation composes reusable styles rather than adding a heavy control library:

- App shell: brand mark, grouped active navigation, local-processing identity, status strip.
- Page header: title/subtitle plus right-aligned actions or status badge.
- Readiness/metric cards: semantic icon, eyebrow, value, helper copy.
- Empty state: spatial icon, concise guidance, one primary action.
- Wizard stepper and selectable project/preset cards.
- Photo grid plus inspector; pipeline timeline; hardware capability rows; model layer rail and
  statistics inspector.
- `SpatialForgeDialog`: themed privacy and destructive confirmation dialog.
- Error panel: plain-language explanation, recommended action, collapsed technical detail.

## Usage rules

Use semantic resources with `StaticResource`; do not paste hex colors into new screens. Keep a
visible label for every form input. Use automation names for icon-only or context-dependent actions.
Use `TargetNullValue` or presentation properties for every optional hardware/model value. Preserve
the existing view-model command and backend contract when rearranging visual composition.
