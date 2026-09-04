# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""Reading Splat data off disk, and packing it for the GPU.

Pure data: no GPU objects, no Blender state, nothing global. Everything here
takes and returns arrays, which is what makes it testable without a viewport.
"""

import math
from pathlib import Path

#: Per-Splat float layout, matching the standard viewer stride:
#:   0..2  position        3..6  rotation (wxyz)
#:   7..9  scale (linear)  10    opacity
#:   11..  spherical-harmonic coefficients, three floats each
HEADER_FLOATS = 11

SH_C0 = 0.28209479177387814

_PLY_DTYPES = {
    "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
    "short": "<i2", "int16": "<i2", "ushort": "<u2", "uint16": "<u2",
    "int": "<i4", "int32": "<i4", "uint": "<u4", "uint32": "<u4",
    "float": "<f4", "float32": "<f4", "double": "<f8", "float64": "<f8",
}


def load_ply(path, np):
    """Read a standard Gaussian PLY into ``(positions, scales, quats, opacity, sh)``."""
    source = Path(path)
    count = 0
    properties = []
    file_format = ""
    in_vertices = False
    with open(source, "rb") as handle:
        if handle.readline().strip() != b"ply":
            raise ValueError(f"{source.name} is not a PLY file")
        while True:
            raw = handle.readline()
            if not raw:
                raise ValueError("Incomplete PLY header")
            line = raw.decode("ascii", errors="strict").strip()
            fields = line.split()
            if fields[:1] == ["format"] and len(fields) >= 2:
                file_format = fields[1]
            elif fields[:2] == ["element", "vertex"] and len(fields) >= 3:
                count = int(fields[2])
                in_vertices = True
            elif fields[:1] == ["element"]:
                in_vertices = False
            elif fields[:1] == ["property"] and in_vertices:
                if len(fields) != 3 or fields[1] == "list":
                    raise ValueError(
                        "List properties are not supported in Splat PLY files"
                    )
                kind = _PLY_DTYPES.get(fields[1])
                if kind is None:
                    raise ValueError(f"Unsupported PLY property type: {fields[1]}")
                properties.append((fields[2], kind))
            elif line == "end_header":
                break
        if count <= 0 or not properties:
            raise ValueError("The PLY contains no vertices")
        dtype = np.dtype(properties)
        if file_format == "binary_little_endian":
            rows = np.fromfile(handle, dtype=dtype, count=count)
        elif file_format == "ascii":
            values = np.loadtxt(handle, dtype=np.float64, ndmin=2)
            if values.shape != (count, len(properties)):
                raise ValueError("The PLY has incomplete vertex data")
            rows = np.empty(count, dtype=dtype)
            for index, (name, _kind) in enumerate(properties):
                rows[name] = values[:, index]
        else:
            raise ValueError(
                f"Unsupported PLY format: {file_format or 'unknown'}"
            )
    if len(rows) != count:
        raise ValueError("The PLY has incomplete vertex data")
    names = set(rows.dtype.names or ())
    if not {"x", "y", "z"}.issubset(names):
        raise ValueError("The PLY does not contain x, y, and z positions")

    def columns(prefix, maximum=None):
        found = sorted(
            (name for name in names if name.startswith(prefix)),
            key=lambda name: int(name.rsplit("_", 1)[1]),
        )
        if maximum is not None:
            found = found[:maximum]
        return (
            np.stack([rows[name] for name in found], axis=1).astype(np.float32)
            if found else None
        )

    positions = np.stack(
        [rows[name] for name in ("x", "y", "z")], axis=1
    ).astype(np.float32)

    sh0 = columns("f_dc_", 3)
    if sh0 is None or sh0.shape[1] != 3:
        if {"red", "green", "blue"}.issubset(names):
            rgb = np.stack(
                [rows[name] for name in ("red", "green", "blue")], axis=1
            ).astype(np.float32)
            if float(rgb.max()) > 1.0:
                rgb /= 255.0
            sh0 = (rgb - 0.5) / SH_C0
        else:
            sh0 = np.zeros((count, 3), dtype=np.float32)
    rest = columns("f_rest_")
    if rest is None:
        shN = np.zeros((count, 0, 3), dtype=np.float32)
    else:
        if rest.shape[1] % 3:
            raise ValueError("The PLY has an invalid spherical-harmonic layout")
        shN = rest.reshape(count, 3, rest.shape[1] // 3).transpose(0, 2, 1)
    sh = np.concatenate((sh0.reshape(count, 1, 3), shN), axis=1)

    log_scales = columns("scale_", 3)
    if log_scales is None or log_scales.shape[1] != 3:
        diagonal = float(np.linalg.norm(np.ptp(positions, axis=0)))
        fallback = max(1.0e-5, diagonal / math.sqrt(max(1, count)))
        scales = np.full((count, 3), fallback, dtype=np.float32)
    else:
        scales = np.exp(np.clip(log_scales, -30.0, 30.0))

    quaternions = columns("rot_", 4)
    if quaternions is None or quaternions.shape[1] != 4:
        quaternions = np.zeros((count, 4), dtype=np.float32)
        quaternions[:, 0] = 1.0

    if "opacity" in names:
        logits = np.asarray(rows["opacity"], dtype=np.float32)
        opacities = 1.0 / (1.0 + np.exp(-np.clip(logits, -80.0, 80.0)))
    elif "alpha" in names:
        opacities = np.asarray(rows["alpha"], dtype=np.float32)
        if float(opacities.max()) > 1.0:
            opacities /= 255.0
    else:
        opacities = np.ones(count, dtype=np.float32)
    return positions, scales, quaternions, opacities, sh


def load_snapshot(path, np):
    """Read the .npz the trainer publishes for the live view."""
    with np.load(str(path)) as archive:
        return (
            archive["positions"],
            archive["scales"],
            archive["quaternions"],
            archive["opacities"],
            archive["sh"],
        )


def validate(positions, scales, quaternions, opacities, sh, np):
    """Reject malformed data and drop any non-finite Splats."""
    positions = np.asarray(positions, dtype=np.float32)
    count = int(len(positions))
    if positions.ndim != 2 or positions.shape[1] != 3 or count <= 0:
        raise ValueError("Splat positions must be a non-empty Nx3 array")
    scales = np.asarray(scales, dtype=np.float32)
    quaternions = np.asarray(quaternions, dtype=np.float32)
    opacities = np.asarray(opacities, dtype=np.float32).reshape(-1)
    sh = np.asarray(sh, dtype=np.float32)
    if scales.shape != (count, 3):
        raise ValueError("Splat scales must be an Nx3 array")
    if quaternions.shape != (count, 4):
        raise ValueError("Splat quaternions must be an Nx4 array")
    if opacities.shape != (count,):
        raise ValueError("Splat opacities must contain one value per Splat")
    if sh.ndim != 3 or sh.shape[0] != count or sh.shape[2] != 3:
        raise ValueError("Splat spherical harmonics must be an NxKx3 array")

    finite = (
        np.isfinite(positions).all(axis=1)
        & np.isfinite(scales).all(axis=1)
        & np.isfinite(quaternions).all(axis=1)
        & np.isfinite(opacities)
        & np.isfinite(sh).all(axis=(1, 2))
    )
    if not bool(finite.any()):
        raise ValueError("The file contains no finite Splats")
    if not bool(finite.all()):
        positions = positions[finite]
        scales = scales[finite]
        quaternions = quaternions[finite]
        opacities = opacities[finite]
        sh = sh[finite]

    norms = np.linalg.norm(quaternions, axis=1, keepdims=True)
    quaternions = quaternions / np.maximum(norms, 1.0e-12)
    return positions, scales, quaternions, opacities, sh


def pack(positions, scales, quaternions, opacities, sh, np):
    """Interleave Splat data into the viewer's flat float layout."""
    count = int(positions.shape[0])
    coefficients = int(sh.shape[1])
    stride = HEADER_FLOATS + coefficients * 3
    packed = np.zeros((count, stride), dtype=np.float32)
    packed[:, 0:3] = positions
    packed[:, 3:7] = quaternions
    packed[:, 7:10] = scales
    packed[:, 10] = opacities
    packed[:, HEADER_FLOATS:] = sh.reshape(count, coefficients * 3)
    degree = int(round(math.sqrt(max(1, coefficients)))) - 1
    return packed.reshape(-1), stride, max(0, min(3, degree))


def coverage_colours(positions, np, neighbours=8, samples=200_000):
    """Colour every point by how densely reconstructed its neighbourhood is.

    A point in a well-covered region has close neighbours; one in a region the
    cameras barely saw is isolated. Mapping that spacing to colour turns the
    point cloud into a coverage read-out: warm and bright where the dataset is
    solid, cold and dark where it is thin, and nothing at all where no camera
    reached. Reading it before training is much cheaper than discovering a
    blind spot afterwards.

    Distances come from a Z-order scan rather than an exact KNN, which is the
    same approximation the trainer uses to size its initial Gaussians.
    """
    points = np.asarray(positions, dtype=np.float64)
    count = int(points.shape[0])
    if count == 0:
        return np.zeros((0, 1, 3), dtype=np.float32)
    if count < 3:
        return np.tile(
            np.asarray([[1.0, 1.0, 1.0]], dtype=np.float32), (count, 1)
        ).reshape(count, 1, 3)

    # A large cloud is judged from a subset: the statistic is a distribution,
    # and sampling it keeps the toggle instant on millions of points.
    if count > samples:
        step = max(1, count // samples)
        reference = points[::step]
    else:
        reference = points

    spacing = _neighbour_spacing(points, reference, np, neighbours)
    finite = spacing[np.isfinite(spacing) & (spacing > 0.0)]
    if finite.size == 0:
        return np.tile(
            np.asarray([[1.0, 1.0, 1.0]], dtype=np.float32), (count, 1)
        ).reshape(count, 1, 3)

    # Percentiles, not min/max: one stray far-away point would otherwise
    # flatten the whole scale.
    dense, sparse = np.percentile(finite, (5.0, 95.0))
    span = max(float(sparse - dense), 1.0e-9)
    thinness = np.clip((spacing - dense) / span, 0.0, 1.0)

    # Dense -> warm white, sparse -> deep blue, so gaps read as cold and dark.
    colours = np.empty((count, 3), dtype=np.float32)
    colours[:, 0] = 1.0 - thinness
    colours[:, 1] = np.clip(1.0 - thinness * 1.6, 0.0, 1.0)
    colours[:, 2] = np.clip(0.25 + thinness * 0.75, 0.0, 1.0)
    return ((colours - 0.5) / SH_C0).reshape(count, 1, 3)


def _neighbour_spacing(points, reference, np, neighbours):
    """Mean distance to the nearest few neighbours, per point."""
    minimum = reference.min(axis=0)
    extent = np.maximum(reference.max(axis=0) - minimum, 1.0e-12)
    grid = np.clip(
        ((reference - minimum) / extent * 1023.0).astype(np.int64), 0, 1023
    )

    def spread(value):
        value = (value | (value << 16)) & 0x030000FF
        value = (value | (value << 8)) & 0x0300F00F
        value = (value | (value << 4)) & 0x030C30C3
        value = (value | (value << 2)) & 0x09249249
        return value

    codes = (
        spread(grid[:, 0]) | (spread(grid[:, 1]) << 1) | (spread(grid[:, 2]) << 2)
    )
    order = np.argsort(codes)
    ordered = reference[order]

    total = int(ordered.shape[0])
    window = int(max(1, min(neighbours * 2, total - 1)))
    best = np.full((total, neighbours), np.inf, dtype=np.float64)
    for offset in range(1, window + 1):
        gap = np.linalg.norm(ordered[offset:] - ordered[:-offset], axis=1)
        for target in (slice(0, total - offset), slice(offset, total)):
            block = best[target]
            replace = gap < block[:, -1]
            if not replace.any():
                continue
            block[replace, -1] = gap[replace]
            block.sort(axis=1)
            best[target] = block

    finite = np.isfinite(best)
    counts = finite.sum(axis=1)
    totals = np.where(finite, best, 0.0).sum(axis=1)
    sampled = np.where(counts > 0, totals / np.maximum(counts, 1), 0.0)

    restored = np.empty(total, dtype=np.float64)
    restored[order] = sampled
    if total == points.shape[0]:
        return restored
    # The cloud was sampled: give every point the value of its sampled
    # neighbour along the same curve, which preserves the spatial pattern.
    return np.repeat(restored, int(np.ceil(points.shape[0] / total)))[
        : points.shape[0]
    ]


def bounds(positions, np):
    """World-space min/max of a Splat set, for framing the view."""
    return (
        np.asarray(positions, dtype=np.float32).min(axis=0),
        np.asarray(positions, dtype=np.float32).max(axis=0),
    )
