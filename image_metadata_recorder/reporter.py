# metadata_workflow/reporter.py

"""Report generation module for metadata analysis.

This module provides functionality to generate human-readable reports from extracted
metadata in both Markdown and PDF formats. It supports structured reporting of image
properties, channel information, and other metadata fields.

Typical usage:
    >>> report = create_markdown_report(metadata_dict)
    >>> create_pdf_report("report.md", "report.pdf")
"""

from typing import Dict, Any, List
import os
import pypandoc

def create_markdown_report(data: Dict[str, Any]) -> str:
    """Generate a Markdown report from metadata dictionary.

    Creates a structured Markdown report containing image properties and channel
    information from the provided metadata dictionary. The report includes:
    - Source file information
    - Image properties (width, length, bits per sample, etc.)
    - Channel information with parsed names
    - Formatted tables for better readability

    Args:
        data: Dictionary containing the metadata to report on. Expected to have
            the following structure:
            {
                "source_file": str,
                "pages": List[Dict[str, Any]]
            }

    Returns:
        A string containing the complete Markdown report.

    Example:
        >>> metadata = {"source_file": "image.tiff", "pages": [...]}
        >>> report = create_markdown_report(metadata)
        >>> print(report)
        # Metadata Report for image.tiff
        ...
    """
    source_file = data.get("source_file", "N/A")
    lines: List[str] = [
        f"# Metadata Report for {os.path.basename(source_file)}",
        f"**Source File:** `{source_file}`\n"
    ]

    lines.append("## Image Properties")
    if data.get("pages"):
        tags = data["pages"][0].get("tags", {})
        lines.extend([
            "| Property | Value |",
            "|:---|:---|",
            f"| Image Width | {tags.get('ImageWidth', 'N/A')} |",
            f"| Image Length | {tags.get('ImageLength', 'N/A')} |",
            f"| Bits Per Sample | {tags.get('BitsPerSample', 'N/A')} |",
            f"| Date/Time | {tags.get('DateTime', 'N/A')} |"
        ])
    else:
        lines.append("No page data found.")
    lines.append("\n")

    lines.append("## Channel Information")
    if data.get("pages"):
        lines.extend([
            "| Page Index | Parsed Name (Channel) |",
            "|:---|:---|"
        ])
        for page in data["pages"]:
            lines.append(
                f"| {page.get('page_index', 'N/A')} | "
                f"{page.get('parsed_name', 'N/A')} |"
            )
    else:
        lines.append("No channel information found.")

    return "\n".join(lines)

def create_pdf_report(md_file_path: str, pdf_file_path: str) -> None:
    """Convert a Markdown report to PDF format.

    Uses pandoc to convert a Markdown report to a PDF file. The PDF will maintain
    the formatting and structure of the Markdown report, including tables and
    headers.

    Args:
        md_file_path: Path to the input Markdown file.
        pdf_file_path: Path where the PDF file should be saved.

    Raises:
        FileNotFoundError: If the input Markdown file doesn't exist.
        RuntimeError: If pandoc conversion fails.
        ImportError: If pypandoc is not installed.

    Note:
        This function requires pandoc to be installed on the system. If pandoc is
        not available, the function will print an error message but will not raise
        an exception.
    """
    try:
        pypandoc.convert_file(md_file_path, 'pdf', outputfile=pdf_file_path)
        print(f"  -> Converted report to PDF: '{os.path.basename(pdf_file_path)}'")
    except Exception as e:
        print(
            f"  [ERROR] Pandoc failed to create PDF. "
            f"Is a LaTeX engine installed? Error: {e}"
        )