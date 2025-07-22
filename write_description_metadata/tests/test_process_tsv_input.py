from pathlib import Path
import pytest
from write_description_metadata import Image, process_tsv_input


def test_valid_input_single_line():
    """Ensure valid input produces a correct Image instance"""
    input = ["IMG_0001.ARW\tDescription"]
    images = process_tsv_input(input)
    assert isinstance(images, dict)
    assert set(images) == {"IMG_0001"}
    img = images["IMG_0001"]
    assert isinstance(img, Image)
    assert img.line_no == 1
    assert img.input_file_path == Path("IMG_0001.ARW")
    assert img.input_desc == "Description"
    assert img.found_file_path is None


def test_input_blank_lines():
    """Ensure we're skipping blank (and whitespace) lines"""
    input = [
        "",
        "IMG_0001.ARW\tDescription",
        "",
    ]
    images = process_tsv_input(input)
    assert set(images) == {"IMG_0001"}
    img = images["IMG_0001"]
    assert img.input_desc == "Description"
    assert img.line_no == 2


def test_input_missing_tabs():
    """Abort on no tabs (one column)"""
    input = ["IMG_0001.ARW Description without tab"]
    with pytest.raises(ValueError):
        process_tsv_input(input)


def test_input_extra_fields():
    """Abort on more than 2 columns (ambiguous)"""
    input = ["IMG_0001.ARW\tDescription\tExtra column"]
    with pytest.raises(ValueError):
        process_tsv_input(input)


def test_input_abort_on_duplicate_file_stems():
    """Abort on duplicate (ambiguous) file stems"""
    input = [
        "IMG_0001.ARW\tDescription for ARW",
        "IMG_0001.JPG\tDescription for JPG",
    ]
    with pytest.raises(SystemExit) as exception:
        process_tsv_input(input)
    assert exception.value.code == 1


def test_input_list_all_duplicate_file_stems(capsys):
    """List all instances of duplicate file stems"""
    input = [
        "IMG_0001.ARW\tDescription for image 1",
        "IMG_0002.JPG\tDescription for image 2",
        "IMG_0003.JPG\tDescription for image 3",
        "IMG_0001.JPG\tDescription for image 1, a duplicate",
        "IMG_0002.ARW\tDescription for image 2, a duplicate",
        "IMG_0002.XMP\tDescription for image 2, another duplicate",
    ]
    with pytest.raises(SystemExit):
        process_tsv_input(input)
    output = capsys.readouterr()
    assert "Duplicate file stems found" in output.err
    assert "1: IMG_0001" in output.err
    assert "4: IMG_0001" in output.err
    assert "2: IMG_0002" in output.err
    assert "5: IMG_0002" in output.err
    assert "6: IMG_0002" in output.err
