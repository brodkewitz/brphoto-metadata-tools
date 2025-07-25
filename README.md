# Metadata Tools

Command line utility scripts for working with photo and video metadata.

These tools require [Exiftool](https://exiftool.org/), Python 3.13+, and [uv](https://docs.astral.sh/uv/).


## Script: Write Description Metadata

[![Tests and Coverage](https://github.com/brodkewitz/brphoto-metadata-tools/actions/workflows/coverage.yml/badge.svg)](https://github.com/brodkewitz/brphoto-metadata-tools/actions/workflows/coverage.yml) ![Coverage percentage](https://raw.githubusercontent.com/brodkewitz/brphoto-metadata-tools/python-coverage-comment-action-data/badge.svg)

Write the given image descriptions (e.g. alt text) to metadata.

### Workflow

I'm including alt text on many of the images in my photography portfolio going forward.

To accomplish this, I render low res jpg's for an LLM to help write descriptions. I ask for the final descriptions in tab-delimited, filename + description format.

This script writes the descriptions to the original images' metadata. This way, the descriptions (1) stay with the files, and (2) can easily be further reviewed and edited alongside the images in a GUI.

I then render high res output files for the website, and Eleventy extracts the alt text from file metadata.

### Cross-Application Metadata Compatibility

I did a bunch of testing across applications to determine which metadata fields are exposed, editable, and preferred. The fields included "description", "caption", "alt text", and "extended description", among others. I tested in:

- Lightroom
- Photo Mechanic
- Capture One
- Exiftool

**tl;dr** If you're trying to write a description that's usable across all four applications, write `-description` or `-xmp:description` explicitly to the xmp, jpeg, or heif file. Don't touch the original raw files using Exiftool.

Note: Lightroom calls this field "Caption".

### Design

This script recognizes various raw formats as well as jpg and heic.

It accepts tsv formatted input with two columns: a filename and a description string.

Entries are matched to files on disk using a recursive search. Matches are made based on *filename stem only*—full paths and file extensions are discarded from the input.

The script is fairly safe:

- Includes a `--dry-run` option to preview the file search without writing any changes. This mode executes everything except the specific step of writing to files.

- Aborts if it encounters a filename more than once. It will not write to more than one file or format for a given image.

- Raw files are never modified. XMP files are prioritized and even created as necessary.

- Uses Exiftool's standard practice of creating `_original` backup files by default.

- Includes a default limit on the number of files scanned to prevent the script from running excessively long.

See `--help` for full list of options.

<!-- 
### About The Code

I have more experience with argparse than Click, and pip than uv, but both have been easy to pick up. uv makes dependency management for my workflows much easier than pip. I'm much more inclined to create "proper" packages now, rather than manually activating virtual environments for some scripts, or globally installing dependencies for others.
 -->

### Unit Tests

This is my first time writing unit tests.

I've written many procedurally structured command line scripts like this with discreetly testable functions, so it was pretty approachable.

Crafting the sample test files probably took almost as long as writing the tests. Writing the tests + sample files took longer than writing the script. Definitely excessive to write 100% coverage for a script like, but it was a good opportunity to learn Pytest.

On that note, Pytest is great! I didn't realize tests could be this easy to write, and dare I say it, fun?!


## Script: Write Apple Photos Video Metadata

Write Apple Photos-compatible video metadata from source files to transcoded copies.

- Creation Date (original capture time)
- Camera Make
- Camera Model
- Lens info, if available
- GPS coordinates, if available

### Workflow

Occasionally I shoot personal videos on my big cameras that I want to trim, transcode, and import into my Apple Photos Library.

This script writes date, camera info, and gps metadata to the transcoded output files in a way that Apple Photos recognizes, as with native iPhone video. Embedding the correct creation date also puts the videos chronologically where they belong in my photo library.

### Usage

This script is basic and rough.

- There's currently no CLI interface
- It assumes a Capture One session based folder structure, with original videos in Selects, and transcoded videos somewhere in Output.
- It assumes output files have my current Apple Compressor preset naming

I edit the script to hardcode the arguments and options that I need, run it, and then reset it in Git.
