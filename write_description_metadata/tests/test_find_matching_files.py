from pathlib import Path
import pytest
from write_description_metadata import (
    Image,
    find_matching_files,
)


@pytest.fixture
def images_template():
    return {
        "IMG_0001": Image(
            line_no=1,
            input_file_path=Path("IMG_0001.ARW"),
            input_desc="Description for 01 arw",
        ),
        "IMG_0002": Image(
            line_no=2,
            input_file_path=Path("IMG_0002.JPG"),
            input_desc="Description for 02 jpg",
        ),
        "IMG_0003": Image(
            line_no=1,
            input_file_path=Path("IMG_0003.HEIC"),
            input_desc="Description for 03 heic",
        ),
    }


def test_standard_matching(images_template, tmp_path):
    """Test matching using a standard file tree similar to a Capture One
    session
    """
    search_dir = tmp_path / "photos"
    search_dir.mkdir()
    (search_dir / "Selects").mkdir()
    (search_dir / "Selects" / "CaptureOne").mkdir()
    (search_dir / "Selects" / "CaptureOne" / "proxy_IMG_0001.JPG").write_text(
        ""
    )
    (search_dir / "Selects" / "CaptureOne" / "proxy_IMG_0002.JPG").write_text(
        ""
    )
    (search_dir / "Selects" / "IMG_0001.ARW").write_text("")
    (search_dir / "Selects" / "IMG_0001.XMP").write_text("")
    (search_dir / "Selects" / "IMG_0002.JPG").write_text("")
    (search_dir / "title-image-IMG_0001.JPG").write_text("")
    images = find_matching_files(
        search_dir=search_dir,
        images=images_template,
        ignore_jpg=False,
        max_scan_items=100,
    )
    assert images["IMG_0001"].found_file_path.suffix.lower() == ".xmp"
    assert images["IMG_0002"].found_file_path.suffix.lower() == ".jpg"


def test_max_scan_items(images_template, tmp_path, capsys):
    """Ensure we stop scanning after max_scan_items"""
    max_scan_items = 4
    search_dir = tmp_path / "photos"
    (tmp_path / "photos").mkdir()
    for i in range(1, 6):
        (search_dir / f"file{i}.JPG").write_text("")
    with pytest.raises(SystemExit) as exception:
        find_matching_files(
            search_dir=search_dir,
            images=images_template,
            ignore_jpg=False,
            max_scan_items=max_scan_items,
        )
    assert exception.value.code == 1
    output = capsys.readouterr()
    assert f"Aborted after scanning {max_scan_items} files." in output.err


def test_skip_captureone_dirs(images_template, tmp_path):
    """CaptureOne directories should be skipped"""
    search_dir = tmp_path / "photos"
    search_dir.mkdir()
    (search_dir / "CaptureOne").mkdir()
    (search_dir / "IMG_0001.ARW").write_text("")
    (search_dir / "CaptureOne" / "IMG_0001.ARW").write_text("")
    (search_dir / "CaptureOne" / "IMG_0002.JPG").write_text("")
    images = find_matching_files(
        search_dir=search_dir,
        images=images_template,
        ignore_jpg=False,
        max_scan_items=100,
    )
    assert images["IMG_0001"].found_file_path == search_dir / "IMG_0001.ARW"
    assert images["IMG_0002"].found_file_path is None


def test_file_type_filter(images_template, tmp_path):
    """Ensure all returned files are among the available types"""
    search_dir = tmp_path / "photos"
    search_dir.mkdir()
    (search_dir / "IMG_0001.txt").write_text("")
    images = find_matching_files(
        search_dir=search_dir,
        images=images_template,
        ignore_jpg=False,
        max_scan_items=100,
    )
    assert images["IMG_0001"].found_file_path is None


def test_ignore_jpgs(images_template, tmp_path):
    """Ensure jpg types are ignored when the option is set"""
    search_dir = tmp_path / "photos"
    search_dir.mkdir()
    (search_dir / "IMG_0002.JPG").write_text("")
    images = find_matching_files(
        search_dir=search_dir,
        images=images_template,
        ignore_jpg=True,
        max_scan_items=100,
    )
    assert images["IMG_0002"].found_file_path is None


def test_return_variable_structure(images_template, tmp_path):
    """The returned images variable must be the same except for any
    found_file_path attributes
    """
    search_dir = tmp_path / "photos"
    search_dir.mkdir()
    file_to_find = search_dir / "IMG_0001.XMP"
    file_to_find.write_text("")
    images_original = images_template
    images_mutated = find_matching_files(
        search_dir=search_dir,
        images=images_template,
        ignore_jpg=False,
        max_scan_items=100,
    )
    assert images_mutated is images_original
    for stem, mutated_image in images_mutated.items():
        original = images_original[stem]
        assert mutated_image.line_no == original.line_no
        assert mutated_image.input_file_path == original.input_file_path
        assert mutated_image.input_desc == original.input_desc
        if stem == "IMG_0001":
            assert mutated_image.found_file_path == file_to_find
        else:
            assert mutated_image.found_file_path is None
 