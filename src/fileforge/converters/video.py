"""Discovery shim: importing this module registers the Pro video routes.

The actual implementation (ffmpeg presets, license gating) lives in
``fileforge.pro.video``; this lets the built-in loader surface the routes in
``fileforge list`` while keeping the logic in the Pro package.
"""

from fileforge.pro import video as _video  # noqa: F401  (import registers routes)
