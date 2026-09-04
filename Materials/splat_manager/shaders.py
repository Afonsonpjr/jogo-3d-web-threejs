# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
# ##### END GPL LICENSE BLOCK #####

"""The viewer's four visualization modes, in one shader program.

All four draw the same instanced quad from the same packed buffer and differ
only in how the quad is sized and shaded, so they share one program and one
uniform set. Switching modes is a uniform change, not a pipeline rebuild, and
adding a fifth mode means one more branch rather than another program.

    0  GAUSSIAN  the standard splat: projected covariance, alpha falloff
    1  POINTS    a flat dot per Splat, for inspecting distribution and density
    2  RINGS     the 1-sigma contour only, for reading size and orientation
    3  CENTERS   a small fixed dot at each Gaussian's centre
"""

MODE_GAUSSIAN = 0
MODE_POINTS = 1
MODE_RINGS = 2
MODE_CENTERS = 3

MODE_VALUES = {
    "GAUSSIAN": MODE_GAUSSIAN,
    "POINTS": MODE_POINTS,
    "RINGS": MODE_RINGS,
    "CENTERS": MODE_CENTERS,
}

_shader = None
_batch = None


_VERTEX_SHADER = r"""
#define SH_C0 0.28209479177387814
#define SH_C1 0.4886025119029199
#define SH_C2_0 1.0925484305920792
#define SH_C2_1 -1.0925484305920792
#define SH_C2_2 0.31539156525252005
#define SH_C2_3 -1.0925484305920792
#define SH_C2_4 0.5462742152960396
#define SH_C3_0 -0.5900435899266435
#define SH_C3_1 2.890611442640554
#define SH_C3_2 -0.4570457994644658
#define SH_C3_3 0.3731763325901154
#define SH_C3_4 -0.4570457994644658
#define SH_C3_5 1.445305721320277
#define SH_C3_6 -0.5900435899266435

float fetchFloat(int index)
{
    int texel = index >> 2;
    int width = textureSize(gaussian_data, 0).x;
    int y = texel / width;
    vec4 block = texelFetch(gaussian_data, ivec2(texel - y * width, y), 0);
    int component = index & 3;
    if (component == 0) { return block.x; }
    if (component == 1) { return block.y; }
    if (component == 2) { return block.z; }
    return block.w;
}

vec3 fetchSH(int base, int coefficient)
{
    int index = base + 11 + coefficient * 3;
    return vec3(
        fetchFloat(index),
        fetchFloat(index + 1),
        fetchFloat(index + 2)
    );
}

mat3 computeCov3D(vec3 scale, vec4 q)
{
    mat3 S = mat3(0.0);
    S[0][0] = scale.x;
    S[1][1] = scale.y;
    S[2][2] = scale.z;

    float r = q.x;
    float x = q.y;
    float y = q.z;
    float z = q.w;

    mat3 R = mat3(
        1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - r * z), 2.0 * (x * z + r * y),
        2.0 * (x * y + r * z), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - r * x),
        2.0 * (x * z - r * y), 2.0 * (y * z + r * x), 1.0 - 2.0 * (x * x + y * y)
    );

    mat3 M = S * R;
    return transpose(M) * M;
}

vec3 computeCov2D(
    vec4 mean_view,
    float focal_x,
    float focal_y,
    float tan_fovx,
    float tan_fovy,
    mat3 cov3D,
    mat4 view_matrix,
    bool is_orthographic
)
{
    vec4 t = mean_view;
    mat3 J;
    if (is_orthographic) {
        J = mat3(
            focal_x, 0.0, 0.0,
            0.0, focal_y, 0.0,
            0.0, 0.0, 0.0
        );
    } else {
        float limx = 1.3 * tan_fovx;
        float limy = 1.3 * tan_fovy;
        float txtz = t.x / t.z;
        float tytz = t.y / t.z;
        t.x = min(limx, max(-limx, txtz)) * t.z;
        t.y = min(limy, max(-limy, tytz)) * t.z;

        J = mat3(
            focal_x / t.z, 0.0, -(focal_x * t.x) / (t.z * t.z),
            0.0, focal_y / t.z, -(focal_y * t.y) / (t.z * t.z),
            0.0, 0.0, 0.0
        );
    }

    mat3 W = transpose(mat3(view_matrix));
    mat3 T = W * J;
    mat3 cov = transpose(T) * transpose(cov3D) * T;

    // Screen-space low-pass filter. Without this a Splat smaller than a
    // pixel aliases instead of fading.
    cov[0][0] += 0.3;
    cov[1][1] += 0.3;
    return vec3(cov[0][0], cov[0][1], cov[1][1]);
}

void main()
{
    int indices_width = textureSize(sorted_indices, 0).x;
    int row = gl_InstanceID / indices_width;
    int column = gl_InstanceID - row * indices_width;
    int splat = int(
        texelFetch(sorted_indices, ivec2(column, row), 0).r + 0.5
    );
    int base = splat * splat_stride;

    vec3 g_pos = vec3(
        fetchFloat(base + 0),
        fetchFloat(base + 1),
        fetchFloat(base + 2)
    );
    vec4 g_rot = vec4(
        fetchFloat(base + 3),
        fetchFloat(base + 4),
        fetchFloat(base + 5),
        fetchFloat(base + 6)
    );
    vec3 g_scale = vec3(
        fetchFloat(base + 7),
        fetchFloat(base + 8),
        fetchFloat(base + 9)
    ) * splat_scale;
    float g_opacity = fetchFloat(base + 10);

    vec4 pos_view = ModelViewMatrix * vec4(g_pos, 1.0);
    vec4 pos_clip = ProjectionMatrix * pos_view;
    bool is_orthographic = (ProjectionMatrix[3][3] > 0.5);
    if (pos_clip.w <= 1.0e-8 && !is_orthographic) {
        gl_Position = vec4(-100.0, -100.0, -100.0, 1.0);
        return;
    }
    pos_clip.xyz = pos_clip.xyz / pos_clip.w;
    pos_clip.w = 1.0;
    if (any(greaterThan(abs(pos_clip.xyz), vec3(1.3)))) {
        gl_Position = vec4(-100.0, -100.0, -100.0, 1.0);
        return;
    }

    // Colour is shared by every mode: even the debug views read better when
    // each Splat keeps its own colour.
    vec3 direction = normalize(g_pos - camera_local);
    vec3 colour = SH_C0 * fetchSH(base, 0);
    if (sh_degree >= 1) {
        float x = direction.x;
        float y = direction.y;
        float z = direction.z;
        colour = colour
            - SH_C1 * y * fetchSH(base, 1)
            + SH_C1 * z * fetchSH(base, 2)
            - SH_C1 * x * fetchSH(base, 3);
        if (sh_degree >= 2) {
            float xx = x * x, yy = y * y, zz = z * z;
            float xy = x * y, yz = y * z, xz = x * z;
            colour = colour
                + SH_C2_0 * xy * fetchSH(base, 4)
                + SH_C2_1 * yz * fetchSH(base, 5)
                + SH_C2_2 * (2.0 * zz - xx - yy) * fetchSH(base, 6)
                + SH_C2_3 * xz * fetchSH(base, 7)
                + SH_C2_4 * (xx - yy) * fetchSH(base, 8);
            if (sh_degree >= 3) {
                colour = colour
                    + SH_C3_0 * y * (3.0 * xx - yy) * fetchSH(base, 9)
                    + SH_C3_1 * xy * z * fetchSH(base, 10)
                    + SH_C3_2 * y * (4.0 * zz - xx - yy) * fetchSH(base, 11)
                    + SH_C3_3 * z * (2.0 * zz - 3.0 * xx - 3.0 * yy) * fetchSH(base, 12)
                    + SH_C3_4 * x * (4.0 * zz - xx - yy) * fetchSH(base, 13)
                    + SH_C3_5 * z * (xx - yy) * fetchSH(base, 14)
                    + SH_C3_6 * x * (xx - 3.0 * yy) * fetchSH(base, 15);
            }
        }
    }
    v_color = max(colour + 0.5, vec3(0.0));
    v_opacity = g_opacity;

    if (render_mode == 1 || render_mode == 3) {
        // Points and centres are a fixed screen-space size, so density reads
        // the same whatever the Splat's own extent happens to be.
        vec2 extent = vec2(point_size);
        v_conic = vec3(0.0);
        v_coordxy = quad_coord * extent;
        pos_clip.xy = pos_clip.xy + quad_coord * (extent / viewport * 2.0);
        gl_Position = pos_clip;
        return;
    }

    float proj_x = ProjectionMatrix[0][0];
    float proj_y = ProjectionMatrix[1][1];
    float focal_x = viewport.x * 0.5 * proj_x;
    float focal_y = viewport.y * 0.5 * proj_y;
    float tan_fovx = (abs(proj_x) > 1.0e-8) ? (1.0 / proj_x) : 1.0;
    float tan_fovy = (abs(proj_y) > 1.0e-8) ? (1.0 / proj_y) : 1.0;

    mat3 cov3d = computeCov3D(g_scale, g_rot);
    vec3 cov2d = computeCov2D(
        pos_view, focal_x, focal_y, tan_fovx, tan_fovy,
        cov3d, ModelViewMatrix, is_orthographic
    );

    float det = cov2d.x * cov2d.z - cov2d.y * cov2d.y;
    if (det <= 0.0) {
        gl_Position = vec4(-100.0, -100.0, -100.0, 1.0);
        return;
    }
    float det_inv = 1.0 / det;
    v_conic = vec3(cov2d.z * det_inv, -cov2d.y * det_inv, cov2d.x * det_inv);

    vec2 extent = vec2(3.0 * sqrt(cov2d.x), 3.0 * sqrt(cov2d.z));
    v_coordxy = quad_coord * extent;
    pos_clip.xy = pos_clip.xy + quad_coord * (extent / viewport * 2.0);
    gl_Position = pos_clip;
}
"""


_FRAGMENT_SHADER = r"""
vec3 srgbToLinear(vec3 colour)
{
    // The custom viewport pass writes into Blender's sRGB framebuffer, so
    // shader output must be linear for the hardware encoding to land on the
    // intended display-referred bytes.
    vec3 c = clamp(colour, vec3(0.0), vec3(1.0));
    vec3 low = c * (1.0 / 12.92);
    vec3 high = pow((c + 0.055) * (1.0 / 1.055), vec3(2.4));
    return mix(low, high, step(vec3(0.04045), c));
}

void main()
{
    if (render_mode == 1 || render_mode == 3) {
        // A round dot, sized in pixels by the vertex stage.
        float radius = length(v_coordxy) / max(point_size, 1.0e-6);
        if (radius > 1.0) {
            discard;
        }
        float edge = smoothstep(1.0, 0.75, radius);
        vec3 colour = (render_mode == 3) ? mix(v_color, vec3(1.0), 0.35)
                                         : v_color;
        float alpha = (render_mode == 3) ? edge
                                         : edge * clamp(v_opacity + 0.25, 0.0, 1.0);
        if (alpha < 0.00392) {
            discard;
        }
        fragColor = vec4(srgbToLinear(colour), alpha);
        return;
    }

    float power =
        -0.5 * (
            v_conic.x * v_coordxy.x * v_coordxy.x
            + v_conic.z * v_coordxy.y * v_coordxy.y
        )
        - v_conic.y * v_coordxy.x * v_coordxy.y;

    if (render_mode == 2) {
        // The 1-sigma contour is where the Gaussian exponent reaches -0.5.
        // Keeping a thin band around it draws the ellipse as an outline, so
        // overlapping Splats stay individually readable.
        float distance_to_ring = abs(power + 0.5);
        if (distance_to_ring > ring_width) {
            discard;
        }
        float alpha = 1.0 - (distance_to_ring / max(ring_width, 1.0e-6));
        fragColor = vec4(srgbToLinear(v_color), alpha * 0.9);
        return;
    }

    if (power > 0.0) {
        discard;
    }
    float alpha = min(0.99, v_opacity * exp(power));
    if (alpha < 0.00392) {
        discard;
    }
    fragColor = vec4(srgbToLinear(v_color), alpha);
}
"""


def get():
    """The shared shader program and quad batch, built on first use."""
    global _shader, _batch
    if _shader is not None and _batch is not None:
        return _shader, _batch

    import gpu
    import numpy as np
    from gpu_extras.batch import batch_for_shader

    info = gpu.types.GPUShaderCreateInfo()
    info.vertex_in(0, "VEC2", "quad_coord")
    info.push_constant("MAT4", "ModelViewMatrix")
    info.push_constant("MAT4", "ProjectionMatrix")
    info.push_constant("VEC3", "camera_local")
    info.push_constant("VEC2", "viewport")
    info.push_constant("FLOAT", "splat_scale")
    info.push_constant("FLOAT", "point_size")
    info.push_constant("FLOAT", "ring_width")
    info.push_constant("INT", "splat_stride")
    info.push_constant("INT", "sh_degree")
    info.push_constant("INT", "render_mode")
    info.sampler(0, "FLOAT_2D", "gaussian_data")
    info.sampler(1, "FLOAT_2D", "sorted_indices")

    interface = gpu.types.GPUStageInterfaceInfo("splatgen_viewer_interface")
    interface.smooth("VEC3", "v_conic")
    interface.smooth("VEC2", "v_coordxy")
    interface.smooth("VEC3", "v_color")
    interface.smooth("FLOAT", "v_opacity")
    info.vertex_out(interface)
    info.fragment_out(0, "VEC4", "fragColor")
    info.vertex_source(_VERTEX_SHADER)
    info.fragment_source(_FRAGMENT_SHADER)
    _shader = gpu.shader.create_from_info(info)

    quad = np.asarray(
        [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)], dtype=np.float32
    )
    indices = np.asarray((0, 1, 2, 0, 2, 3), dtype=np.uint32)
    _batch = batch_for_shader(
        _shader, "TRIS", {"quad_coord": quad}, indices=indices
    )
    return _shader, _batch


def release():
    global _shader, _batch
    _shader = None
    _batch = None
