"""Composable FFmpeg video filters."""

from __future__ import annotations


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


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


def line_drawing_filter(detail: int = 50) -> str:
    # Baseline cartoon anonymisation using generous line detection only. This
    # is based on the previous detailed-cartoon recipe, nudged only slightly
    # toward more fine edges while avoiding source grayscale blending.
    detail_factor = _clamp(detail, 0, 100) / 50 if detail else 0.2
    fine_low = _clamp(0.0009 / max(detail_factor, 0.2), 0.00035, 0.003)
    fine_high = _clamp(0.008 / max(detail_factor, 0.2), 0.004, 0.020)
    coarse_low = _clamp(0.005 / max(detail_factor, 0.2), 0.0025, 0.012)
    coarse_high = _clamp(0.032 / max(detail_factor, 0.2), 0.015, 0.060)
    contrast = _clamp(1.04 + detail_factor * 0.08, 1.04, 1.22)
    return (
        "format=gray,hqdn3d=0.7:0.7:1.4:1.4,split=2[fine][coarse];"
        f"[fine]unsharp=9:9:1.8,edgedetect=low={fine_low:.5f}:high={fine_high:.5f},"
        "negate,eq=contrast=1.30:brightness=0.03[fineink];"
        f"[coarse]unsharp=5:5:1.1,edgedetect=low={coarse_low:.5f}:high={coarse_high:.5f},"
        "negate,eq=contrast=1.15:brightness=0.06[coarseink];"
        "[fineink][coarseink]blend=all_mode=multiply:all_opacity=0.72,"
        f"eq=contrast={contrast:.2f}:brightness=0.04,format=gray"
    )


def detailed_line_drawing_filter(detail: int = 55, shadows: int = 60) -> str:
    # Detailed cartoon anonymisation. Three generous edge passes preserve fine
    # facial, clothing, hand, and object lines, while a blurred posterised
    # branch adds broad shadow shapes without restoring plain source footage.
    detail_factor = _clamp(detail, 0, 100) / 55 if detail else 0.2
    shadow_factor = _clamp(shadows, 0, 100) / 60 if shadows else 0.0
    micro_low = _clamp(0.00035 / max(detail_factor, 0.2), 0.00018, 0.0012)
    micro_high = _clamp(0.0045 / max(detail_factor, 0.2), 0.002, 0.012)
    fine_low = _clamp(0.0007 / max(detail_factor, 0.2), 0.00025, 0.002)
    fine_high = _clamp(0.007 / max(detail_factor, 0.2), 0.003, 0.016)
    coarse_low = _clamp(0.004 / max(detail_factor, 0.2), 0.0018, 0.010)
    coarse_high = _clamp(0.025 / max(detail_factor, 0.2), 0.012, 0.050)
    shadow_sigma = _clamp(1.2 + shadow_factor * 1.0, 1.2, 3.2)
    shadow_contrast = _clamp(1.10 + shadow_factor * 0.55, 1.10, 2.10)
    shadow_opacity = _clamp(0.45 + shadow_factor * 0.26, 0.45, 0.90)
    return (
        "format=gray,hqdn3d=0.35:0.35:0.9:0.9,split=4[micro][fine][coarse][shade];"
        f"[shade]gblur=sigma={shadow_sigma:.2f},eq=contrast={shadow_contrast:.2f}:brightness=-0.06,"
        "curves=all='0/0.42 0.22/0.56 0.48/0.80 0.72/0.94 1/1'[shadow];"
        f"[micro]unsharp=11:11:2.0,edgedetect=low={micro_low:.5f}:high={micro_high:.5f},"
        "negate,eq=contrast=1.18:brightness=0.055[microink];"
        f"[fine]unsharp=9:9:1.8,edgedetect=low={fine_low:.5f}:high={fine_high:.5f},"
        "negate,eq=contrast=1.25:brightness=0.045[fineink];"
        f"[coarse]unsharp=5:5:1.2,edgedetect=low={coarse_low:.5f}:high={coarse_high:.5f},"
        "negate,eq=contrast=1.12:brightness=0.07[coarseink];"
        "[microink][fineink]blend=all_mode=multiply:all_opacity=0.82[tmp];"
        "[tmp][coarseink]blend=all_mode=multiply:all_opacity=0.72[ink];"
        f"[shadow][ink]blend=all_mode=multiply:all_opacity={shadow_opacity:.2f},"
        "eq=contrast=1.12:brightness=0.025,format=gray"
    )


def pixelation_filter(block_size: int = 20) -> str:
    block = int(_clamp(block_size, 4, 50))
    return f"scale=iw/{block}:ih/{block},scale=iw*{block}:ih*{block}:flags=neighbor,setsar=1"


def blur_filter(sigma: int = 20) -> str:
    return f"gblur=sigma={int(_clamp(sigma, 1, 60))}"


def silhouette_filter(strength: int = 50) -> str:
    # A true person-mask silhouette needs segmentation. This local-only FFmpeg
    # recipe deliberately reduces the whole frame into coarse high-contrast
    # shapes, preserving motion while discarding detail.
    factor = _clamp(strength, 0, 100) / 100
    sigma = 4 + factor * 14
    contrast = 2.2 + factor * 1.8
    brightness = -0.12 - factor * 0.20
    low = 0.40 + factor * 0.12
    high = low + 0.14
    return (
        f"format=gray,gblur=sigma={sigma:.1f},eq=contrast={contrast:.2f}:brightness={brightness:.2f},"
        f"curves=all='0/0 {low:.2f}/0 {high:.2f}/1 1/1',format=gray"
    )


def grayscale_filter(contrast: int = 100) -> str:
    contrast_value = _clamp(contrast, 50, 180) / 100
    return f"format=gray,eq=contrast={contrast_value:.2f}"


def resize_filter(height: int) -> str:
    return f"scale=-2:{height}"
