#!/usr/bin/env uv run

"""
Created 2025-06-25

Write descriptions (e.g. alt text) to image metadata description fields.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import click
import exiftool


# Name exports for shorter import statements in other scripts
__all__ = [
    "RAW_TYPES",
    "JPG_TYPES",
    "XMP_TYPES",
    "TYPE_PRIORITIES",
    "Image",
    "process_tsv_input",
    "select_preferred_path",
    "find_matching_files",
    "write_descriptions",
    "main",
]


XMP_TYPES: set = {".xmp"}
RAW_TYPES: set = {".arw", ".cr2", ".dng", ".raf", ".nef"}
JPG_TYPES: set = {".jpg", ".jpeg", ".heic"}
ALL_AVAILABLE_TYPES = XMP_TYPES | RAW_TYPES | JPG_TYPES
TYPE_PRIORITIES: dict = {
    **{ext: 3 for ext in XMP_TYPES},
    **{ext: 2 for ext in RAW_TYPES},
    **{ext: 1 for ext in JPG_TYPES},
}


@dataclass
class Image:
    line_no: int
    input_file_path: Path
    input_desc: str
    found_file_path: Path | None = None


def process_tsv_input(input_descriptions: list[str]) -> Mapping[str, Image]:
    """Parse incoming filenames and descripions. Check for basic errors.

    Returns a dict with filename stems as keys and Image classes as values.
    """
    images = dict()
    seen_stems = set()
    seen_dup_stems = set()
    duplicates = list()

    for line_no, line in enumerate(input_descriptions, start=1):
        # Skip empty lines
        if not line.strip():
            continue

        # Abort if a line can't be parsed
        try:
            input_file_str, input_desc = line.strip().split("\t")
            input_file_path = Path(input_file_str)
            file_stem = input_file_path.stem
        except ValueError:
            click.secho(
                (f"Error parsing line {line_no}: {line}"),
                fg="red",
                err=True,
            )
            raise

        # Check for and collect duplicates based on file stem
        if file_stem not in seen_stems:
            seen_stems.add(file_stem)
        else:
            # We have a duplicate
            if file_stem not in seen_dup_stems:
                seen_dup_stems.add(file_stem)
                # This is the first duplicate, meaning the second occurrence,
                # add the first
                first_occurrence = images[file_stem]
                duplicates.append(
                    {
                        "line_no": first_occurrence.line_no,
                        "input_file_path": first_occurrence.input_file_path,
                    }
                )
            duplicates.append(
                {"line_no": line_no, "input_file_path": input_file_path}
            )

        new_image = Image(
            line_no=line_no,
            input_file_path=Path(input_file_path),
            input_desc=input_desc,
        )
        images[file_stem] = new_image

    # Abort if duplicate file stems were found.
    if duplicates:
        click.secho(
            "Duplicate file stems found for the following filenames:",
            fg="red",
            err=True,
        )
        for d in duplicates:
            click.secho(
                f"  {d['line_no']}: {d['input_file_path']}", fg="red", err=True
            )
        click.secho(
            "Filenames, excluding file type, must be unique.",
            fg="red",
            err=True,
        )
        raise SystemExit(1)

    return images


def select_preferred_path(cur_path: Path | None, new_path: Path) -> Path:
    """Implement file type priorities and conflict checking

    - Prioritize XMP > RAW_TYPES
    - Abort if both a JPG type and any RAW/XMP type is found
    """
    # Check that new_path is an available type. We should never get to this
    # code path if the file search function is working correctly.
    if new_path.suffix.lower() not in ALL_AVAILABLE_TYPES:
        raise ValueError(f"Unavailable file type: {new_path}")

    # Check that we're not comparing two files in the same type set. We should
    # never get to this code path if the file search function is working
    # correctly.
    if cur_path and new_path:
        combined_suffix_set = {
            cur_path.suffix.lower(),
            new_path.suffix.lower(),
        }
        if (
            combined_suffix_set.issubset(RAW_TYPES)
            or combined_suffix_set.issubset(JPG_TYPES)
            or combined_suffix_set.issubset(XMP_TYPES)
        ):
            raise ValueError(
                (
                    "Comparing two files of same rank:\n  "
                    f"{cur_path}\n  {new_path}"
                )
            )

    # Look up file type priorities
    if cur_path is not None:
        cur_path_priority = TYPE_PRIORITIES[cur_path.suffix.lower()]
    else:
        cur_path_priority = 0
    new_path_priority = TYPE_PRIORITIES[new_path.suffix.lower()]

    # First file found
    if cur_path_priority == 0:
        click.echo(f"Found {new_path.stem} -> {new_path}")
        return new_path
    # More than one file found, and one of them is jpg type
    if cur_path_priority == 1 or new_path_priority == 1:
        click.secho(
            (
                f"Found both a jpg type and raw/xmp type for {new_path.stem}, "
                f"will not write to both:\n  {cur_path}\n  {new_path}"
            ),
            fg="red",
            err=True,
        )
        raise SystemExit(1)
    # Prioritize between xmp and raw
    if new_path_priority > cur_path_priority:
        click.echo(f"Updating {new_path.stem} -> {new_path}")
        return new_path

    return cur_path


def find_matching_files(
    search_dir: Path,
    images: Mapping[str, Image],
    ignore_jpg: bool,
    max_scan_items: int,
) -> Mapping[str, Image]:
    """Rescursively search for matching files

    - Ignore CaptureOne/ directories
    - Filter for only the available image types
    - Abort after checking max_scan_items. We probably didn't mean to search a
      directory tree that large.
    """
    scanned = 0
    ignore_dirs = {"CaptureOne"}

    # Be careful not to mutate ALL_AVAILABLE_TYPES using regular = assignment,
    # or -= mutation in place
    file_type_filter = set(ALL_AVAILABLE_TYPES)
    if ignore_jpg:
        file_type_filter = ALL_AVAILABLE_TYPES - JPG_TYPES

    for (
        current_dir,
        subdirs,
        files,
    ) in search_dir.walk():
        # Prune excluded subdirs in place
        subdirs[:] = [d for d in subdirs if d not in ignore_dirs]

        for file in files:
            file = Path(file)
            # scanned counter should increment whether files are a match or not
            scanned += 1
            if scanned > max_scan_items:
                click.secho(
                    f"Aborted after scanning {max_scan_items} files.",
                    fg="red",
                    err=True,
                )
                raise SystemExit(1)
            if file.suffix.lower() not in file_type_filter:
                print(f"Skipping unavailable type {file}")
                continue
            if file.stem not in images.keys():
                continue

            # Found a file from the input list
            cur_path = images[file.stem].found_file_path
            new_path = current_dir / file.name
            images[file.stem].found_file_path = select_preferred_path(
                cur_path, new_path
            )

    return images


def write_descriptions(
    images, dry_run, overwrite_descriptions, overwrite_originals
) -> int:
    """Write descriptions to files

    - For xmp file type, the xmp file is updated
    - For raw file types, an xmp file is created (asserting that one does not
      exist first)
    - For jpg file types, the jpg file is updated

    - If a desc already exists and matches the new one, it's a noop
    - If a desc already exists and does not match, behavior is determined by
      the overwrite_descriptions option
    - If a desc exists in a raw file that does not have an xmp yet, an xmp
      file will be created and the raw file will remain untouched (including
      its existing desc)

    Note that in the rare, latter case, you will likely end up with metadata in
    the raw file that is "masked" by the xmp file. Even if an xmp has no
    description field, applications that are xmp-first will display nothing for
    the caption/description fields, despite the raw file itself having one.
    """
    with exiftool.ExifToolHelper() as et:
        files_updated = 0
        for image in images.values():
            et_params = []  # Build a parameter list as we check conditions
            if overwrite_originals:
                et_params.append("-overwrite_original")
            target_file = image.found_file_path
            if target_file is None:
                continue

            # Create xmp if target_file is a raw type
            if target_file.suffix.lower() in RAW_TYPES:
                # Check one last time that there isn't an xmp file
                assert not (
                    target_file.with_suffix(".xmp").is_file()
                    or target_file.with_suffix(".XMP").is_file()
                ), (
                    f"Target file {target_file.name} has XMP that was "
                    "missed during file scan."
                )
                # Create an xmp file, copying over the raw file's metadata
                # NOTE: -tagsFromFile is implied with -o if an input file is
                # provided.
                # NOTE: "Combining the -overwrite_originals option with -o
                # causes the original source file to be erased after the output
                # file is successfully written." However, this does NOT mean it
                # will delete the raw file after creating the XMP.
                et_params.extend(["-out", target_file.with_suffix(".XMP")])
                click.secho(
                    f"Creating XMP file for {image.found_file_path.name}",
                    fg="yellow",
                )

            # Check for existing description values
            # This is kind of ugly, but we need some heuristics since we don't
            # know the exact dictionary key that will be returned for
            # "Description"
            if target_file.is_file():
                tags_result = et.get_tags(target_file, "description")
                del tags_result[0]["SourceFile"]
                existing_desc = tags_result[0]
                # Empty description fields are empty strings. No description
                # fields is dict.values([]). Both are covered by this
                # conditional.
                if not all(c == "" for c in existing_desc.values()):
                    if list(existing_desc.values())[0] == image.input_desc:
                        click.secho(
                            f"Skipping {image.found_file_path.name} "
                            "- matching description already exists"
                        )
                        continue
                    if not overwrite_descriptions:
                        click.secho(
                            f"Skipping {image.found_file_path.name} "
                            "- a nonmatching description already exists"
                        )
                        continue
                    click.secho(
                        "Overwriting existing description for "
                        f"{image.found_file_path.name}",
                        fg="yellow",
                    )

            # Execute
            if not dry_run:
                try:
                    result = et.set_tags(
                        target_file,
                        {"Description": image.input_desc},
                        params=et_params,
                    )
                    click.secho(f"{result.strip()}")
                    files_updated += 1
                except:
                    click.secho(f"Error writing description for {target_file}")
                    click.secho(f"{et.last_status=}", fg="red")
                    click.secho(f"{et.last_stderr=}", fg="red")
                    raise
        return files_updated


@click.command()
@click.argument("input_descriptions", type=click.File("r"))
@click.option(
    "--search-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd(),
    show_default=True,
    help="Directory to search. The default is cwd.",
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    help=(
        "Find matching files and check for existing description values. "
        "No changes are written."
    ),
)
@click.option(
    "--ignore-jpg",
    is_flag=True,
    help=(
        "Ignore jpg/heic types when searching for files to update. This "
        "allows you to e.g. provide a top level Capture One session folder "
        "and have it ignore any rendered Output files."
    ),
)
@click.option(
    "--max-scan-items",
    # Scanning one item is not very useful, but who am I to judge
    type=click.IntRange(min=1),
    default=30_000,
    show_default=True,
    help=(
        "Abort the matching file search after scanning this many files. This "
        "is a sanity check in case we pass in an excessively large search_dir."
    ),
)
@click.option(
    "--overwrite-descriptions",
    is_flag=True,
    help=(
        "Overwrite existing description values. Without this, files with "
        "existing descriptions are skipped."
    ),
)
@click.option(
    "--overwrite-originals",
    is_flag=True,
    help=(
        'Write changes directly to input files, without creating "_original" '
        "backup files. Exiftool cautions against this. It's safer to check "
        'that everything worked and delete the "_original" files as a '
        "separate step."
    ),
)
def main(
    input_descriptions,
    search_dir,
    dry_run,
    ignore_jpg,
    max_scan_items,
    overwrite_descriptions,
    overwrite_originals,
):
    """Write descriptions to XMP Description metadata field.

    input_descriptions must be tsv formatted with columns
    [filename] | [description string].
    stdin is accepted as `-`.

    \b
    - Files are matched using file stem only - directories and extensions are
      ignored.
    - CaptureOne directories are ignored.
    - Jpeg files can be ignored.

    Descriptions for raw files are written to XMP, creating XMP files as
    needed.
    """
    if dry_run:
        click.secho("\nDRY RUN -- Nothing will be written", fg="yellow")
    if overwrite_originals:
        click.secho(
            (
                "Warning: You've chosen to ovewrite original files without "
                "creating backup copies for manual verification. Are you "
                "sure? [y/n]"
            ),
            nl=False,
            fg="red",
        )
        confirmation = None
        while confirmation not in ("y", "n"):
            confirmation = click.getchar()
        if confirmation == "n":
            overwrite_originals = False
            click.secho("\noverwrite_originals turned off")
        else:
            click.secho("\nRight. Overwriting original files...")

    click.secho("\nProcessing input descriptions...", fg="blue")
    images = process_tsv_input(input_descriptions)
    click.echo(f"{len(images.keys())} descriptions to write")

    click.secho("\nSearching for file paths using filename stem", fg="blue")
    images = find_matching_files(
        search_dir, images, ignore_jpg, max_scan_items
    )
    images_found_count = len(
        [i for i in images.values() if i.found_file_path is not None]
    )
    click.echo(
        f"Found {images_found_count}/{len(images.keys())} files to update"
    )

    click.secho("\nWriting descriptions...", fg="blue")
    files_updated_count = write_descriptions(
        images, dry_run, overwrite_descriptions, overwrite_originals
    )
    click.secho(f"\n{files_updated_count} files updated", fg="blue")


if __name__ == "__main__":
    main()  # pragma: no cover
