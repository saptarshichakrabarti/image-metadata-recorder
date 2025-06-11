#!/usr/bin/env python3
"""Command-line interface for the metadata workflow tool.

This module provides the main entry point for the metadata workflow tool,
handling command-line arguments, file discovery, and orchestrating the
metadata extraction, analysis, and reporting workflow.

Typical usage:
    $ metadata-workflow
    $ metadata-workflow --skip-pdf
"""

import os
import json
import glob
import sys
import shutil
import argparse
from typing import List, Optional

# Import functions from our package
from image_metadata_recorder.extractor import extract_metadata_from_tiff, extract_metadata_from_czi
from image_metadata_recorder.analyzer import get_key_paths, generate_structure_template
from image_metadata_recorder.reporter import create_markdown_report, create_pdf_report

def check_dependencies() -> bool:
    """Check for required libraries and external tools.

    Verifies that all required Python packages are installed and that
    optional tools (like pandoc) are available if needed.

    Returns:
        bool: True if pandoc is available, False otherwise.

    Raises:
        SystemExit: If any required dependencies are missing.
    """
    print("--- Performing pre-flight dependency checks... ---")
    try:
        import tifffile
        import aicspylibczi
        import xmltodict
    except ImportError as e:
        print(
            f"Error: A required Python library is missing: {e.name}",
            file=sys.stderr
        )
        print(
            "Please update dependencies from pyproject.toml / requirements.txt",
            file=sys.stderr
        )
        sys.exit(1)

    has_pandoc = False
    try:
        import pypandoc
        if shutil.which("pandoc") is not None:
            has_pandoc = True
    except ImportError:
        pass  # pypandoc is optional

    print("Dependencies checked.")
    return has_pandoc

def find_supported_files() -> List[str]:
    """Find all supported image files in the current directory.

    Returns:
        A list of file paths for supported image formats (.tiff, .qptiff, .czi).
    """
    return (
        glob.glob("*.qptiff") +
        glob.glob("*.tiff") +
        glob.glob("*.czi")
    )

def process_file(
    image_file: str,
    skip_pdf: bool,
    has_pandoc: bool
) -> None:
    """Process a single image file through the metadata workflow.

    This function handles the complete workflow for a single file:
    1. Metadata extraction
    2. Analysis and template generation
    3. Report generation (Markdown and optionally PDF)

    Args:
        image_file: Path to the image file to process.
        skip_pdf: Whether to skip PDF report generation.
        has_pandoc: Whether pandoc is available for PDF generation.
    """
    print(f"\n--- Processing: {image_file} ---")
    base_name = os.path.splitext(image_file)[0]
    metadata_dict = None
    is_tiff = False

    # Extract metadata based on file type
    if image_file.lower().endswith(('.tiff', '.qptiff')):
        is_tiff = True
        metadata_dict = extract_metadata_from_tiff(image_file)
        with open(f"{base_name}_metadata.json", 'w') as f:
            json.dump(metadata_dict, f, indent=4)
        print(f"  -> Saved TIFF metadata to '{base_name}_metadata.json'")

    elif image_file.lower().endswith('.czi'):
        metadata_dict = extract_metadata_from_czi(image_file)
        with open(f"{base_name}_full_metadata.json", 'w') as f:
            json.dump(metadata_dict, f, indent=2)
        print(f"  -> Saved CZI metadata to '{base_name}_full_metadata.json'")

    # Analyze metadata if extraction was successful
    if metadata_dict:
        key_paths = get_key_paths(metadata_dict)
        with open(f"{base_name}_key_paths.txt", 'w') as f:
            f.write("\n".join(sorted(key_paths)))

        structure_template = generate_structure_template(key_paths)
        with open(f"{base_name}_structure_template.txt", 'w') as f:
            f.write("\n".join(structure_template))
        print(f"  -> Saved analysis files (keys and structure).")

        # Generate reports for TIFF files
        if is_tiff:
            md_content = create_markdown_report(metadata_dict)
            md_filename = f"{base_name}_report.md"
            with open(md_filename, 'w') as f:
                f.write(md_content)
            print(f"  -> Saved Markdown report for TIFF file.")

            if not skip_pdf and has_pandoc:
                create_pdf_report(md_filename, f"{base_name}_report.pdf")
        else:
            print("  -> Reporting for this file type is not yet implemented.")

def main() -> None:
    """Main entry point for the metadata workflow tool.

    This function:
    1. Parses command-line arguments
    2. Checks for required dependencies
    3. Finds supported image files
    4. Processes each file through the workflow
    """
    parser = argparse.ArgumentParser(
        description="A modular workflow for image metadata extraction and analysis."
    )
    parser.add_argument(
        '--skip-pdf',
        action='store_true',
        help="Skip PDF generation for supported formats."
    )
    args = parser.parse_args()

    has_pandoc = check_dependencies()

    # Find and process supported files
    image_files = find_supported_files()
    if not image_files:
        print(
            "No supported image files (.tiff, .qptiff, .czi) "
            "found in the current directory."
        )
        return

    print(f"\nFound {len(image_files)} image files to process.")

    for image_file in image_files:
        process_file(image_file, args.skip_pdf, has_pandoc)

    print("\n==========================")
    print("    Workflow Complete!    ")
    print("==========================")

if __name__ == "__main__":
    main()