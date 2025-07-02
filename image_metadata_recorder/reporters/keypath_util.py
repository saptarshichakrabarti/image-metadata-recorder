import re
from typing import Any, Set, List


def extract_key_paths(data: Any, parent: str = "") -> Set[str]:
    """
    Recursively extract all key paths from a nested dict/list.
    Returns a set of dot-separated key paths, including indices for lists.
    """
    paths = set()
    if isinstance(data, dict):
        for k, v in data.items():
            path = f"{parent}.{k}" if parent else k
            paths.add(path)
            paths.update(extract_key_paths(v, path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            path = f"{parent}.{i}" if parent else str(i)
            paths.add(path)
            paths.update(extract_key_paths(item, path))
    return paths


def template_key_paths(paths: Set[str]) -> List[str]:
    """
    Replace all numeric indices in key paths with [] for structure template.
    Returns a sorted list of unique template paths.
    """
    return sorted({re.sub(r"\.(\d+)", r".[]", p) for p in paths})


def write_key_paths_to_file(data: Any, keypath_file: str, template_file: str):
    """
    Given a dict (parsed JSON), write all key paths and structure template paths to files.
    """
    key_paths = sorted(extract_key_paths(data))
    with open(keypath_file, "w") as f:
        for p in key_paths:
            f.write(p + "\n")
    structure_paths = template_key_paths(set(key_paths))
    with open(template_file, "w") as f:
        for p in structure_paths:
            f.write(p + "\n")


# Example usage (uncomment to use as a script):
# if __name__ == "__main__":
#     import sys
#     json_file = sys.argv[1]
#     keypath_file = sys.argv[2]
#     template_file = sys.argv[3]
#     with open(json_file) as f:
#         data = json.load(f)
#     write_key_paths_to_file(data, keypath_file, template_file)
