"""Composable FFmpeg video filters."""

from __future__ import annotations


def audio_distortion_filter() -> str:
    # TV-style anonymisation: pitch is raised slightly, timing is compensated
    # back into sync, and the spectrum is narrowed to reduce voice naturalness.
    return (
        "aresample=48000,"
        "asetrate=48000*1.08,"
        "aresample=48000,"
        "atempo=0.925926,"
        "highpass=f=120,"
        "lowpass=f=6500,"
        "acompressor=threshold=0.08:ratio=2.5:attack=20:release=250:makeup=1.5,"
        "alimiter=limit=0.95"
    )


def line_drawing_filter() -> str:
    # Baseline cartoon treatment. One branch keeps grayscale shading while a
    # second branch extracts fine black edges; multiply blending gives a pencil
    # cartoon look while still reducing natural video appearance.
    return (
        "format=gray,eq=contrast=1.15:brightness=0.03,"
        "split=2[shade][edge];"
        "[edge]unsharp=5:5:1.0,edgedetect=low=0.005:high=0.030,negate[ink];"
        "[shade]eq=contrast=1.75:brightness=-0.08,"
        "curves=all='0/0 0.34/0.18 0.68/0.74 1/1'[tones];"
        "[tones][ink]blend=all_mode=multiply:all_opacity=0.80,"
        "unsharp=3:3:0.7,format=gray"
    )


def detailed_line_drawing_filter() -> str:
    # Very light anonymisation for close review. This intentionally preserves
    # far more source detail than the cartoon mode: it is closer to sharpened
    # black-and-white review footage than to line-art anonymisation.
    return (
        "format=gray,"
        "hqdn3d=1.2:1.2:2.5:2.5,"
        "unsharp=7:7:1.8,"
        "eq=contrast=1.22:brightness=0.035:saturation=0,"
        "curves=all='0/0 0.18/0.12 0.50/0.53 0.82/0.88 1/1',"
        "format=gray"
    )


def pixelation_filter() -> str:
    return "scale=iw/20:ih/20,scale=iw*20:ih*20:flags=neighbor,setsar=1"


def blur_filter() -> str:
    return "gblur=sigma=20"


def silhouette_filter() -> str:
    # A true person-mask silhouette needs segmentation. This local-only FFmpeg
    # recipe deliberately reduces the whole frame into coarse high-contrast
    # shapes, preserving motion while discarding detail.
    return "format=gray,gblur=sigma=10,eq=contrast=3.0:brightness=-0.22,curves=all='0/0 0.48/0 0.62/1 1/1',format=gray"


def grayscale_filter() -> str:
    return "format=gray"


def resize_filter(height: int) -> str:
    return f"scale=-2:{height}"
