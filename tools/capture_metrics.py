"""Image measurements for native capture validation, independent of Kit imports.

Exploratory contrast targets describe measurements, never product acceptance.
"""
from PIL import Image, ImageChops, ImageStat


def mean_rgb_difference(before, after):
    with Image.open(before) as first, Image.open(after) as second:
        if first.size != second.size:
            raise ValueError('Capture sizes differ; image comparison refused')
        difference = ImageChops.difference(first.convert('RGB'), second.convert('RGB'))
        return sum(ImageStat.Stat(difference).mean) / 3


def surface_deviation(wire_only, faint, opaque):
    faint_mean = mean_rgb_difference(wire_only, faint)
    opaque_mean = mean_rgb_difference(wire_only, opaque)
    ratio = faint_mean / opaque_mean if opaque_mean else None
    return dict(faint_mean_rgb_difference_from_wire_only=faint_mean,
                opaque_mean_rgb_difference_from_wire_only=opaque_mean,
                ratio=ratio, quarter_target_passed=ratio is not None and ratio < .25,
                acceptance_gate=False)
