# image_metadata_recorder/reporters/structure_reporter.py

"""
Metadata structure analysis and template generation module.

This module provides functionality to analyze the structure of ImageMetadata
objects and generate templates that can be used for validation or documentation.
It focuses on extracting key paths from the `structured_metadata` and
`unprocessed_tags` fields of the canonical schema.

Typical usage:
    >>> # Assuming 'metadata_obj' is a populated ImageMetadata instance
    >>> key_paths = get_all_key_paths_from_metadata(metadata_obj)
    >>> structure_template = generate_structure_template_from_paths(key_paths)
    >>> with open("structure_report.txt", "w") as f:
    >>>     for path in structure_template:
    >>>         f.write(path + "\\n")
"""

from typing import List, Dict, Any, Set, Union, Optional  # Added Optional
import logging

from image_metadata_recorder.workflow.context import (
    WorkflowContext,
)  # Import WorkflowContext

# Module-level logger can be kept for general module info
logger = logging.getLogger(__name__)


def _extract_key_paths_from_data(
    data: Union[Dict[str, Any], List[Any]],
    parent_path: str = "",
    context: Optional[WorkflowContext] = None,
) -> List[str]:
    """
    Recursively extracts all possible key paths from a nested data structure.
    Optionally uses logger from context if provided.
    """
    # This helper is mostly pure, but could log if context is passed, e.g., for very deep recursion warnings.
    # For now, direct context use is minimal here to keep it simple.
    # If context was mandatory: def _extract_key_paths_from_data(data: ..., parent_path: str, context: WorkflowContext)

    paths = []
    if isinstance(data, dict):
        for key, value in data.items():
            current_key_str = str(key).replace(".", "_")
            path = (
                f"{parent_path}.{current_key_str}" if parent_path else current_key_str
            )
            paths.append(path)
            paths.extend(
                _extract_key_paths_from_data(value, path, context)
            )  # Pass context along
    elif isinstance(data, list):
        for i, item in enumerate(data):
            path = f"{parent_path}.{i}"
            paths.extend(
                _extract_key_paths_from_data(item, path, context)
            )  # Pass context along
    return paths


# This is the correct version of get_all_key_paths_from_metadata
def get_all_key_paths_from_metadata(
    metadata: Dict[str, Any], context: WorkflowContext
) -> List[str]:
    """
    Extracts all unique key paths from the `structured_metadata` (root level)
    and `unprocessed_tags` (page level) within a metadata dictionary.

    Args:
        metadata: The metadata dictionary to analyze.

    Returns:
        A sorted list of unique dot-notation key paths.
    """
    all_paths: Set[str] = set()

    # Extract paths from root-level structured_metadata
    if metadata.get("structured_metadata"):
        context.logger.debug("Extracting paths from root structured_metadata.")
        # Pass context to helper, though its direct use there is currently minimal
        paths_from_structured = _extract_key_paths_from_data(
            metadata["structured_metadata"], "structured_metadata", context
        )
        all_paths.update(paths_from_structured)

    # Extract paths from page-level unprocessed_tags
    if metadata.get("pages"):
        for i, page in enumerate(metadata["pages"]):
            if page.get("unprocessed_tags"):
                context.logger.debug(
                    f"Extracting paths from unprocessed_tags for page {i}."
                )
                page_tags_prefix = f"pages.{i}.unprocessed_tags"
                paths_from_page_tags = _extract_key_paths_from_data(
                    page["unprocessed_tags"], page_tags_prefix, context
                )
                all_paths.update(paths_from_page_tags)

    context.logger.info(
        f"Extracted {len(all_paths)} unique key paths from metadata for {context.current_base_filename}."
    )
    return sorted(list(all_paths))


def generate_structure_template_from_paths(
    key_paths: List[str], context: WorkflowContext
) -> List[str]:
    """
    Generates a structural template from a list of key paths, using context for logging.

    This function takes a list of dot-notation key paths and normalizes them by
    replacing numeric list indices with a generic '[]' placeholder. This is useful
    for creating a template that represents the general structure of the metadata,
    abstracting away the number of elements in lists.

    Args:
        key_paths: A list of dot-notation paths, typically from
                   `get_all_key_paths_from_metadata()`.

    Returns:
        A sorted list of unique template paths with numeric indices replaced by '[]'.
    """
    templates: Set[str] = set()
    if not key_paths:
        return []

    for path in key_paths:
        if not path:
            continue  # Skip empty paths if any
        parts = path.split(".")
        # Replace numeric parts (list indices) with '[]'
        template_parts = [part if not part.isdigit() else "[]" for part in parts]
        templates.add(".".join(template_parts))

    context.logger.info(
        f"Generated {len(templates)} unique template paths from {len(key_paths)} raw paths for {context.current_base_filename}."
    )
    return sorted(list(templates))


def create_structure_report_file(
    metadata: Dict[str, Any], context: WorkflowContext
) -> None:
    """
    Analyzes the structure of a metadata dictionary and writes a structure
    template report (list of key paths) to a text file, using WorkflowContext.

    Args:
        metadata: The metadata dictionary to analyze.
        context: The WorkflowContext object for logging and output path generation.
    """
    output_filepath = context.get_output_path("_structure.txt")
    context.logger.info(
        f"Generating structure report for: {metadata.get('source_file', '')} to {output_filepath}"
    )

    raw_key_paths = get_all_key_paths_from_metadata(metadata, context)
    template_paths = generate_structure_template_from_paths(raw_key_paths, context)

    try:
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(f"# Structure Report for: {metadata.get('source_file', '')}\n")
            f.write(
                f"# Processed File: {context.current_base_filename}{context.current_input_filepath.suffix if context.current_input_filepath else ''}\n"
            )
            f.write(f"# Schema Version: {metadata.get('schema_version', 'N/A')}\n\n")

            if not template_paths:
                f.write(
                    "No dynamic key paths found in structured_metadata or unprocessed_tags.\n"
                )
            else:
                f.write(
                    "## Key Path Templates (numeric list indices replaced with '[]'):\n"
                )
                for path in template_paths:
                    f.write(path + "\n")

            # Optionally, include raw key paths for debugging or detailed view
            # f.write("\n\n## Raw Key Paths (includes numeric list indices):\n")
            # for raw_path in raw_key_paths:
            #    f.write(raw_path + "\n")

        context.logger.info(
            f"Successfully wrote structure report to: {output_filepath}"
        )
    except IOError as e:
        context.logger.error(
            f"Failed to write structure report to {output_filepath}: {e}"
        )
        # Decide on error handling: re-raise, or just log. Workflow currently logs errors from reporters.
        # raise # If this should halt processing for this file.
