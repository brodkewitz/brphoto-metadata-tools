#!/usr/bin/env uv run

"""
Created 2025-07-06

Write Apple Photos compatible video metadata from original files to transcoded copies

- Creation Date (original capture time)
- Camera Make
- Camera Model
- Lens info, if available
- GPS coordinates, if available
"""

from pathlib import Path

import exiftool


files = [
    Path("..."),
    Path("..."),
    Path("..."),
]


def generate_paths(rendered_video_path: Path):
    src_video_name = Path(
        rendered_video_path.name.replace(
            "-optimized-hevc-12mbps-vbr-multipass", ""
        )
    ).with_suffix(".MP4")
    parents = list(rendered_video_path.resolve().parents)
    for p in parents:
        # Climb up until we're out of the output directory
        if "/Output" not in str(p):
            src_dir = p / "Selects"
            break
    src_video_path = src_dir / src_video_name
    if not src_video_path.is_file:
        src_video_path = None
    src_xmp_path = src_dir / src_video_name.with_suffix(".xmp")
    if not src_xmp_path.is_file:
        src_xmp_path = None
    return src_video_path, src_xmp_path


def write_apple_photos_metadata(
    rendered_video_path: Path,
    src_video_path: Path | None,
    src_xmp_path: Path | None,
):
    with exiftool.ExifToolHelper() as et:
        params = []
        if not (src_video_path or src_xmp_path):
            print("No source files to copy metadata from")
            print(rendered_video_path.name)
            return
        if src_video_path:
            params.append("-TagsFromFile")
            params.append(src_video_path)
            params.append("-XML:DeviceManufacturer>Keys:Make")
            params.append("-XML:DeviceModelName>Keys:Model")
        if src_xmp_path:
            params.append("-TagsFromFile")
            params.append(src_xmp_path)
            params.append("-All")
            params.append("-CreateDate>Keys:CreationDate")
            params.append("-GPSPosition>Keys:GPSCoordinates")
        params.append(rendered_video_path)
        print(f"Writing metadata to {rendered_video_path.name}")
        result = et.execute(*params)
        print(result)
        # print(et.execute("-G0:1", "-s2", "-a", "-sort", rendered_video_path))


if __name__ == "__main__":
    for rendered_video_path in files:
        src_video_path, src_xmp_path = generate_paths(rendered_video_path)
        write_apple_photos_metadata(
            rendered_video_path, src_video_path, src_xmp_path
        )
