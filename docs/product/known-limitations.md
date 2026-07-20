# Known Limitations

- Final Windows runtime, WebView2, and installer validation must run in Windows CI/VM.
- The desktop no longer abandons imports or quality analysis after 30 seconds, and an automated
  80-image regression fixture passes. Representative 80-photo, full-resolution validation on the
  affected Windows machine remains required before the resource-related crash is considered closed.
- The 0.2.0 visual refresh is XAML-compiled and programmatically contrast-tested, but screenshot,
  keyboard traversal, 100–200% DPI, dark title-bar, and packaged-theme inspection still require
  the Windows validation matrix; this Linux host cannot render WPF.
- COLMAP is discovered from the configured path or `PATH`; it is not redistributed yet.
- Dense stereo depends on the installed COLMAP build and generally requires NVIDIA CUDA.
- Intel Arc is experimental and is not advertised as a supported dense path.
- The current engine slice creates sparse, dense PLY, and Poisson mesh artifacts; a separate
  production texture engine integration remains required for guaranteed textured output.
- Sparse, dense, mesh, and reconstructed-camera layers have independent visibility controls.
  Camera frustums represent COLMAP registration poses, not the physical size of the phone.
- Export texture resolution is persisted as the requested target, but untextured input cannot gain
  textures and arbitrary source materials are not yet resampled by a dedicated texture engine.
- Export-size estimates are directional and can differ substantially for textured or highly
  compressible models; the completed export record stores the actual combined output size.
- OpenGL/WebGL capability requires the Windows WebView2 runtime probe; the Linux build host cannot
  certify the final driver/context version.
- Cropping keeps faces whose centres lie inside the selected box; it does not cap cut edges.
- Measurements are approximate, depend on point placement and reconstruction quality, and
  are not suitable for survey, structural, legal, or safety-critical use.
- GLB/OBJ/PLY conversion preserves supported mesh attributes; format-specific material
  features may not round-trip perfectly.
- The requested 50/100/250/500/1,000-image performance matrix still requires representative legal
  phone captures and target Windows hardware; synthetic correctness tests are not performance data.
