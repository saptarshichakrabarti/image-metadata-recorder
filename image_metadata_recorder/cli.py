#!/usr/bin/env python3
"""
Command-line interface for the image-metadata-recorder.

This module provides the main entry point for the tool, handling
command-line arguments, discovering files, and orchestrating the
metadata extraction, normalization, and reporting workflow by calling
the `run_for_file` orchestrator.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

# Import the main workflow orchestrator
from image_metadata_recorder.workflow import workflow

# Supported file extensions (case-insensitive for matching)
SUPPORTED_EXTENSIONS = [".tiff", ".tif", ".qptiff", ".czi"]


def setup_logging(log_level_str: str = "INFO") -> None:
    """Configures basic logging for the application."""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )



def find_files(target_path_str: str) -> List[Path]:
    """
    Finds all supported image files in the given path (file or directory).

    Args:
        target_path_str: A path to a single file or a directory.

    Returns:
        A list of Path objects for supported image files.
        Returns an empty list if no supported files are found or path is invalid.
    """
    target_path = Path(target_path_str)
    found_files: List[Path] = []

    if not target_path.exists():
        logging.error(f"Input path does not exist: {target_path_str}")
        return found_files

    if target_path.is_file():
        if target_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            found_files.append(target_path.resolve())
        else:
            logging.warning(
                f"Specified file is not a supported type: {target_path.name}. "
                f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
            )
    elif target_path.is_dir():
        logging.info(f"Scanning directory: {target_path_str} for supported files...")
        for ext in SUPPORTED_EXTENSIONS:
            # Search for both lowercase and uppercase extensions if OS is case-sensitive
            found_files.extend(target_path.glob(f"*{ext}"))
            if ext.lower() != ext.upper():  # e.g. for .tif vs .TIF
                found_files.extend(target_path.glob(f"*{ext.upper()}"))

        # Resolve paths and filter unique files in case of case-insensitive globbing on some systems
        # or duplicate patterns (e.g. .tif and .tiff potentially matching same files)
        unique_resolved_files = sorted(list(set(f.resolve() for f in found_files)))

        # Final filter by suffix just to be sure glob didn't pick up something odd
        found_files = [
            f for f in unique_resolved_files if f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        logging.info(f"Found {len(found_files)} supported files in {target_path_str}.")
    else:
        logging.error(f"Input path is not a file or directory: {target_path_str}")

    return found_files


def main() -> None:
    """
    Main entry point for the image-metadata-recorder CLI.
    Parses arguments, sets up logging, finds files, and calls the workflow orchestrator.
    """
    parser = argparse.ArgumentParser(
        description="Extracts, normalizes, and reports metadata from microscopy image files."
    )
    parser.add_argument(
        "input_path",
        type=str,
        help="Path to an image file or a directory containing image files.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="metadata_output",
        help="Directory to save output files (default: 'metadata_output' in current dir).",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO).",
    )

    args = parser.parse_args()

    setup_logging(args.log_level)

    files_to_process = find_files(args.input_path)

    if not files_to_process:
        logging.info(
            f"No supported image files found at path: {args.input_path}. Exiting."
        )
        sys.exit(0)  # Not necessarily an error if path was valid but empty of targets

    output_directory = Path(args.output_dir)
    try:
        output_directory.mkdir(parents=True, exist_ok=True)
        logging.info(f"Output will be saved to: {output_directory.resolve()}")
    except OSError as e:
        logging.error(f"Could not create output directory {output_directory}: {e}")
        sys.exit(1)

    logging.info(f"Found {len(files_to_process)} image file(s) to process.")

    success_count = 0
    failure_count = 0

    for image_file_path in files_to_process:
        logging.info(f"--- Starting processing for: {image_file_path.name} ---")
        try:
            # Ensure file path is absolute string for run_for_file
            workflow.run_for_file(
                filepath_str=str(image_file_path.resolve()),
                output_dir_str=str(output_directory.resolve()),
            )
            logging.info(f"--- Finished processing for: {image_file_path.name} ---")
            success_count += 1
        except Exception as e:
            logging.error(
                f"!!! Critical error during workflow for {image_file_path.name}: {e} !!!",
                exc_info=True,  # Print stack trace for unexpected errors at this level
            )
            failure_count += 1
            # Optionally, create a specific error file for this top-level failure
            error_file = output_directory / f"{image_file_path.stem}_WORKFLOW_ERROR.txt"
            with open(error_file, "w") as f_err:
                f_err.write(
                    f"A critical error occurred processing {image_file_path.name}:\n{e}\n"
                )
                f_err.write("Check logs for more details.")

    logging.info("\n===================================================")
    logging.info("              Batch Processing Complete!             ")
    logging.info(f"  Successfully processed: {success_count} file(s)")
    logging.info(f"  Failed to process:    {failure_count} file(s)")
    logging.info("===================================================")

    if failure_count > 0:
        sys.exit(1)  # Indicate that some operations failed


if __name__ == "__main__":
    main()
