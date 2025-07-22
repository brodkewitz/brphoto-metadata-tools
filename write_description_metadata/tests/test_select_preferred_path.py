from pathlib import Path
import pytest
from write_description_metadata import (
    RAW_TYPES,
    JPG_TYPES,
    XMP_TYPES,
    TYPE_PRIORITIES,
    select_preferred_path,
)


def test_first_instance_of_stem():
    """None vs any type -> Return the new file"""
    cur_path = None
    raw_path = Path("./Selects/IMG_0001.ARW")
    xmp_path = Path("./Selects/IMG_0001.XMP")
    jpg_path = Path("./Selects/IMG_0001.JPG")
    assert select_preferred_path(cur_path, raw_path) == raw_path
    assert select_preferred_path(cur_path, xmp_path) == xmp_path
    assert select_preferred_path(cur_path, jpg_path) == jpg_path


def test_unsupported_file_type():
    """New path is unsupported type -> Abort"""
    cur_path = None
    new_path = Path("./wrong-type.txt")
    with pytest.raises(ValueError, match="Unavailable file type"):
        select_preferred_path(cur_path, new_path)


def test_duplicates_of_same_type():
    """Duplicates of same type -> Abort on duplicate file stems (ambiguous)"""
    """New path is unsupported type -> Abort"""
    cur_path = Path("./Selects/IMG_0001.JPG")
    new_path = Path("./Selects/IMG_0001.HEIC")
    with pytest.raises(ValueError, match="Comparing two files of same rank"):
        select_preferred_path(cur_path, new_path)


def test_raw_vs_xmp():
    """RAW vs XMP -> new XMP"""
    cur_path = Path("./Selects/IMG_0001.ARW")
    new_path = Path("./Selects/IMG_0001.XMP")
    assert select_preferred_path(cur_path, new_path) == new_path


def test_xmp_vs_raw():
    """XMP vs RAW -> original XMP"""
    cur_path = Path("./Selects/IMG_0001.XMP")
    new_path = Path("./Selects/IMG_0001.ARW")
    assert select_preferred_path(cur_path, new_path) == cur_path


def test_raw_vs_jpg(capsys):
    """RAW vs JPG -> Abort on duplicate file stems (ambiguous)"""
    cur_path = Path("./Selects/IMG_0001.ARW")
    new_path = Path("./Selects/IMG_0001.JPG")
    with pytest.raises(SystemExit) as exception:
        select_preferred_path(cur_path, new_path)
    assert exception.value.code == 1
    output = capsys.readouterr()
    assert "Found both a jpg type and raw/xmp type" in output.err


def test_jpg_vs_raw(capsys):
    """JPG vs RAW -> Abort on duplicate file stems (ambiguous)"""
    cur_path = Path("./Selects/IMG_0001.JPG")
    new_path = Path("./Selects/IMG_0001.ARW")
    with pytest.raises(SystemExit) as exception:
        select_preferred_path(cur_path, new_path)
    assert exception.value.code == 1
    output = capsys.readouterr()
    assert "Found both a jpg type and raw/xmp type" in output.err


def test_xmp_vs_jpg(capsys):
    """XMP vs JPG -> Abort on duplicate file stems (ambiguous)"""
    cur_path = Path("./Selects/IMG_0001.XMP")
    new_path = Path("./Selects/IMG_0001.JPG")
    with pytest.raises(SystemExit) as exception:
        select_preferred_path(cur_path, new_path)
    assert exception.value.code == 1
    output = capsys.readouterr()
    assert "Found both a jpg type and raw/xmp type" in output.err


def test_jpg_vs_xmp(capsys):
    """JPG vs XMP -> Abort on duplicate file stems (ambiguous)"""
    cur_path = Path("./Selects/IMG_0001.JPG")
    new_path = Path("./Selects/IMG_0001.XMP")
    with pytest.raises(SystemExit) as exception:
        select_preferred_path(cur_path, new_path)
    assert exception.value.code == 1
    output = capsys.readouterr()
    assert "Found both a jpg type and raw/xmp type" in output.err
