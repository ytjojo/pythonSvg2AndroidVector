# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an SVG to Android VectorDrawable (AVD) converter tool. It takes SVG files and converts them to Android-compatible XML vector drawable format, handling various SVG elements like paths, shapes, colors, and styling attributes.

## Key Architecture

- **converter.py**: Main conversion engine with SVG parsing and AVD generation
- **Core conversion functions**: Handles SVG elements (line, rect, circle, ellipse, polygon, polyline, path) → Android VectorDrawable paths
- **Color normalization**: Handles SVG colors → Android ARGB format with alpha channel
- **Unit conversion**: px → dp unit conversion for Android compatibility

## Commands

### Basic Usage
```bash
# Convert single SVG file
python3 converter.py -i input.svg -o output_dir

# Batch convert directory
python3 converter.py -i svg_dir -o avd_output

# Recursive processing
python3 converter.py -i svg_dir -o avd_output -r
```

### Development
```bash
# Run converter with test files
python3 converter.py -i svg_dir -o avd_output

# Check converter help
python3 converter.py --help
```

## Key Components

- **convert_svg_to_avd()**: Main conversion function that parses SVG and generates AVD XML
- **convert_element_to_path()**: Converts SVG shapes to path data for Android compatibility
- **normalize_color()**: Handles color format conversion (SVG → Android ARGB)
- **convert_units()**: Converts pixel units to Android dp units
- **batch_convert()**: Handles directory batch processing

## File Structure
- `converter.py`: Main conversion script
- `svg_dir/`: Input SVG files directory
- `avd_output/`: Output directory for generated Android VectorDrawable XML files
- `bash.md`: Usage documentation and reference links