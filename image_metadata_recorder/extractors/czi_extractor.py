# image_metadata_recorder/extractors/czi_extractor.py

"""
CZI metadata extraction module.
"""

import logging
from typing import Any, Dict
from xml.etree import ElementTree

import xmltodict
from aicspylibczi import CziFile
from image_metadata_recorder.workflow.context import WorkflowContext

# ---------------------- Logging Setup ---------------------- #

# Module-level logger can be kept for general module info
logger = logging.getLogger(__name__)

# ---------------------- CZI Extractor ---------------------- #


def extract(context: WorkflowContext) -> Dict[str, Any]:
    """
    Extract raw metadata from Carl Zeiss Image (CZI) files using a WorkflowContext.

    Args:
        context: The WorkflowContext object containing the filepath and logger.

    Returns:
        A dictionary containing the extracted raw metadata, suitable for schema-less downstream processing.
    """
    if not context.current_input_filepath:
        context.logger.error(
            "CZI Extractor: current_input_filepath not set in context."
        )
        return {"error": "Input filepath not provided in context."}

    czi_file_path_str = str(context.current_input_filepath)
    raw_metadata: Dict[str, Any] = {"source_file_path": czi_file_path_str}

    try:
        # Use context.logger for operational messages
        context.logger.debug(f"Attempting to open CZI file: {czi_file_path_str}")
        czi = CziFile(czi_file_path_str)

        xml_metadata_element = czi.meta
        if xml_metadata_element is None:
            context.logger.warning(
                f"No XML metadata found in CZI file: {czi_file_path_str}"
            )
            raw_metadata["warning"] = "No XML metadata element found by aicspylibczi."
            try:
                raw_metadata["dimensions_summary_from_czi_object"] = str(czi.dims)
                raw_metadata["size_summary_from_czi_object"] = str(czi.size)
                raw_metadata["is_mosaic_from_czi_object"] = czi.is_mosaic
            except Exception as basic_info_e:
                context.logger.warning(
                    f"Could not retrieve basic CZI info for {czi_file_path_str}: {basic_info_e}"
                )
            return raw_metadata

        xml_string = ElementTree.tostring(xml_metadata_element, encoding="unicode")
        raw_metadata["xml_metadata_string"] = xml_string

        # Parse the XML string to a dictionary
        # The postprocessor and xmltodict.parse don't use logging directly here,
        # so they don't need context passed in unless we modify them, which is out of scope.
        # process_namespaces=True helps in correctly parsing namespaced XML like CZI's
        # Might need a custom postprocessor if numbers/booleans are not parsed correctly
        def postprocessor(_, key, val):
            if val is None or not isinstance(val, str):
                return key, val
            if val.lower() in {"true", "false"}:
                return key, val.lower() == "true"
            try:
                if "." in val or "e" in val.lower():  # Heuristic for float
                    return key, float(val)
                elif val.lstrip("-+").isdigit():  # Check if it's an integer
                    return key, int(val)
            except ValueError:
                pass  # Keep as string if conversion fails
            return key, val

        parsed_xml = xmltodict.parse(
            xml_string,
            process_namespaces=True,
            namespaces={
            },
            postprocessor=postprocessor,
        )

        # The root of CZI metadata is often <ImageDocument> or similar.
        # xmltodict will create a dict with this root as the single key.
        # We can simplify this if the root key is predictable or just store as is.
        raw_metadata["structured_metadata"] = parsed_xml

    except FileNotFoundError:
        context.logger.error(f"CZI file not found: {czi_file_path_str}")
        raw_metadata["error"] = f"File not found: {czi_file_path_str}"
    except Exception as e:
        context.logger.error(
            f"Failed to extract CZI metadata from {czi_file_path_str}: {e}",
            exc_info=True,
        )
        raw_metadata["error"] = str(e)

    return raw_metadata
