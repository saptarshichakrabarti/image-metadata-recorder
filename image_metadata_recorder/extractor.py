# metadata_workflow/extractor.py

"""Metadata extraction module for biomedical image files.

This module provides functionality to extract metadata from various biomedical image formats,
including TIFF, QPTIFF, and CZI files. It handles both standard metadata fields and
format-specific metadata structures.

Typical usage:
    >>> metadata = extract_metadata_from_tiff("path/to/image.tiff")
    >>> czi_metadata = extract_metadata_from_czi("path/to/image.czi")
"""

from typing import Dict, Any, Optional
from xml.etree import ElementTree
from tifffile import TiffFile
from aicspylibczi import CziFile
import xmltodict

def extract_metadata_from_tiff(tiff_file_path: str) -> Dict[str, Any]:
    """Extract rich metadata from a single TIFF/QPTIFF file.

    This function extracts all available metadata from a TIFF or QPTIFF file, including:
    - OME metadata (if present)
    - ImageJ metadata (if present)
    - Page-specific metadata and tags
    - XML descriptions and parsed channel names

    Args:
        tiff_file_path: Path to the TIFF/QPTIFF file to process.

    Returns:
        A dictionary containing the extracted metadata with the following structure:
        {
            "source_file": str,
            "ome_metadata": Optional[str],
            "imagej_metadata": Optional[Dict],
            "pages": List[Dict],
            "error": Optional[str]
        }

    Raises:
        FileNotFoundError: If the specified file does not exist.
        PermissionError: If the file cannot be accessed.
    """
    file_metadata = {"source_file": tiff_file_path, "pages": []}
    try:
        with TiffFile(tiff_file_path) as tif:
            if tif.ome_metadata:
                file_metadata["ome_metadata"] = tif.ome_metadata
            if tif.imagej_metadata:
                file_metadata["imagej_metadata"] = tif.imagej_metadata

            for i, page in enumerate(tif.series[0].pages):
                page_info = {
                    "page_index": i,
                    "description_xml": page.description,
                    "parsed_name": None,
                    "tags": {}
                }
                if page.description:
                    try:
                        root = ElementTree.fromstring(page.description)
                        name_element = root.find('.//Name')
                        if name_element is not None:
                            page_info["parsed_name"] = name_element.text
                    except ElementTree.ParseError:
                        page_info["parsed_name"] = "XML_PARSE_ERROR"

                for tag in page.tags.values():
                    page_info["tags"][tag.name] = str(tag.value)

                file_metadata["pages"].append(page_info)
    except Exception as e:
        print(f"  [ERROR] Could not extract from {tiff_file_path}. Reason: {e}")
        file_metadata["error"] = str(e)

    return file_metadata

def extract_metadata_from_czi(czi_path: str) -> Dict[str, Any]:
    """Extract metadata from a CZI (Carl Zeiss Image) file.

    This function extracts the complete XML metadata from a CZI file and converts it
    to a Python dictionary. The metadata includes information about:
    - Image dimensions and properties
    - Channel information
    - Acquisition parameters
    - Instrument settings
    - Custom metadata

    Args:
        czi_path: Path to the CZI file to process.

    Returns:
        A dictionary containing the parsed CZI metadata with the following structure:
        {
            "source_file": str,
            "metadata": Dict[str, Any],
            "error": Optional[str]
        }

    Raises:
        FileNotFoundError: If the specified file does not exist.
        PermissionError: If the file cannot be accessed.
        ValueError: If the file is not a valid CZI file.
    """
    try:
        czi = CziFile(czi_path)
        xml_string = ElementTree.tostring(czi.meta, encoding='unicode')
        metadata_dict = xmltodict.parse(xml_string, process_namespaces=True)
        metadata_dict['source_file'] = czi_path
        return metadata_dict
    except Exception as e:
        print(f"  [ERROR] Could not extract from {czi_path}. Reason: {e}")
        return {"source_file": czi_path, "error": str(e)}