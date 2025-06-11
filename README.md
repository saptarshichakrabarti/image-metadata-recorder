# Image Metadata Recorder

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen)](https://github.com/yourusername/image-metadata-recorder#readme)

A specialized tool for biomedical researchers to extract, analyze, and document metadata from various microscopy image formats. This package is designed to support research workflows by providing detailed insights into image acquisition parameters and experimental conditions.

## Features

- **Multi-format Support**
  - TIFF and QPTIFF file processing
  - CZI (Carl Zeiss Image) file support
  - Extensible architecture for additional formats

- **Comprehensive Metadata Extraction**
  - Image dimensions and properties
  - Channel information and configurations
  - Acquisition parameters
  - Instrument settings
  - Custom metadata fields

- **Analysis Tools**
  - Metadata structure analysis
  - Key path extraction
  - Template generation for metadata validation
  - Pattern recognition in metadata structures

- **Reporting Capabilities**
  - Markdown report generation
  - PDF report creation (requires pandoc)
  - Structured data output in JSON format
  - Customizable report templates

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- pandoc (optional, for PDF report generation)

### Basic Installation

```bash
pip install image-metadata-recorder
```

### Development Installation

```bash
git clone https://github.com/saptarshichakrabarti/image-metadata-recorder.git
cd image-metadata-recorder
pip install -e ".[dev]"
```

## Usage

### Command Line Interface

The tool can be used directly from the command line:

```bash
# Process all supported files in the current directory
record_image_metadata

# Skip PDF generation
record_image_metadata --skip-pdf
```

### Output Files

For each processed image, the tool generates:
- `*_metadata.json`: Complete metadata in JSON format
- `*_key_paths.txt`: List of all metadata paths
- `*_structure_template.txt`: Template of metadata structure
- `*_report.md`: Human-readable report
- `*_report.pdf`: PDF version of the report (if pandoc is available)

### Example Workflow

1. Place your image files in a directory
2. Run the tool:
   ```bash
   record_image_metadata
   ```
3. Review the generated reports and metadata files
4. Use the structure templates for metadata validation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [aicspylibczi](https://github.com/AllenCellModeling/aicspylibczi) for CZI file support
- [tifffile](https://github.com/cgohlke/tifffile) for TIFF processing
- [pypandoc](https://github.com/bebraw/pypandoc) for PDF generation
