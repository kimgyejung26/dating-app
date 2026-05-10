# Stamp Scene GLB Requirements

Place the production 3D model at:

```text
assets/models/stamp_scene.glb
```

The committed `stamp_scene.glb` is a text sentinel only, not a real 3D model.
It exists so Flutter's explicit asset registration can pass analysis and test
bundle validation without generating an arbitrary binary model. Replace it with
the real Blender export using the same file name.

## Recommended Node Structure

- `StampRoot`
- `StampHandle`
- `StampBody`
- `StampBottom`
- `Paper`
- `InkDecal`

## Recommended Animation Clip

Use an animation named `Stamp`, or another name containing `stamp`.

Avoid special characters in animation names. Plain ASCII names such as `Stamp`,
`StampDown`, or `stamp_press` are safest across Flutter, Android, iOS, and Web.

## Timeline Example

- Frame 1: the stamp starts above the paper with a slight tilt.
- Frame 10: the stamp moves down quickly.
- Frame 13: the stamp contacts the paper.
- Frame 13-18: `InkDecal` scale animates from `0.001` to `1.08` to `1.0`.
- Frame 17 onward: the stamp rebounds slightly upward.
- Frame 28-32: the stamp settles into its final position.

Prefer animating `InkDecal` scale over material opacity for the ink mark. Scale
animation exports more reliably in GLB pipelines and avoids platform-specific
transparency sorting artifacts.
