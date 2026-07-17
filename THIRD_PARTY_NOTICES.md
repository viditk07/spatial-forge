# Third-Party Notices

SpatialForge uses permissively licensed open-source runtime components listed in
`DEPENDENCY_LICENSES.md`, including Python, FastAPI, Pydantic, SQLAlchemy, Alembic, Uvicorn,
psutil, Pillow, OpenCV, Trimesh, Three.js, and the .NET runtime libraries.

Copyright and licence texts supplied by those distributions must accompany every installer.
Apache-2.0 components must include their licence and any supplied NOTICE files. Microsoft .NET
and WebView2 components remain subject to their applicable distribution and runtime terms.

COLMAP, OpenMVS, and Blender are optional external programs and are not included in the current
package definition. PyInstaller is used under its GPL special exception for distributing bundled
applications. SpatialForge does not modify third-party sources in the validated build.

This source-tree summary is not a substitute for the release-generated notice bundle. Packaging
must fail closed when a shipped dependency lacks identifiable licence metadata.
