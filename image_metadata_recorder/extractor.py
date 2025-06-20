# metadata_workflow/extractor.py

"""
Metadata extraction module for biomedical image files.

Provides functionality to extract metadata from TIFF/QPTIFF and CZI files,
automatically detecting and parsing embedded XML structures.

Typical usage:
    >>> extract_metadata_from_tiff("file.tiff")
    >>> extract_metadata_from_czi("file.czi")
"""

import json
import logging
import re
from typing import Any, Dict, Optional, Union, List
from xml.etree import ElementTree

import xmltodict
from tifffile import TiffFile, TiffPage
from aicspylibczi import CziFile

# ---------------------- Logging Setup ---------------------- #

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)

# ---------------------- Constants ---------------------- #

COMMON_ENCODINGS = ["utf-16", "utf-8", "latin1"]

# ---------------------- Helper Functions ---------------------- #


def _try_decode(value: bytes) -> Optional[str]:
    """Attempt to decode a byte string using common encodings."""
    for enc in COMMON_ENCODINGS:
        try:
            decoded = value.decode(enc)
            if "<?xml" in decoded:
                return decoded
        except Exception:
            continue
    return None


def _parse_generic_xml(xml_input: Union[str, bytes]) -> Optional[Dict[str, Any]]:
    """Parse XML string or bytes into a dictionary using xmltodict."""
    if isinstance(xml_input, bytes):
        xml_input = _try_decode(xml_input)
    else:
        xml_input = str(xml_input)

    if not xml_input or not xml_input.strip():
        return None

    match = re.search(r"<(?!!--)", xml_input)
    if not match:
        return None

    clean_xml = xml_input[match.start() :]

    def postprocessor(_, key, val):
        if val is None or not isinstance(val, str):
            return key, val
        if val.lower() in {"true", "false"}:
            return key, val.lower() == "true"
        if val.isdigit():
            return key, int(val)
        try:
            return key, float(val)
        except Exception:
            return key, val

    try:
        return xmltodict.parse(
            clean_xml, process_namespaces=True, postprocessor=postprocessor
        )
    except Exception as e:
        logging.warning("Failed to parse XML: %s", e)
        return None


def _find_xml_description_in_tags(page: TiffPage) -> Optional[str]:
    """Find XML content from the description or known XML-style tags."""

    def process_value(val: Any) -> Optional[str]:
        if isinstance(val, bytes):
            return _try_decode(val)
        if isinstance(val, str) and val.strip().startswith("<"):
            return val
        return None

    xml_str = process_value(getattr(page, "description", None))
    if xml_str:
        return xml_str

    for tag in page.tags.values():
        if "description" in tag.name.lower():
            return process_value(tag.value)

    return None


def _parse_perkinelmer_xml(xml_string: str) -> Dict[str, Any]:
    """Parse PerkinElmer-specific XML that may contain embedded JSON."""
    try:
        parsed = xmltodict.parse(xml_string, process_namespaces=True)
        root_key = next(iter(parsed))
        desc_data = parsed[root_key]

        if "ScanProfile" in desc_data and isinstance(desc_data["ScanProfile"], str):
            try:
                desc_data["ScanProfile"] = json.loads(desc_data["ScanProfile"])
            except json.JSONDecodeError as e:
                desc_data["ScanProfile"] = {
                    "error": f"JSON parse error: {e}",
                    "raw_value": desc_data["ScanProfile"],
                }

        return desc_data
    except Exception as e:
        logging.error("Failed to parse PerkinElmer XML: %s", e)
        return {"error": str(e), "raw_value": xml_string}


# ---------------------- TIFF Extractor ---------------------- #


def extract_metadata_from_tiff(tiff_file_path: str) -> Dict[str, Any]:
    """Extract metadata from TIFF or QPTIFF files."""
    metadata: Dict[str, Any] = {"source_file": tiff_file_path, "pages": []}

    try:
        with TiffFile(tiff_file_path) as tif:
            series = tif.series[0] if tif.series else None
            if not series:
                logging.warning("No image series found in file: %s", tiff_file_path)
                return metadata

            top_level_fields = {
                "ome_metadata": getattr(tif, "ome_metadata", None),
                "imagej_metadata": getattr(tif, "imagej_metadata", None),
            }

            for key, value in top_level_fields.items():
                if value:
                    metadata[key] = value
                    structured = _parse_generic_xml(value)
                    if structured:
                        metadata[f"structured_{key}"] = structured

            for i, page in enumerate(series.pages):
                page_info: Dict[str, Any] = {"page_index": i, "tags": {}}

                if not hasattr(page, "tags"):
                    page_info["warning"] = "No tags available (TiffFrame)"
                    metadata["pages"].append(page_info)
                    continue

                xml_str = _find_xml_description_in_tags(page)
                if xml_str:
                    page_info["description_xml"] = xml_str
                    structured = _parse_perkinelmer_xml(xml_str)
                    page_info["structured_description"] = structured
                    if isinstance(structured, dict):
                        page_info["parsed_name"] = structured.get("Name")

                for tag in page.tags.values():
                    raw_val = str(tag.value) if tag.value is not None else ""
                    page_info["tags"][tag.name] = raw_val

                    if not raw_val or not isinstance(raw_val, str):
                        continue

                    parsed = _parse_generic_xml(raw_val)
                    if parsed:
                        safe_key = re.sub(r"[^a-z0-9_]", "_", tag.name.lower())
                        key_name = f"structured_{safe_key}"
                        if key_name not in page_info:
                            page_info[key_name] = parsed

                metadata["pages"].append(page_info)

    except Exception as e:
        logging.error("Failed to extract TIFF metadata from %s: %s", tiff_file_path, e)
        metadata["error"] = str(e)

    return metadata


# ---------------------- CZI Extractor ---------------------- #


def extract_metadata_from_czi(czi_path: str) -> Dict[str, Any]:
    """Extract metadata from Carl Zeiss Image (CZI) files."""
    try:
        czi = CziFile(czi_path)
        xml_string = ElementTree.tostring(czi.meta, encoding="unicode")
        metadata = xmltodict.parse(xml_string, process_namespaces=True)
        metadata["source_file"] = czi_path
        return metadata
    except Exception as e:
        logging.error("Failed to extract CZI metadata from %s: %s", czi_path, e)
        return {"source_file": czi_path, "error": str(e)}
