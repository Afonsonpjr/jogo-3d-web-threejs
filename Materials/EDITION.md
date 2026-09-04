# SplatGen Standard 5.1.0

This package is the **Standard** edition of SplatGen.

## What it contains

- Camera placement, camera rigs and the render queue
- Camera coverage validation
- Dataset building: RGB, masks, metric depth, normals, `cameras.txt`,
  `images.txt` and `points3D.txt`
- Preview of the built point cloud and the coverage result in the viewport

It needs no GPU and downloads nothing.

## What it does not contain

- Gaussian Splat training, and the managed CUDA runtime it needs
- The live training preview
- The Viewer section
- PLY and SOG export

These are in SplatGen Pro. The datasets this edition builds are the input
Pro trains from, so nothing has to be rebuilt to move up.

This marketplace package installs as the Blender extension
`splatgen_standard`, giving it a distinct identity from other SplatGen
editions already published on Blendkit.
