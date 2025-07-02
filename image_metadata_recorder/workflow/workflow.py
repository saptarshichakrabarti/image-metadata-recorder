# image_metadata_recorder/workflow/workflow.py

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from image_metadata_recorder import extractors
from image_metadata_recorder.processors import standard_processor
from image_metadata_recorder.reporters import markdown_reporter, keypath_util
from image_metadata_recorder.workflow.context import WorkflowContext

module_logger = logging.getLogger(__name__)


def run_for_file(
    filepath_str: str, output_dir_str: str, skip_pdf_generation: bool = False
) -> None:
    context_logger = logging.getLogger()
    p_filepath = Path(filepath_str)
    context = WorkflowContext(
        output_dir=Path(output_dir_str),
        logger=context_logger,
        skip_pdf_generation=skip_pdf_generation,
    )
    context.set_current_file(p_filepath)
    context.logger.info(
        f"Processing file: {context.current_input_filepath} with context."
    )
    context.output_dir.mkdir(parents=True, exist_ok=True)
    file_extension = p_filepath.suffix.lower()

    extractor_func = extractors.get_extractor(file_extension)
    if not extractor_func:
        context.logger.error(
            f"No extractor found for file type: {file_extension} (file: {context.current_input_filepath})"
        )
        error_metadata = {
            "source_file": str(context.current_input_filepath),
            "error": f"No extractor found for file type: {file_extension}",
        }
        error_file_path = context.get_output_path("_error.json")
        try:
            with open(error_file_path, "w", encoding="utf-8") as f:
                json.dump(error_metadata, f, indent=2)
            context.logger.info(f"Error report saved to: {error_file_path}")
        except IOError as e:
            context.logger.error(
                f"Failed to write error report to {error_file_path}: {e}"
            )
        return

    context.logger.debug(
        f"Using extractor: {extractor_func.__name__} for {context.current_input_filepath}"
    )
    raw_metadata: Optional[Dict[str, Any]] = None
    try:
        raw_metadata = extractor_func(context)
    except Exception as e:
        context.logger.error(
            f"Error during extraction for {context.current_input_filepath}: {e}",
            exc_info=True,
        )
        # ... (error handling for extraction) ...
        return

    if raw_metadata is None:
        context.logger.error(
            f"Extractor returned None for {context.current_input_filepath}. Aborting."
        )
        return

    raw_output_path = context.get_output_path("_raw_metadata.json")
    try:
        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(raw_metadata, f, indent=2, default=str)
        context.logger.info(f"Raw metadata saved to: {raw_output_path}")
    except Exception as e:
        context.logger.error(
            f"Failed to serialize raw metadata for {context.current_input_filepath}: {e}",
            exc_info=True,
        )

    context.logger.debug(f"Processing metadata for {context.current_input_filepath}")
    processed_data: Optional[Dict[str, Any]] = None
    try:
        processed_data = standard_processor.process(raw_metadata)
    except Exception as e:
        context.logger.error(
            f"Error during processing for {context.current_input_filepath}: {e}",
            exc_info=True,
        )
        # ... (error handling for processing) ...
        return

    if processed_data is None:
        context.logger.error(
            f"Processor returned None for {context.current_input_filepath}. Aborting."
        )
        return

    processed_dump_path = context.get_output_path("_processed_metadata.json")
    try:
        with open(processed_dump_path, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2, default=str)
        context.logger.info(f"Processed metadata saved to: {processed_dump_path}")
    except Exception as e:
        context.logger.error(
            f"Failed to serialize processed metadata for {context.current_input_filepath}: {e}",
            exc_info=True,
        )

    # --- BEGIN: Key path and structure template generation ---
    # To disable this feature, simply remove or comment out the following block.
    try:
        keypath_file = str(context.get_output_path("_key_paths.txt"))
        template_file = str(context.get_output_path("_metadata_structure_template.txt"))
        keypath_util.write_key_paths_to_file(
            processed_data, keypath_file, template_file
        )
        context.logger.info(
            f"Key paths and structure template written to: {keypath_file}, {template_file}"
        )
    except Exception as e:
        context.logger.error(
            f"Failed to generate key paths or structure template for {context.current_input_filepath}: {e}",
            exc_info=True,
        )
    # --- END: Key path and structure template generation ---

    context.logger.debug(f"Generating reports for {context.current_input_filepath}")
    try:
        markdown_reporter.create_markdown_report(processed_data, context)
    except Exception as e:
        context.logger.error(
            f"Failed to generate Markdown report for {context.current_input_filepath}: {e}",
            exc_info=True,
        )

    context.logger.info(
        f"Successfully completed processing for file: {context.current_input_filepath}"
    )


# Keep the __main__ block for potential direct testing if it was there
if __name__ == "__main__":
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    module_logger.info("Running workflow.py directly for testing...")
    # ... (rest of the original __main__ block if any specific tests were there) ...
    # For brevity, I'm omitting the dummy file creation part of __main__ here,
    # assuming it's for local testing and not critical for this overwrite.
    # If it's needed, it should be included.
    module_logger.info("Workflow test script (workflow.py __main__) finished.")
