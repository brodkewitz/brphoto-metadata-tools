import hashlib
from pathlib import Path
import shutil

import exiftool
import pytest

from write_description_metadata import (
    Image,
    write_descriptions,
)


# Simulate images dict after finding matching files
# Note that file matching requires the dict keys to be filename stems, but for
# these tests I'm using more intuitive key names
@pytest.fixture
def images_template(tmp_path):
    return {
        "01_xmp_creation_input": Image(
            line_no=1,
            input_file_path=Path("IMG_0001-write_md-raw-without-xmp.JPG"),
            input_desc="write_descriptions function should receive an ARW file and write this description to a newly created XMP file.",
            found_file_path=tmp_path
            / "sample-files"
            / "IMG_0001-write_md-raw-without-xmp.ARW",
        ),
        "02_assertion_error_input": Image(
            line_no=2,
            input_file_path=Path("IMG_0002-write_md-file-scan-missed-xmp.JPG"),
            input_desc="write_descriptions function should receive an ARW file, find its XMP sidecar that was previously missed, and write this description to the XMP file.",
            found_file_path=tmp_path
            / "sample-files"
            / "IMG_0002-write_md-file-scan-missed-xmp.ARW",
        ),
        "03_xmp_no_desc": Image(
            line_no=3,
            input_file_path=Path("IMG_0003-write_md-xmp-no-desc.JPG"),
            input_desc="write_descriptions function should receive an XMP file and write this description to it.",
            found_file_path=tmp_path
            / "sample-files"
            / "IMG_0003-write_md-xmp-no-desc.XMP",
        ),
        "04_jpg_no_desc": Image(
            line_no=4,
            input_file_path=Path("IMG_0004-write_md-jpg-no-desc.JPG"),
            input_desc="write_descriptions function should receive a JPG file and write this description to it.",
            found_file_path=tmp_path
            / "sample-files"
            / "IMG_0004-write_md-jpg-no-desc.JPG",
        ),
        "05_heic_no_desc": Image(
            line_no=5,
            input_file_path=Path("IMG_0005-write_md-heic-no-desc.HEIC"),
            input_desc="write_descriptions function should receive a HEIC file and write this description to it.",
            found_file_path=tmp_path
            / "sample-files"
            / "IMG_0005-write_md-heic-no-desc.HEIC",
        ),
        "06_xmp_existing_eq_desc": Image(
            line_no=6,
            input_file_path=Path("IMG_0006-write_md-xmp-existing-eq-desc.JPG"),
            input_desc="write_descriptions function should receive an XMP file with this exact description already written.",
            found_file_path=tmp_path
            / "sample-files"
            / "IMG_0006-write_md-xmp-existing-eq-desc.XMP",
        ),
        "07_xmp_existing_ne_desc": Image(
            line_no=7,
            input_file_path=Path("IMG_0007-write_md-xmp-existing-ne-desc.JPG"),
            input_desc="write_descriptions function should receive an XMP file with a *different* description than this one already written.",
            found_file_path=tmp_path
            / "sample-files"
            / "IMG_0007-write_md-xmp-existing-ne-desc.XMP",
        ),
        "08_error_file": Image(
            line_no=8,
            input_file_path=Path("IMG_0008-nonexistant-file.JPG"),
            input_desc='This file is "found" but doesn\'t exist, so exiftool will throw an error trying to write to it.',
            found_file_path=tmp_path
            / "sample-files"
            / "IMG_0008-nonexistant-file.XMP",
        ),
        "09_no_matching_file": Image(
            line_no=8,
            input_file_path=Path("IMG_0009-no-matching-file.JPG"),
            input_desc="This entry has no matching file to find, so the entry will be skipped.",
            found_file_path=None,
        ),
    }


# Copy sample files (for all input variations) into tmp_path
@pytest.fixture
def sample_files(tmp_path):
    template_src_dir = Path(__file__).parent / "fixtures" / "sample-files"
    template_instance_dir = tmp_path / "sample-files"
    shutil.copytree(template_src_dir, template_instance_dir)
    return template_instance_dir


def make_snapshot(root: Path):
    """Make a quick snapshot of a directory tree for comparison

    Returns a dict with file paths as keys, and modtime + size tuples as
    values
    """
    snapshot = {}
    for p in root.rglob("*"):
        stat = p.stat()
        rel_path = str(p.relative_to(root))
        snapshot[rel_path] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def get_snapshot_hash(snapshot: dict):
    """Compute a single hash from the given directory tree snapshot for
    comparison
    """
    # Create a hash object
    h = hashlib.sha256()
    for path in sorted(snapshot):
        mtime, size = snapshot[path]
        # Feed it bytes as many times as you need
        h.update(path.encode("utf-8"))
        h.update(str(mtime).encode())
        h.update(str(size).encode())
        # Ask it for the current hex digest at any time
    return h.hexdigest()


def test_raw_input_triggers_xmp_creation(
    images_template, sample_files, capsys
):
    """Confirm raw input file type triggers XMP creation"""
    test_key = "01_xmp_creation_input"
    test_image = {}
    test_image[test_key] = images_template[test_key]
    write_descriptions(
        test_image,
        dry_run=False,
        overwrite_descriptions=False,
        overwrite_originals=False,
    )
    input_filepath = images_template[test_key].found_file_path
    output_filepath = input_filepath.with_suffix(".XMP")
    output = capsys.readouterr()
    assert f"Creating XMP file for {input_filepath.name}" in output.out
    xmp_files_after_writing = [p for p in sample_files.glob("*.XMP")]
    assert output_filepath in xmp_files_after_writing


def test_assert_no_xmp_before_creating_one(images_template, sample_files):
    """Confirm final check before creating an xmp correctly asserts that
    one does not already exist
    """
    test_key = "02_assertion_error_input"
    test_image = {}
    test_image[test_key] = images_template[test_key]
    with pytest.raises(AssertionError):
        write_descriptions(
            test_image,
            dry_run=False,
            overwrite_descriptions=False,
            overwrite_originals=False,
        )


def test_dry_run(images_template, sample_files):
    """Confirm dry run doesn't write any data"""
    test_keys = [
        "01_xmp_creation_input",
        "03_xmp_no_desc",
        "04_jpg_no_desc",
        "05_heic_no_desc",
        "06_xmp_existing_eq_desc",
        "07_xmp_existing_ne_desc",
    ]
    test_images = {k: v for k, v in images_template.items() if k in test_keys}
    snapshot_orig = make_snapshot(sample_files)
    snapshot_orig_hash = get_snapshot_hash(snapshot_orig)
    files_updated_int = write_descriptions(
        test_images,
        dry_run=True,
        overwrite_descriptions=False,
        overwrite_originals=False,
    )
    snapshot_new = make_snapshot(sample_files)
    snapshot_new_hash = get_snapshot_hash(snapshot_new)
    assert files_updated_int == 0
    assert snapshot_new_hash == snapshot_orig_hash


@pytest.mark.parametrize(
    "test_key", ["03_xmp_no_desc", "04_jpg_no_desc", "05_heic_no_desc"]
)
def test_write_to_files_with_no_desc(images_template, sample_files, test_key):
    """Confirm descriptions written to files with no existing value"""
    test_image = {}
    test_image[test_key] = images_template[test_key]
    test_image_filepath = test_image[test_key].found_file_path
    with exiftool.ExifToolHelper() as et:
        # No description before
        tags_result = et.get_tags(test_image_filepath, "description")
        del tags_result[0]["SourceFile"]
        existing_desc = tags_result[0]
        assert all(desc == "" for desc in existing_desc.values())

        # Write description
        write_descriptions(
            test_image,
            dry_run=False,
            overwrite_descriptions=False,
            overwrite_originals=False,
        )

        # Description after
        tags_result = et.get_tags(test_image_filepath, "description")
        assert "XMP:Description" in tags_result[0].keys()
        assert (
            tags_result[0]["XMP:Description"]
            == test_image[test_key].input_desc
        )


def test_always_skip_matching_desc(images_template, sample_files, capsys):
    """Confirm file with existing, matching description value is always
    skipped
    """
    test_key = "06_xmp_existing_eq_desc"
    test_image = {}
    test_image[test_key] = images_template[test_key]
    snapshot_orig = make_snapshot(sample_files)
    snapshot_orig_hash = get_snapshot_hash(snapshot_orig)
    write_descriptions(
        test_image,
        dry_run=False,
        overwrite_descriptions=False,
        overwrite_originals=False,
    )
    # No filesystem changes when overwrite_descriptions=False
    snapshot_new = make_snapshot(sample_files)
    snapshot_new_hash = get_snapshot_hash(snapshot_new)
    assert snapshot_new_hash == snapshot_orig_hash
    write_descriptions(
        test_image,
        dry_run=False,
        overwrite_descriptions=True,
        overwrite_originals=False,
    )
    # No filesystem changes still, when overwrite_descriptions=True
    snapshot_new = make_snapshot(sample_files)
    snapshot_new_hash = get_snapshot_hash(snapshot_new)
    assert snapshot_new_hash == snapshot_orig_hash
    # Notification of skipping file
    output = capsys.readouterr()
    test_image_name = test_image[test_key].found_file_path.name
    assert (
        f"Skipping {test_image_name} - matching description already exists"
    ) in output.out


@pytest.mark.parametrize(
    "test_key,test_overwrite_desc_val",
    [("07_xmp_existing_ne_desc", False), ("07_xmp_existing_ne_desc", True)],
)
def test_nonmatching_desc(
    images_template, sample_files, capsys, test_key, test_overwrite_desc_val
):
    """Confirm file with existing, nonmatching description is handled
    correctly depending on overwrite_descriptions value
    """
    test_image = {}
    test_image[test_key] = images_template[test_key]
    snapshot_orig = make_snapshot(sample_files)
    snapshot_orig_hash = get_snapshot_hash(snapshot_orig)
    write_descriptions(
        test_image,
        dry_run=False,
        overwrite_descriptions=test_overwrite_desc_val,
        overwrite_originals=False,
    )
    snapshot_new = make_snapshot(sample_files)
    snapshot_new_hash = get_snapshot_hash(snapshot_new)
    output = capsys.readouterr()
    test_image_name = test_image[test_key].found_file_path.name
    if not test_overwrite_desc_val:
        # No filesystem changes
        assert snapshot_new_hash == snapshot_orig_hash
        # Notification of skipping file
        assert (
            f"Skipping {test_image_name} - a nonmatching description "
            "already exists"
        ) in output.out
    else:
        # Filesystem updated
        assert snapshot_new_hash != snapshot_orig_hash
        # Notification of overwriting description
        assert (
            f"Overwriting existing description for {test_image_name}"
        ) in output.out


def test_overwrite_originals_no_backup_files(images_template, sample_files):
    """Confirm overwrite_originals writes to original files and does not
    create backup files
    """
    test_key = "03_xmp_no_desc"
    test_image = {}
    test_image[test_key] = images_template[test_key]
    write_descriptions(
        test_image,
        dry_run=False,
        overwrite_descriptions=False,
        overwrite_originals=True,
    )
    backup_files_after_writing = [p for p in sample_files.glob("*_original")]
    assert backup_files_after_writing == []


def test_return_file_count_updated(images_template, sample_files):
    """Confirm function returns integer count of files updated"""
    test_keys = [
        "01_xmp_creation_input",
        "03_xmp_no_desc",
        "04_jpg_no_desc",
        "05_heic_no_desc",
        "06_xmp_existing_eq_desc",
        "07_xmp_existing_ne_desc",
    ]
    test_images = {k: v for k, v in images_template.items() if k in test_keys}
    files_updated_int = write_descriptions(
        test_images,
        dry_run=False,
        overwrite_descriptions=True,
        overwrite_originals=False,
    )
    assert files_updated_int > 0


def test_exiftool_write_error(images_template, capsys):
    """Confirm ExifTool execution errors show output message"""
    test_key = "08_error_file"
    test_image = {}
    test_image[test_key] = images_template[test_key]
    with pytest.raises(exiftool.exceptions.ExifToolExecuteError):
        write_descriptions(
            test_image,
            dry_run=False,
            overwrite_descriptions=False,
            overwrite_originals=False,
        )
    output = capsys.readouterr()
    test_image_path = test_image[test_key].found_file_path
    assert f"Error writing description for {test_image_path}" in output.out


def test_skip_entries_with_no_file_found(images_template, sample_files):
    """Confirm Image objects with no matching files found are skipped"""
    test_key = "09_no_matching_file"
    test_image = {}
    test_image[test_key] = images_template[test_key]
    snapshot_orig = make_snapshot(sample_files)
    snapshot_orig_hash = get_snapshot_hash(snapshot_orig)
    write_descriptions(
        test_image,
        dry_run=False,
        overwrite_descriptions=False,
        overwrite_originals=False,
    )
    snapshot_new = make_snapshot(sample_files)
    snapshot_new_hash = get_snapshot_hash(snapshot_new)
    assert snapshot_new_hash == snapshot_orig_hash
