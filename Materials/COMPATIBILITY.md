# SplatGen Standard compatibility

| Component | Requirement |
|---|---|
| Blender | 5.0 or newer |
| Operating system | Any desktop operating system supported by Blender 5.0+ |
| GPU | Optional; Blender's configured render device is used |
| Internet | Not required |
| Storage | Depends on image resolution, camera count, format, and enabled passes |

SplatGen Standard contains Python source and image resources only. It does not
ship native binaries, install Python packages, download a runtime, or train
Gaussian Splats.

Before a large build, use a small camera set and low resolution to verify the
output directory, render engine, image format, and selected data passes.
