from pathlib import Path

from click.testing import CliRunner
import pytest
from write_description_metadata import write_description_metadata
from write_description_metadata import Image, main


# NOTE: This test module contains custom marker(s) that are registered
# in pyproject.toml. Be sure to keep things in sync.


@pytest.fixture
def tsv_infile(tmp_path):
    """Create an input file argument for the script

    This isn't actually processed, but rather processing is simulated in
    the monkey patched function below.
    """
    tsv = tmp_path / "input.tsv"
    tsv.write_text("IMG_0001.JPG\tTest description\n")
    return tsv


@pytest.fixture(autouse=True)
def stub_functions(monkeypatch, request):
    """Override the core script functions so we can test the CLI
    interface in isolation
    """

    def sim_process_tsv_input(fh):
        """Return exactly one sample image"""
        return {
            "IMG_0001": Image(
                line_no=1,
                input_file_path=Path("IMG_0001.JPG"),
                input_desc="Test description",
            ),
        }

    monkeypatch.setattr(
        write_description_metadata, "process_tsv_input", sim_process_tsv_input
    )

    if not request.node.get_closest_marker("orig_find_matching_files"):

        def sim_find_matching_files(
            search_dir, images, ignore_jpg, max_scan_items
        ):
            """Return a match for the sample image"""
            images["IMG_0001"].found_file_path = (
                search_dir / images["IMG_0001"].input_file_path.name
            )
            return images

        monkeypatch.setattr(
            write_description_metadata,
            "find_matching_files",
            sim_find_matching_files,
        )

    def sim_write_descriptions(
        images, dry_run, overwrite_descriptions, overwrite_originals
    ):
        """Return a files-updated count as if metadata was written"""
        return len(images)

    monkeypatch.setattr(
        write_description_metadata,
        "write_descriptions",
        sim_write_descriptions,
    )


@pytest.mark.parametrize("dry_run_flag", ["-n", "--dry-run"])
def test_dry_run_and_basic_flow(dry_run_flag, tmp_path, tsv_infile):
    """Basic usage in dry run mode"""
    runner = CliRunner()
    # Cast input Path to str to test Click converting it back to a Path
    result = runner.invoke(main, [dry_run_flag, str(tsv_infile)])
    assert result.exit_code == 0
    output = result.output
    assert "DRY RUN -- Nothing will be written" in output
    assert "Processing input descriptions..." in output
    assert "1 descriptions to write" in output
    assert "Searching for file paths using filename stem" in output
    assert "Found 1/1 files to update" in output
    assert "Writing descriptions..." in output
    assert "1 files updated" in output


def test_search_dir_is_used(tmp_path, monkeypatch, tsv_infile):
    """Confirm that search_dir is respected"""

    search_dir = tmp_path / "test-search-dir"
    search_dir.mkdir()

    # Override find_matching_files function again so we can confirm the CLI is
    # using our search_dir
    # Use a mutable data type so we're not creating another search_dir_used
    # inside the function
    params_passed = {}
    # Get the current (already monkey-patched) find_matching_files function to
    # override
    current_find_matching = write_description_metadata.find_matching_files

    def sim_find_matching_files_capture_search_dir(
        search_dir, images, ignore_jpg, max_scan_items
    ):
        params_passed["dir"] = search_dir
        return current_find_matching(
            search_dir, images, ignore_jpg, max_scan_items
        )

    monkeypatch.setattr(
        write_description_metadata,
        "find_matching_files",
        sim_find_matching_files_capture_search_dir,
    )

    runner = CliRunner()
    result = runner.invoke(
        main, ["--search-dir", str(search_dir), str(tsv_infile)]
    )
    assert result.exit_code == 0
    assert params_passed["dir"] == search_dir


def test_invalid_search_dir(tmp_path, tsv_infile):
    """Confirm a nonexistant search_dir is caught by Click"""
    bad_search_dir = tmp_path / "dir_not_created"
    # bad_search_dir.mkdir()
    runner = CliRunner()
    result = runner.invoke(
        main, ["--search-dir", str(bad_search_dir), str(tsv_infile)]
    )
    assert result.exit_code == 2, (
        result.output
    )  # print output if assertion fails


@pytest.mark.orig_find_matching_files
def test_ignore_jpg(tmp_path, monkeypatch, tsv_infile):
    """Confirm ignore_jpg is respected"""
    # Without ignore_jpg, the script would abort on this file set
    Path(tmp_path / "IMG_0001.XMP").touch()
    Path(tmp_path / "IMG_0001.JPG").touch()

    # Override find_matching_files function so we can confirm the CLI is
    # passing the correct argument
    params_passed = {}
    # Avoid infinite recursion by capturing reference to orig function
    orig_find = write_description_metadata.find_matching_files

    def sim_find_matching_files_with_ignore_jpg(
        search_dir, images, ignore_jpg, max_scan_items
    ):
        params_passed["ignore_jpg"] = ignore_jpg
        return orig_find(search_dir, images, ignore_jpg, max_scan_items)

    monkeypatch.setattr(
        write_description_metadata,
        "find_matching_files",
        sim_find_matching_files_with_ignore_jpg,
    )

    runner = CliRunner()
    result = runner.invoke(
        main, ["--search-dir", str(tmp_path), "--ignore-jpg", str(tsv_infile)]
    )
    assert result.exit_code == 0
    assert "Searching for file paths using filename stem" in result.output


@pytest.mark.orig_find_matching_files
def test_max_scan_items(tmp_path, monkeypatch, tsv_infile):
    """Confirm max_scan_items is respected"""
    Path(tmp_path / "IMG_0001.JPG").touch()
    Path(tmp_path / "file2.txt").touch()
    Path(tmp_path / "file3.txt").touch()
    Path(tmp_path / "file4.txt").touch()
    Path(tmp_path / "file5.txt").touch()
    Path(tmp_path / "file6.txt").touch()

    # Override find_matching_files function so we can confirm the CLI is
    # passing the correct argument
    params_passed = {}
    # Avoid infinite recursion by capturing reference to orig function
    orig_find = write_description_metadata.find_matching_files

    def sim_find_matching_files_with_max_scan_items(
        search_dir, images, ignore_jpg, max_scan_items
    ):
        params_passed["max_scan_items"] = max_scan_items
        return orig_find(search_dir, images, ignore_jpg, max_scan_items)

    monkeypatch.setattr(
        write_description_metadata,
        "find_matching_files",
        sim_find_matching_files_with_max_scan_items,
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--search-dir",
            str(tmp_path),
            "--max-scan-items",
            "3",
            str(tsv_infile),
        ],
    )
    assert result.exit_code == 1
    assert "Aborted after scanning 3 files." in result.output


def test_overwrite_descriptions(monkeypatch, tsv_infile):
    """Confirm overwrite_descriptions is respected"""
    params_passed = {}
    # Override the monkey-patched write_descriptions function to capture
    # parameter passed
    current_write_desc = write_description_metadata.write_descriptions

    def sim_write_descriptions_overwrite_desc(
        images, dry_run, overwrite_descriptions, overwrite_originals
    ):
        params_passed["overwrite_desc"] = overwrite_descriptions
        return current_write_desc(
            images, dry_run, overwrite_descriptions, overwrite_originals
        )

    monkeypatch.setattr(
        write_description_metadata,
        "write_descriptions",
        sim_write_descriptions_overwrite_desc,
    )

    runner = CliRunner()
    result = runner.invoke(main, ["--overwrite-descriptions", str(tsv_infile)])
    assert params_passed["overwrite_desc"] is True
    assert result.exit_code == 0


@pytest.mark.parametrize("overwrite_orig_confirmation", ["y", "n"])
def test_overwrite_originals(
    monkeypatch, tsv_infile, overwrite_orig_confirmation
):
    """Confirm that overwrite_originals prompts for confirmation, and is
    respected
    """
    params_passed = {}
    # Override the monkey-patched write_descriptions function to capture
    # parameter passed
    current_write_desc = write_description_metadata.write_descriptions

    def sim_write_descriptions_overwrite_orig(
        images, dry_run, overwrite_descriptions, overwrite_originals
    ):
        params_passed["overwrite_orig"] = overwrite_originals
        return current_write_desc(
            images, dry_run, overwrite_descriptions, overwrite_originals
        )

    monkeypatch.setattr(
        write_description_metadata,
        "write_descriptions",
        sim_write_descriptions_overwrite_orig,
    )

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--overwrite-originals", str(tsv_infile)],
        input=overwrite_orig_confirmation,
    )
    assert result.exit_code == 0
    # I assume this checks for an exception raised within the Click framework?
    assert not result.exception
    assert "Warning: You've chosen to ovewrite original files" in result.output
    if overwrite_orig_confirmation == "y":
        assert params_passed["overwrite_orig"] is True
        assert "Right. Overwriting original files..." in result.output
    else:
        assert params_passed["overwrite_orig"] is False
        assert "overwrite_originals turned off" in result.output
