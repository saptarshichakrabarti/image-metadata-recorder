# image_metadata_recorder/workflow/context.py
from pathlib import Path
from typing import Optional, Any
from pydantic import BaseModel, Field


class WorkflowContext(BaseModel):
    """
    Manages and passes shared state and configurations throughout the metadata processing pipeline.
    """

    # Core resources
    output_dir: Path = Field(
        ..., description="The base directory where all output files will be saved."
    )
    logger: Any = Field(
        ...,
        description="A configured logger instance for consistent logging across components.",
    )

    # File-specific information (could be updated per file in a batch process)
    current_input_filepath: Optional[Path] = Field(
        None,
        description="The absolute path to the image file currently being processed.",
    )
    current_base_filename: Optional[str] = Field(
        None, description="The base name (stem) of the file currently being processed."
    )

    # Configuration / Flags (can be extended)
    skip_pdf_generation: bool = Field(
        False,
        description="Flag to indicate whether PDF report generation should be skipped.",
    )
    # Example: Could add more config like 'force_overwrite: bool = False'

    # Placeholder for other shared resources or results that components might need to pass
    # shared_cache: Optional[Dict[str, Any]] = Field(default_factory=dict, description="A shared cache for intermediate results, if needed.")

    class Config:
        # Pydantic config: allow arbitrary types for logger instance
        arbitrary_types_allowed = True

    def get_output_path(self, suffix: str, prefix: Optional[str] = None) -> Path:
        """
        Generates a standardized output path within the context's output_dir
        for the current file, using a given suffix.
        """
        if not self.current_base_filename:
            raise ValueError(
                "current_base_filename must be set in context to generate output paths."
            )

        filename = f"{prefix or ''}{self.current_base_filename}{suffix}"
        return self.output_dir / filename

    def set_current_file(self, filepath: Path):
        """Updates context with the current file being processed."""
        self.current_input_filepath = filepath.resolve()
        self.current_base_filename = filepath.stem
        self.logger.debug(f"Context updated for file: {self.current_input_filepath}")


# Example usage (for illustration, not part of the class itself):
# if __name__ == '__main__':
#     # Setup a dummy logger for example
#     logging.basicConfig(level=logging.DEBUG)
#     dummy_logger = logging.getLogger("context_example")
#
#     # Create context
#     ctx = WorkflowContext(output_dir=Path("/tmp/metadata_outputs"), logger=dummy_logger)
#     print(f"Initial context: {ctx.model_dump_json(indent=2)}")
#
#     # Simulate processing a file
#     dummy_file = Path("/path/to/my_image.tiff")
#     ctx.set_current_file(dummy_file)
#     print(f"Context after setting file: {ctx.model_dump_json(indent=2)}")
#
#     # Get output paths
#     raw_json_path = ctx.get_output_path("_raw_metadata.json")
#     report_md_path = ctx.get_output_path("_report.md")
#     print(f"Raw JSON path: {raw_json_path}")
#     print(f"Report MD path: {report_md_path}")
#
#     # Accessing context attributes
#     ctx.logger.info(f"Processing {ctx.current_input_filepath} into {ctx.output_dir}")
