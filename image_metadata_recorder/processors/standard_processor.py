# image_metadata_recorder/processors/standard_processor.py

import re
from typing import Any, Dict, List, Union
import logging

logger = logging.getLogger(__name__)


# Helper functions from the original standard_normalizer.py
def _to_camel_case(text: str) -> str:
    """Converts snake_case, kebab-case, space-separated, or PascalCase text to camelCase."""
    if not text:
        return ""

    # Normalize separators (hyphen, underscore, space) to space, then split
    s = text.replace("-", " ").replace("_", " ")
    parts = s.split()  # Splits by space and handles multiple spaces

    if not parts:  # Handles cases like "___" or "---" becoming empty list
        return ""

    # If only one part (e.g., "Word", "word", "WORD"), lowercase first letter, rest as is.
    if len(parts) == 1:
        return parts[0][0].lower() + parts[0][1:]

    # Multiple parts: first word's first char lower (rest of word as is),
    # subsequent words capitalized (first char upper, rest of word as is).
    first_word = parts[0][0].lower() + parts[0][1:]
    following_words = "".join(word.capitalize() for word in parts[1:])

    return first_word + following_words


def normalize_recursively(
    data: Union[Dict[str, Any], List[Any], Any],
) -> Union[Dict[str, Any], List[Any], Any]:
    """
    Recursively converts all keys in a dictionary to camelCase and processes nested structures.
    Attempts to coerce string representations of numbers to numeric types.
    """
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            new_key = _to_camel_case(str(key))
            new_dict[new_key] = normalize_recursively(
                value
            )  # Value is processed recursively
        return new_dict
    elif isinstance(data, list):
        return [normalize_recursively(item) for item in data]
    elif isinstance(data, str):
        if re.match(r"^-?\d+$", data):
            try:
                return int(data)
            except ValueError:
                pass
        elif re.match(r"^-?\d*\.\d+$", data) or re.match(r"^-?\d+\.\d*$", data):
            try:
                return float(data)
            except ValueError:
                pass
        return data
    else:
        return data


def process(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cleans and restructures a raw metadata dictionary for schema-less downstream use.
    - Recursively cleans all keys to camelCase and coerces values to appropriate types.
    - Promotes common, high-value tags from any nested 'tags' dictionary to the parent 'page' level for easier access.
    """
    logger.info("Processing raw metadata for key cleaning and field promotion.")

    processed_data = normalize_recursively(raw_data)

    if "pages" in processed_data and isinstance(processed_data.get("pages"), list):
        for page in processed_data["pages"]:
            if (
                not isinstance(page, dict)
                or "tags" not in page
                or not isinstance(page.get("tags"), dict)
            ):
                logger.debug(
                    "Skipping page for promotion: not a dict, or 'tags' key missing/invalid."
                )
                continue

            keys_to_promote = [
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
            ]

            for key in keys_to_promote:
                if key in page["tags"]:
                    page[key] = page["tags"].pop(key)
                    logger.debug("Promoted key '%s' to page level.", key)

            if page.get("tags") == {}:
                page.pop("tags")
                logger.debug(
                    "Removed empty 'tags' dictionary from page level after promotion."
                )

    return processed_data
