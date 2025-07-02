# Image Metadata Recorder

A specialized tool for biomedical researchers to extract, analyze, and document metadata from various microscopy image formats. This package is designed to support research workflows by providing detailed insights into image acquisition parameters and experimental conditions.

## Features

- **Multi-format Support**
  - TIFF, QPTIFF, and CZI (Carl Zeiss Image) file processing
  - Extensible architecture for additional formats

- **Comprehensive Metadata Extraction**
  - Image dimensions and properties
  - Channel information and configurations
  - Acquisition parameters
  - Instrument settings
  - Custom metadata fields

- **Reporting Capabilities**
  - Markdown report generation
  - Structured data output in JSON format

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Basic Installation

```bash
pip install image-metadata-recorder
```

### Development Installation

```bash
git clone https://github.com/saptarshichakrabarti/image-metadata-recorder.git
cd image-metadata-recorder
pip install -e .
```

## Usage

### Command Line Interface

The tool can be used directly from the command line:

```bash
# Process all supported files in the current directory
record_image_metadata .
```

### Output Files

For each processed image, the tool generates:
- `*_raw_metadata.json`: Complete raw metadata in JSON format
- `*_processed_metadata.json`: Cleaned and promoted metadata in JSON format
- `*_key_paths.txt`: List of all metadata paths (for structure analysis)
- `*_report.md`: Human-readable Markdown report

### Example Workflow

1. Place your image files in a directory
2. Run the tool:
   ```bash
   record_image_metadata .
   ```
3. Review the generated reports and metadata files

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [aicspylibczi](https://github.com/AllenCellModeling/aicspylibczi) for CZI file support
- [tifffile](https://github.com/cgohlke/tifffile) for TIFF processing
