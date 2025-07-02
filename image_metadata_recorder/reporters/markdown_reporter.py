# metadata_workflow/reporter.py

"""Report generation module for metadata analysis.

This module provides functionality to generate human-readable reports from
normalized ImageMetadata objects. It supports structured reporting of image
properties, channel information, and other metadata fields.

Typical usage:
    >>> markdown_content = create_markdown_report(image_metadata_object)
    # To create a PDF, you would still need a separate function that takes markdown content
    # or a filepath and converts it, as pypandoc works with files.
"""

from typing import List, Optional
import os
import logging

# from image_metadata_recorder.schemas.metadata_schema import ImageMetadata, PageInfo # Removed
# from image_metadata_recorder.schemas.sourced_value import SourcedValue # Removed
from image_metadata_recorder.workflow.context import WorkflowContext
from typing import Dict, Any, List, Optional  # Ensure List and Optional are imported
import json

# Module-level logger is fine for general info, but operations will use context.logger
logger = logging.getLogger(__name__)


def generate_markdown_content(
    metadata: Dict[str, Any], context: WorkflowContext
) -> str:
    """
    Generates the Markdown content for a report from a processed metadata dictionary.

    Args:
        metadata: A dictionary containing the processed metadata.
        context: The WorkflowContext object.

    Returns:
        A string containing the complete Markdown report.
    """

    # Helper to safely get values and format them for the report
    def format_value(value: Any, default_na: bool = True) -> str:
        if value is None:
            return "N/A" if default_na else ""
        return str(value)

    source_file = metadata.get("sourceFile", "Unknown Source File")

    lines: List[str] = [
        f"# Metadata Report for {os.path.basename(source_file)}",
        f"**Source File:** `{source_file}`",
    ]
    lines.append("\n")

    # General Image Properties (from the first page, if available)
    lines.append("## General Image Properties (from first page if available)")

    pages_data = metadata.get("pages", [])
    first_page: Optional[Dict[str, Any]] = next(iter(pages_data), None)

    if first_page:
        lines.extend(
            [
                "| Property        | Value                                  |",
                "|:----------------|:---------------------------------------|",
                f"| Image Width     | {format_value(first_page.get('imageWidth'))} |",
                f"| Image Length    | {format_value(first_page.get('imageLength'))} |",
                f"| Bits Per Sample | {format_value(first_page.get('bitsPerSample'))} |",
                f"| Date/Time       | {format_value(first_page.get('dateTime'))} |",
            ]
        )
        lines.append("\n")

        lines.append("## Technical Details (from first page if available)")
        lines.extend(
            [
                "| Detail                      | Value                                         |",
                "|:----------------------------|:----------------------------------------------|",
                f"| Software                    | {format_value(first_page.get('software'))} |",
                f"| Compression                 | {format_value(first_page.get('compression'))} |",
                f"| Photometric Interpretation  | {format_value(first_page.get('photometricInterpretation'))} |",
                f"| X Resolution                | {format_value(first_page.get('xResolution'))} |",
                f"| Y Resolution                | {format_value(first_page.get('yResolution'))} |",
                f"| Resolution Unit             | {format_value(first_page.get('resolutionUnit'))} |",
                f"| Sample Format               | {format_value(first_page.get('sampleFormat'))} |",
            ]
        )
        lines.append("\n")

        # Section for other/unprocessed tags from the first page:
        # Iterate over keys not already explicitly handled.
        explicitly_handled_keys = {
            "imageWidth",
            "imageLength",
            "bitsPerSample",
            "dateTime",
            "software",
            "compression",
            "photometricInterpretation",
            "xResolution",
            "yResolution",
            "resolutionUnit",
            "sampleFormat",
            "pageIndex",
            "parsedName",
            "tags",
        }

        other_page_keys = {
            k: v for k, v in first_page.items() if k not in explicitly_handled_keys
        }

        # Display remaining tags if 'tags' dict exists and has content
        current_page_tags = first_page.get("tags")
        if isinstance(current_page_tags, dict) and current_page_tags:
            lines.append("### Remaining Tags from First Page (under 'tags' key):")
            lines.append("| Tag Key (Raw) | Value (Raw) |")
            lines.append("|:--------------|:------------|")
            count = 0
            for key, value in current_page_tags.items():
                if count < 5:
                    lines.append(f"| {key} | {str(value)[:100]} |")
                    count += 1
                else:
                    lines.append(f"| ...and {len(current_page_tags) - count} more | |")
                    break
            lines.append("\n")
        elif (
            isinstance(current_page_tags, dict) and not current_page_tags
        ):  # tags dict is empty
            lines.append("### Remaining Tags from First Page (under 'tags' key):")
            lines.append("| (No remaining tags under 'tags' key) | |")
            lines.append("\n")

        # Display other top-level page keys
        if other_page_keys:
            lines.append("### Other Top-Level Fields from First Page:")
            lines.append("| Field Key     | Value       |")
            lines.append("|:--------------|:------------|")
            count = 0
            for key, value in other_page_keys.items():
                if count < 5:
                    lines.append(f"| {key} | {str(value)[:100]} |")
                    count += 1
                else:
                    lines.append(f"| ...and {len(other_page_keys)-count} more | |")
                    break
            lines.append("\n")
    else:
        lines.append("No page data available to display general properties.")
    lines.append("\n")

    # Structured Metadata (Catch-all from the root of the metadata dictionary)
    lines.append("## Other Root-Level Metadata Blocks")

    known_root_fields_handled_elsewhere = {
        "pages",
        "sourceFile",
        "schemaVersion",
    }

    other_root_data = {
        k: v
        for k, v in metadata.items()
        if k not in known_root_fields_handled_elsewhere
    }

    if other_root_data:
        for key, value_block in other_root_data.items():
            lines.append(f"### {key}")
            try:
                if isinstance(value_block, (dict, list)):
                    value_str = json.dumps(value_block, indent=2, default=str)
                    lines.append(f"```json\n{value_str}\n```")
                else:
                    lines.append(f"```\n{str(value_block)}\n```")
            except Exception as e:
                logger.warning(f"Could not serialize content for root key {key}: {e}")
                lines.append(
                    f"Could not display content for {key} (serialization error)."
                )
            lines.append("\n")
    else:
        lines.append("No other root-level metadata blocks found or handled.")

    return "\n".join(lines)


def create_markdown_report(metadata: Dict[str, Any], context: WorkflowContext) -> None:
    md_content = generate_markdown_content(metadata, context)
    md_report_path = context.get_output_path("_report.md")
    try:
        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        context.logger.info(f"Markdown report saved to: {md_report_path}")
    except IOError as e:
        context.logger.error(
            f"Failed to write Markdown report to {md_report_path}: {e}"
        )
        return