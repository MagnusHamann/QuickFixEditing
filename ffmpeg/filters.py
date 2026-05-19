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
    # Baseline cartoon anonymisation using generous line detection only. This
    # is based on the previous detailed-cartoon recipe, nudged only slightly
    # toward more fine edges while avoiding source grayscale blending.
    return (
        "format=gray,hqdn3d=0.7:0.7:1.4:1.4,split=2[fine][coarse];"
        "[fine]unsharp=9:9:1.8,edgedetect=low=0.0009:high=0.008,"
        "negate,eq=contrast=1.30:brightness=0.03[fineink];"
        "[coarse]unsharp=5:5:1.1,edgedetect=low=0.005:high=0.032,"
        "negate,eq=contrast=1.15:brightness=0.06[coarseink];"
        "[fineink][coarseink]blend=all_mode=multiply:all_opacity=0.72,"
        "eq=contrast=1.12:brightness=0.04,format=gray"
    )


def detailed_line_drawing_filter() -> str:
    # Detailed cartoon anonymisation. Three generous edge passes preserve fine
    # facial, clothing, hand, and object lines, while a blurred posterised
    # branch adds broad shadow shapes without restoring plain source footage.
    return (
        "format=gray,hqdn3d=0.35:0.35:0.9:0.9,split=4[micro][fine][coarse][shade];"
        "[shade]gblur=sigma=2.2,eq=contrast=1.65:brightness=-0.06,"
        "curves=all='0/0.42 0.22/0.56 0.48/0.80 0.72/0.94 1/1'[shadow];"
        "[micro]unsharp=11:11:2.0,edgedetect=low=0.00035:high=0.0045,"
        "negate,eq=contrast=1.18:brightness=0.055[microink];"
        "[fine]unsharp=9:9:1.8,edgedetect=low=0.0007:high=0.007,"
        "negate,eq=contrast=1.25:brightness=0.045[fineink];"
        "[coarse]unsharp=5:5:1.2,edgedetect=low=0.004:high=0.025,"
        "negate,eq=contrast=1.12:brightness=0.07[coarseink];"
        "[microink][fineink]blend=all_mode=multiply:all_opacity=0.82[tmp];"
        "[tmp][coarseink]blend=all_mode=multiply:all_opacity=0.72[ink];"
        "[shadow][ink]blend=all_mode=multiply:all_opacity=0.88,"
        "eq=contrast=1.12:brightness=0.025,format=gray"
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
