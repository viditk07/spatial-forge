# UI Refresh Audit

Date: 2026-07-18

## Scope inspected

The desktop is a .NET 10 WPF application using MVVM, dependency injection, a singleton
navigation service, native Windows pickers, and an offline Three.js viewer hosted in a locked-down
WebView2. The audit covered `App.xaml`, `MainWindow`, every desktop view and code-behind file,
desktop view models/contracts, confirmation and first-run dialogs, desktop tests, packaging inputs,
and the embedded viewer boundary.

No third-party UI framework or icon package was present. The refresh deliberately keeps that small
dependency surface: controls are native WPF templates, and icons use Windows' Segoe Fluent/MDL2
glyph fonts with a text fallback. No runtime download or network dependency was introduced.

## Original issues

- `App.xaml` defined only six brushes and minimal implicit styles. Complex controls retained native
  light templates, producing white popup surfaces, low-contrast selected text, and inconsistent
  focus/disabled behavior.
- Navigation was a flat list of generic buttons with no active-page state, weak grouping, and a
  visually detached privacy label.
- Pages used unrelated fixed widths, radii, margins, and direct hex colors. Layouts made poor use
  of wide screens and did not scroll consistently on smaller screens.
- Dashboard readiness, engine state, recent projects, and empty state had little hierarchy.
- The project wizard presented unrelated fields together rather than explaining the active step.
- Hardware bindings could resolve to null or empty strings without an explicit visible fallback.
- Image review lacked clear filtering state and a disciplined photo/inspector relationship.
- Processing showed a basic list rather than a checkpoint timeline and separated resource summary.
- Model review gave the WebView the whole page without WPF-level layer or model context.
- Settings mixed privacy, expert controls, storage, and diagnostics in two undifferentiated cards.
- Destructive confirmations and first-run privacy used light native message boxes.
- Existing tests verified core commands and flows but did not validate theme resources or contrast.

## Preserved integration boundaries

All existing navigation routes, view models, commands, API methods, project records, WebView message
types, file pickers, reconstruction stages, and backend lifecycle behavior remain in place. The UI
adds presentation-only properties for human-readable labels and navigation state. No database,
reconstruction, file-layout, privacy, or network behavior changed.

## Validation constraint

This Linux development host can compile the Windows-targeted WPF project but cannot launch WPF,
WebView2, or the Inno Setup installer. XAML compilation, programmatic token/contrast checks, MVVM
tests, and cross-build validation are performed here. Screenshot, high-DPI, keyboard traversal,
packaged-EXE launch, and clean Windows installer review remain explicit Windows release checks.
