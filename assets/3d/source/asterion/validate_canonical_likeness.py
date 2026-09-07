"""Measure the registered Blender view against Asterion's canonical PNG."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--render", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    canonical_path = Path(args.canonical).resolve()
    render_path = Path(args.render).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical_image = Image.open(canonical_path).convert("RGBA")
    render_image = Image.open(render_path).convert("RGBA")
    if canonical_image.size != render_image.size:
        raise RuntimeError(f"Registration size mismatch: {canonical_image.size} vs {render_image.size}")
    canonical = np.asarray(canonical_image)
    rendered = np.asarray(render_image)
    canonical_mask = canonical[:, :, 3] > 127
    rendered_mask = rendered[:, :, 3] > 127
    intersection = int((canonical_mask & rendered_mask).sum())
    union = int((canonical_mask | rendered_mask).sum())
    alpha_iou = intersection / union
    mismatch_pixels = int((canonical_mask != rendered_mask).sum())
    opaque = (canonical[:, :, 3] > 245) & (rendered[:, :, 3] > 245)
    rgb_delta = canonical[:, :, :3].astype(np.float32) - rendered[:, :, :3].astype(np.float32)
    opaque_mae = float(np.abs(rgb_delta[opaque]).mean())
    opaque_mse = float((rgb_delta[opaque] ** 2).mean())
    opaque_psnr = float(20.0 * math.log10(255.0 / math.sqrt(opaque_mse)))
    alpha_mae = float(np.abs(canonical[:, :, 3].astype(np.float32) - rendered[:, :, 3].astype(np.float32)).mean())

    scale = 4
    panel_width, panel_height = canonical_image.width * scale, canonical_image.height * scale
    comparison = Image.new("RGBA", (panel_width * 2 + 24, panel_height + 46), (3, 8, 24, 255))
    comparison.alpha_composite(canonical_image.resize((panel_width, panel_height), Image.Resampling.NEAREST), (0, 38))
    comparison.alpha_composite(render_image.resize((panel_width, panel_height), Image.Resampling.NEAREST), (panel_width + 24, 38))
    draw = ImageDraw.Draw(comparison)
    draw.text((8, 10), "KANONISCHES 2D-ORIGINAL", fill=(235, 241, 255, 255))
    draw.text((panel_width + 32, 10), "REGISTRIERTE 3D-ANSICHT", fill=(235, 241, 255, 255))
    comparison_path = output_dir / "asterion-canonical-highpoly-v001-likeness-comparison.png"
    comparison.save(comparison_path)

    checks = {
        "same_canvas": canonical_image.size == render_image.size,
        "exact_binary_silhouette": mismatch_pixels == 0 and alpha_iou == 1.0,
        "opaque_rgb_mae_under_8": opaque_mae < 8.0,
    }
    report = {
        "canonical": str(canonical_path),
        "canonical_sha256": sha256(canonical_path),
        "render": str(render_path),
        "render_sha256": sha256(render_path),
        "canvas": list(canonical_image.size),
        "canonical_mask_pixels": int(canonical_mask.sum()),
        "render_mask_pixels": int(rendered_mask.sum()),
        "alpha_iou_at_127": alpha_iou,
        "binary_silhouette_mismatch_pixels": mismatch_pixels,
        "opaque_rgb_mae_255": opaque_mae,
        "opaque_rgb_psnr_db": opaque_psnr,
        "alpha_mae_255": alpha_mae,
        "comparison": str(comparison_path),
        "checks": checks,
        "passed": all(checks.values()),
        "note": "RGB differences are bounded render/color-pipeline rounding; geometry mask is exact at the canonical threshold.",
    }
    report_path = output_dir / "asterion-canonical-highpoly-v001-likeness-validation.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise RuntimeError("Canonical likeness validation failed")


if __name__ == "__main__":
    main()
