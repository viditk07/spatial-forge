# UI Refresh Plan

## Implementation sequence

1. Audit the WPF shell, view hierarchy, bindings, commands, tests, viewer bridge, and packaging.
2. Introduce semantic tokens and complete dark control templates without a new runtime dependency.
3. Rebuild the shell around an active navigation rail, focused workspace, local-service strip, and
   persistent local-processing identity.
4. Redesign dashboard, five-step project wizard, photo review, processing, hardware, model review,
   settings, error, privacy, and confirmation experiences.
5. Add human-readable presentation contracts, missing-value fallbacks, keyboard focus states,
   accessible names, and WCAG contrast tests.
6. Run formatter, build, desktop tests, aggregate backend/viewer validation, and Windows packaging.

## Acceptance mapping

- Readability and contrast: semantic brushes and automated AA checks.
- Native dark controls: explicit templates for inputs, dropdown/popup, buttons, checks, lists,
  progress, menus, tooltips, grids, and selection/focus states.
- Navigation: current-page state is exposed by the existing navigation service and tested.
- Guided creation: one visible wizard step at a time with cards, descriptions, summary, and stable
  existing commands.
- Hardware clarity: capability cards and explicit `Not detected`, `Unavailable`, or `Not installed`.
- Spatial workstation: dominant offline viewport with layer rail, inspector, and status strip.
- Regression safety: API calls, commands, WebView protocol, model operations, and data are unchanged.

## Remaining Windows visual gate

Run the packaged `0.2.0` build at 1280×720 through 2560×1440 and 100–200% scaling; capture all
major views and dialogs; verify tab order, focus visibility, dropdowns, scrolling, title bar,
WebView composition, taskbar/installer icon, and reduced-motion/system accessibility behavior.
