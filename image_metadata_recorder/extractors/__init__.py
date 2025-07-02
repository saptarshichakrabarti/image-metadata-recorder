import logging
from typing import Callable, Dict, Optional, Any
from importlib.metadata import entry_points as iter_entry_points  # Renamed for clarity

# Import built-in extractors
from . import tiff_extractor, czi_extractor

# Import WorkflowContext for type hinting Callable argument
from image_metadata_recorder.workflow.context import WorkflowContext

logger = logging.getLogger(__name__)

# Define the new signature for extractor functions
ExtractorCallable = Callable[[WorkflowContext], Dict[str, Any]]

# Initialize with built-in extractors
# These are always available. Plugins can add to this or override if names clash (last one loaded wins for a given key).
# Keys are file extensions (lowercase, with leading dot).
_BUILTIN_EXTRACTORS: Dict[str, ExtractorCallable] = {
    ".tiff": tiff_extractor.extract,
    ".tif": tiff_extractor.extract,
    ".qptiff": tiff_extractor.extract,
    ".czi": czi_extractor.extract,
}

# Global registry that will be populated once
_EXTRACTOR_REGISTRY: Optional[Dict[str, ExtractorCallable]] = None


def _load_extractors() -> Dict[str, ExtractorCallable]:
    """
    Loads extractors from entry points and merges them with built-in extractors.
    This function should ideally be called only once.
    """
    global _EXTRACTOR_REGISTRY
    if _EXTRACTOR_REGISTRY is not None:
        return _EXTRACTOR_REGISTRY

    logger.info("Initializing extractor registry...")
    # Start with built-in extractors
    # Make a copy to avoid modifying the original _BUILTIN_EXTRACTORS dict if loaded multiple times by mistake
    loaded_registry: Dict[str, ExtractorCallable] = _BUILTIN_EXTRACTORS.copy()

    logger.debug(f"Built-in extractors registered: {list(loaded_registry.keys())}")

    # Discover and load plugins from the entry point group
    discovered_plugins = iter_entry_points(group="image_metadata_recorder.extractors")

    for entry_point in discovered_plugins:
        try:
            logger.debug(
                f"Found plugin entry point: {entry_point.name} from {entry_point.value}"
            )
            loaded_plugin_module = (
                entry_point.load()
            )  # This loads the callable (e.g., an 'extract' function)

            # Adopting Option 1 for now as per the plan's simplicity: entry_point.name is the extension.
            file_extension_from_plugin_name = entry_point.name
            if not file_extension_from_plugin_name.startswith("."):
                logger.warning(
                    f"Extractor plugin '{entry_point.name}' from '{entry_point.module_name}' "
                    f"uses an entry point name that does not start with a dot. "
                    f"Assuming it's a descriptive name, not the file extension. Plugin will not be registered by name. "
                    f"The plugin itself must register extensions if this is the case, or use the extension as the entry point name."
                )
                continue

            if not callable(loaded_plugin_module):
                logger.warning(
                    f"Plugin {entry_point.name} from {entry_point.module_name} "
                    f"did not load a callable function. Loaded: {type(loaded_plugin_module)}. Skipping."
                )
                continue

            normalized_extension = file_extension_from_plugin_name.lower()
            if normalized_extension in loaded_registry:
                logger.warning(
                    f"Plugin '{entry_point.name}' (from {entry_point.module_name}) "
                    f"is overriding the extractor for extension '{normalized_extension}'."
                )

            loaded_registry[normalized_extension] = loaded_plugin_module
            logger.info(
                f"Successfully loaded and registered extractor plugin for '{normalized_extension}' from {entry_point.module_name}."
            )

        except Exception as e:
            logger.error(
                f"Failed to load extractor plugin '{entry_point.name}': {e}",
                exc_info=True,
            )

    _EXTRACTOR_REGISTRY = loaded_registry
    logger.info(
        f"Extractor registry fully initialized. Total extractors: {len(_EXTRACTOR_REGISTRY)}. Keys: {list(_EXTRACTOR_REGISTRY.keys())}"
    )
    return _EXTRACTOR_REGISTRY


def get_extractor(file_extension: str) -> Optional[ExtractorCallable]:
    """
    Retrieves the appropriate metadata extractor function for a given file extension
    from the dynamically populated registry.

    Args:
        file_extension: The file extension (e.g., ".tiff", ".czi").
                        It should include the leading dot.

    Returns:
        A callable function that takes a WorkflowContext object and returns a
        dictionary of extracted metadata, or None if no extractor is found
        for the given extension.
    """
    # Ensure registry is loaded
    if _EXTRACTOR_REGISTRY is None:
        _load_extractors()  # Load on first call

    current_registry = _EXTRACTOR_REGISTRY if _EXTRACTOR_REGISTRY is not None else {}

    return current_registry.get(file_extension.lower())


# Optional: function to force reload or inspect registry
def get_registered_extractors() -> Dict[str, str]:
    """Returns a dictionary of registered extensions and their module source for inspection."""
    if _EXTRACTOR_REGISTRY is None:
        _load_extractors()

    desc = {}
    if _EXTRACTOR_REGISTRY:
        for ext, func in _EXTRACTOR_REGISTRY.items():
            desc[ext] = f"{func.__module__}.{func.__name__}"
    return desc
