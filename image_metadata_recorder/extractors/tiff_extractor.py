# image_metadata_recorder/extractors/tiff_extractor.py

"""
TIFF metadata extraction module.
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Union

import xmltodict
from tifffile import TiffFile, TiffPage
from image_metadata_recorder.workflow.context import WorkflowContext

# ---------------------- Logging Setup ---------------------- #

# Module-level logger is fine, but operations might use context.logger
logger = logging.getLogger(__name__)

# ---------------------- Constants ---------------------- #

COMMON_ENCODINGS = ["utf-16", "utf-8", "latin1"]

# ---------------------- Helper Functions ---------------------- #


def _try_decode(value: bytes) -> Optional[str]:
    """Attempt to decode a byte string using common encodings."""
    for enc in COMMON_ENCODINGS:
        try:
            decoded = value.decode(enc)
            # Be more specific for XML detection if possible
            if "<?xml" in decoded.lower():  # Check for XML declaration
                return decoded
        except UnicodeDecodeError:
            continue
    # Fallback if no XML declaration found but might still be XML-like
    try:
        return value.decode(
            "utf-8", errors="replace"
        )  # Replace errors if not strictly decodable
    except Exception:
        return None


def _parse_generic_xml(xml_input: Union[str, bytes]) -> Optional[Dict[str, Any]]:
    """Parse XML string or bytes into a dictionary using xmltodict."""
    if isinstance(xml_input, bytes):
        xml_input = _try_decode(xml_input)

    if not xml_input or not isinstance(xml_input, str) or not xml_input.strip():
        return None

    # More robust check for actual XML content
    if not xml_input.strip().startswith("<"):
        return None

    # Attempt to find the start of the XML content if prefixed with junk
    match = re.search(r"<(?!!--)", xml_input)
    if not match:
        return None
    clean_xml = xml_input[match.start() :]

    def postprocessor(_, key, val):
        if val is None or not isinstance(val, str):
            return key, val
        if val.lower() in {"true", "false"}:
            return key, val.lower() == "true"
        # Handle potential errors with int/float conversion
        try:
            if "." in val or "e" in val.lower():  # Heuristic for float
                return key, float(val)
            elif val.lstrip(
                "-+"
            ).isdigit():  # Check if it's an integer (positive or negative)
                return key, int(val)
        except ValueError:
            pass  # Keep as string if conversion fails
        return key, val

    try:
        # Disable namespace processing if it causes issues, or handle specific namespaces
        return xmltodict.parse(
            clean_xml,
            process_namespaces=False,  # Changed to False for broader compatibility
            namespaces=None,  # Explicitly no specific namespace mapping
            postprocessor=postprocessor,
        )
    except Exception as e:
        logger.warning(
            "Failed to parse XML: %s. XML content: %s", e, clean_xml[:200]
        )  # Log part of the XML
        return None


def _find_xml_description_in_tags(page: TiffPage) -> Optional[str]:
    """Find XML content from the description or known XML-style tags."""

    def process_value(val: Any) -> Optional[str]:
        if isinstance(val, bytes):
            decoded_val = _try_decode(val)
            # Ensure what's returned is actually XML-like
            if decoded_val and decoded_val.strip().startswith("<"):
                return decoded_val
            return None  # Return None if not XML-like
        if isinstance(val, str) and val.strip().startswith("<"):
            return val
        return None

    # Prioritize ImageDescription tag as it's standard for OME-XML etc.
    if page.tags.get("ImageDescription"):
        xml_str = process_value(page.tags["ImageDescription"].value)
        if xml_str:
            return xml_str

    # Fallback to page.description (less common for primary XML)
    xml_str_desc = process_value(getattr(page, "description", None))
    if xml_str_desc:
        return xml_str_desc

    return None


def _parse_perkinelmer_xml(xml_string: str) -> Dict[str, Any]:
    """Parse PerkinElmer-specific XML that may contain embedded JSON."""
    try:
        # Using generic parser first might be safer
        parsed = _parse_generic_xml(xml_string)
        if not parsed:  # If generic parsing fails, return an error structure
            return {"error": "Failed generic XML parse", "raw_value": xml_string}

        # We need to find ScanProfile
        # This part needs to be robust to different XML structures.
        def find_key(data, target_key):
            if isinstance(data, dict):
                if target_key in data:
                    return data[target_key]
                for k, v in data.items():
                    found = find_key(v, target_key)
                    if found:
                        return found
            elif isinstance(data, list):
                for item in data:
                    found = find_key(item, target_key)
                    if found:
                        return found
            return None

        scan_profile_val = find_key(parsed, "ScanProfile")

        if scan_profile_val and isinstance(scan_profile_val, str):
            try:
                # Attempt to replace ScanProfile in its original location
                # This is tricky without knowing the exact path to ScanProfile
                # For simplicity, let's assume it's at a known location or update a copy
                # This part might need adjustment based on actual PerkinElmer XML structure
                # For now, let's add a new key 'parsed_scan_profile'
                parsed["parsed_scan_profile"] = json.loads(scan_profile_val)
            except json.JSONDecodeError as e:
                # Store error and raw value for ScanProfile specifically
                if "ScanProfile" in parsed:  # if it was a top-level key
                    parsed["ScanProfile"] = {
                        "error": f"JSON parse error: {e}",
                        "raw_value": scan_profile_val,
                    }
                else:  # if found nested, store it separately
                    parsed["parsed_scan_profile_error"] = {
                        "error": f"JSON parse error: {e}",
                        "raw_value": scan_profile_val,
                    }
        return parsed
    except Exception as e:
        logger.error("Failed to parse PerkinElmer XML: %s", e)
        return {"error": str(e), "raw_value": xml_string}


# ---------------------- TIFF Extractor ---------------------- #


def extract(context: WorkflowContext) -> Dict[str, Any]:
    """
    Extract raw metadata from TIFF or QPTIFF files using a WorkflowContext.
    Returns a dictionary of all extracted metadata, suitable for schema-less downstream processing.

    Args:
        context: The WorkflowContext object containing the filepath and logger.

    Returns:
        A dictionary containing the extracted raw metadata.
    """
    if not context.current_input_filepath:
        # This should ideally not happen if context is managed properly by the workflow
        context.logger.error(
            "TIFF Extractor: current_input_filepath not set in context."
        )
        return {"error": "Input filepath not provided in context."}

    tiff_file_path_str = str(context.current_input_filepath)
    # Use context.logger instead of the module-level logger for operational messages
    # Module-level logger can still be used for general module info if needed.

    raw_metadata: Dict[str, Any] = {"source_file_path": tiff_file_path_str, "pages": []}
    top_level_tags = {}

    try:
        with TiffFile(tiff_file_path_str) as tif:
            if tif.ome_metadata:
                top_level_tags["ome_xml_string"] = tif.ome_metadata
                parsed_ome = _parse_generic_xml(
                    tif.ome_metadata
                )  # Uses module logger for XML parsing warnings
                if parsed_ome:
                    top_level_tags["structured_ome_metadata"] = parsed_ome

            if tif.imagej_metadata:
                top_level_tags["imagej_metadata"] = tif.imagej_metadata

            if not tif.series or not tif.series[0].pages:
                context.logger.warning(
                    f"No image series or pages found in file: {tiff_file_path_str}"
                )
                raw_metadata["top_level_tags"] = top_level_tags
                return raw_metadata

            series = tif.series[0]

            for i, page in enumerate(series.pages):
                page_data: Dict[str, Any] = {"page_index_in_series": i, "tags": {}}

                if not hasattr(page, "tags") or not page.tags:
                    page_data["warning"] = (
                        "No TIFF tags available for this page (possibly a TiffFrame)."
                    )
                    raw_metadata["pages"].append(page_data)
                    continue

                xml_str_from_description = _find_xml_description_in_tags(page)
                if xml_str_from_description:
                    page_data["image_description_xml"] = xml_str_from_description
                    if (
                        "PerkinElmer" in xml_str_from_description
                        or "QPTIFF" in tiff_file_path_str.upper()
                    ):
                        # _parse_perkinelmer_xml uses module logger
                        parsed_desc_xml = _parse_perkinelmer_xml(
                            xml_str_from_description
                        )
                    else:
                        # _parse_generic_xml uses module logger
                        parsed_desc_xml = _parse_generic_xml(xml_str_from_description)

                    if parsed_desc_xml:
                        page_data["structured_image_description"] = parsed_desc_xml

                for tag_obj in page.tags.values():
                    tag_name = tag_obj.name
                    tag_value = tag_obj.value

                    if isinstance(tag_value, bytes):
                        decoded_value = _try_decode(tag_value)
                        if decoded_value and decoded_value.strip().startswith("<"):
                            page_data["tags"][tag_name] = decoded_value
                        else:
                            page_data["tags"][tag_name] = repr(tag_value)
                    elif (
                        isinstance(tag_value, (list, tuple))
                        and tag_value
                        and isinstance(tag_value[0], (int, float))
                    ):
                        page_data["tags"][tag_name] = list(tag_value)
                    else:
                        page_data["tags"][tag_name] = tag_value

                raw_metadata["pages"].append(page_data)

            if top_level_tags:
                raw_metadata["top_level_tags"] = top_level_tags

    except FileNotFoundError:
        context.logger.error(f"TIFF file not found: {tiff_file_path_str}")
        raw_metadata["error"] = f"File not found: {tiff_file_path_str}"
    except Exception as e:
        context.logger.error(
            f"Failed to extract TIFF metadata from {tiff_file_path_str}: {e}",
            exc_info=True,
        )
        raw_metadata["error"] = str(e)

    return raw_metadata
