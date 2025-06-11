# metadata_workflow/analyzer.py

"""Metadata analysis and structure template generation module.

This module provides functionality to analyze metadata structures and generate
templates that can be used for validation or documentation purposes. It includes
tools for:
- Extracting all possible key paths from nested metadata structures
- Generating structural templates from key paths
- Normalizing metadata structures for comparison

Typical usage:
    >>> paths = get_key_paths(metadata_dict)
    >>> templates = generate_structure_template(paths)
"""

from typing import List, Dict, Any, Set

def get_key_paths(data: Dict[str, Any], parent_path: str = "") -> List[str]:
    """Recursively extract all possible key paths from a nested data structure.

    This function traverses a nested dictionary or list structure and generates
    dot-notation paths for all possible keys. It handles both dictionary keys
    and list indices.

    Args:
        data: The nested data structure to analyze. Can be a dictionary or list.
        parent_path: The current path prefix (used in recursion).

    Returns:
        A list of strings representing all possible paths in the data structure.

    Example:
        >>> data = {"a": {"b": [1, 2]}, "c": 3}
        >>> paths = get_key_paths(data)
        >>> print(paths)
        ['a', 'a.b', 'a.b.0', 'a.b.1', 'c']
    """
    paths = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{parent_path}.{key}" if parent_path else key
            paths.append(path)
            paths.extend(get_key_paths(value, path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            path = f"{parent_path}.{i}"
            paths.extend(get_key_paths(item, path))
    return paths

def generate_structure_template(key_paths: List[str]) -> List[str]:
    """Generate a structural template from a list of key paths.

    This function takes a list of key paths and generates a normalized template
    structure by replacing numeric indices with '[]' notation. This is useful
    for documenting or validating metadata structures.

    Args:
        key_paths: List of dot-notation paths from get_key_paths().

    Returns:
        A sorted list of template paths with numeric indices replaced by '[]'.

    Example:
        >>> paths = ['a.b.0', 'a.b.1', 'c.d.2']
        >>> templates = generate_structure_template(paths)
        >>> print(templates)
        ['a.b.[]', 'c.d.[]']
    """
    templates: Set[str] = set()
    for path in key_paths:
        parts = path.split('.')
        template_parts = [part if not part.isdigit() else '[]' for part in parts]
        templates.add(".".join(template_parts))
    return sorted(list(templates))