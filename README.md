# File Organizer CLI

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests Passing](https://img.shields.io/badge/tests-10/10%20passing-brightgreen.svg)](#running-tests)

A command-line utility to intelligently organize files from a source directory into categorized subdirectories within a destination, featuring recursive processing and smart deduplication.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Usage](#usage)
  - [Command-Line Arguments](#command-line-arguments)
  - [Examples](#examples)
- [File Categorization](#file-categorization)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Future Enhancements (Ideas)](#future-enhancements-ideas)
- [License](#license)
- [Contributing](#contributing)
- [Contact](#contact)

## Overview

The File Organizer CLI is a Python script designed to help users tidy up their digital spaces. It takes a source directory, scans it recursively for files, and moves them into a structured set of category-based subfolders within a specified destination directory. This tool is particularly useful for decluttering download folders, project archives, or any collection of miscellaneous files.

The script prioritizes data integrity by handling potential file duplicates intelligently:
- **Identical files** (same name and content) are skipped to avoid redundancy.
- Files with **conflicting names but different content** are automatically renamed with a numerical suffix before being moved.

## Key Features

*   **Recursive Organization:** Scans the entire source directory, including all nested subfolders.
*   **Extension-Based Categorization:** Sorts files into predefined category folders (e.g., "Images", "Documents", "Archives") based on their file extensions. The mapping is easily customizable within the script.
*   **Intelligent Deduplication:**
    *   Uses SHA256 hashing to compare file content for accurate duplicate detection.
    *   Skips moving a file if an identical version (same name and hash) already exists at the destination.
    *   Automatically renames files (e.g., `document(1).pdf`) if a file with the same name but different content exists at the destination.
*   **Dry-Run Mode:** Allows users to preview the organization plan without making any actual changes to the file system. Intended actions are logged to the console.
*   **Verbose Logging:** Offers detailed logging, including a DEBUG level for in-depth process tracing, helping with troubleshooting and understanding the script's operations.
*   **Command-Line Interface:** Easy-to-use CLI with clear arguments for specifying source, destination, and operational modes.
*   **Cross-Platform Compatibility:** Written in Python, making it inherently cross-platform (Windows, macOS, Linux).
*   **Robust Error Handling:** Includes checks for invalid paths and gracefully handles potential errors during file operations or hash calculations.
*   **Comprehensive Unit Tests:** A full suite of unit tests (10/10 passing) ensures reliability and maintainability, covering core logic, edge cases, and error scenarios.

## Tech Stack

*   **Language:** Python 3.8+
*   **Core Libraries:**
    *   `pathlib`: For modern, object-oriented path manipulation.
    *   `shutil`: For high-level file operations (moving files).
    *   `hashlib`: For generating file content hashes (SHA256).
    *   `argparse`: For parsing command-line arguments.
    *   `logging`: For structured application logging.
*   **Testing:**
    *   `unittest` (Python's built-in testing framework)
    *   `unittest.mock` (for creating mock objects and patching)
    *   (Optionally, if you use it: `pytest` for test execution)

## Installation

1.  **Clone the repository (or download the script):**
    ```
    git clone https://github.com/GisellyOliveira/smart-data-wrangle-cli.git
    ```

2.  **Python Environment (Recommended):**
    It's good practice to use a virtual environment:
    ```
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **No external dependencies are required** for the core script functionality if you are using Python 3.8 or newer, as it relies on built-in libraries. If you plan to run tests with `pytest` or use `coverage`, you might install them:
    ```
    # Optional, for development/testing
    # pip install pytest coverage
    ```

## Usage

The script is run from the command line.

### Command-Line Arguments

usage: 
```
organizer.py [-h] [--dry-run] [-v] source_dir dest_dir
```

Organizes files from a source directory (recursively) into subdirectories
within a destination directory based on file extension, handling duplicates.
positional arguments:

- **source_dir** The source directory containing files to organize.
- **dest_dir** The base destination where organized sub-folders will be created.

options:
- *-h, --help* show this help message and exit
- *--dry-run* Simulates the organization process without actually moving files.
- Logs intended actions instead.
- *-v, --verbose*- Increase output verbosity to DEBUG level.


### Examples

1.  **Organize files from `~/Downloads` into `~/OrganizedFiles`:**
    ```
    python organizer.py ~/Downloads ~/OrganizedFiles
    ```

2.  **Perform a dry run to see what would happen:**
    ```
    python organizer.py /path/to/messy_folder /path/to/clean_folder --dry-run
    ```

3.  **Organize files with verbose (DEBUG level) logging:**
    ```
    python organizer.py ./my_source ./my_destination -v
    ```

## File Categorization

Files are categorized based on the `EXTENSION_MAP` dictionary defined at the top of `organizer.py`. You can customize this map to change categories or add support for more file types. Some examples include:

*   `.pdf`, `.docx` -> `Documents/`
*   `.jpg`, `.png` -> `Images/`
*   `.zip`, `.rar` -> `Archives/`
*   `.mp3` -> `Music/`
*   ...and many more.

Files with no extension or unmapped extensions are logged and skipped.

## Running Tests

The project includes a comprehensive suite of unit tests to ensure its functionality and reliability.

To run the tests:
```
python -m unittest test_organizer.py -v
```

Or, if you have pytest installed:

``` 
pytest -s 
```
All 10 tests should pass.

## Project Structure

|── organizer.py        # The main script for file organization.\
|── test_organizer.py   # Unit tests for organizer.py.\
|── README.md           # This file.\
└── .gitignore          # Specifies intentionally untracked files that Git should ignore.

### Optional:

|── requirements.txt    # For listing dependencies (if any beyond standard library).\
└── venv/               # Virtual environment directory (if used).


## Future Enhancements (Ideas)

While this tool is already quite capable, here are some potential future enhancements:

*   **Interactive & Customizable Extension Mapping (Under Development / Next Up!):**
    *   Allow users to interactively define destination folders for newly discovered file extensions not present in the default map during an organization session.
    *   Provide an option to review and customize the default `EXTENSION_MAP` before organizing.
    *   Implement a user configuration file (e.g., JSON or YAML) to persist custom mappings between sessions, making the tool highly adaptable to individual user preferences and evolving needs.
*   **Configuration File for `EXTENSION_MAP`:** (Este pode ser combinado ou ser um sub-item do anterior) Allow `EXTENSION_MAP` to be loaded from an external JSON or YAML file for easier customization without modifying the script.
*   **Enhanced CLI with `Typer` or `Click`:** Improve the command-line experience with more advanced argument parsing, auto-completion hints, and richer help messages.
*   **Customizable Naming for Duplicates:** Option to define a different pattern for renaming conflicting files.
*   **"Undo" Functionality:** A more advanced feature to revert the last organization (would require careful state management).
*   **GUI Version:** A graphical user interface for users less comfortable with the command line.
*   **Parallel Processing:** For very large numbers of files, explore parallelizing hash calculations or file operations.
*   **Plugin System:** Allow users to write plugins for custom actions or categorization rules.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details.

## Contributing
Contributions, issues, and feature requests are welcome! Please feel free to:
- Open an issue if you find a bug or have a suggestion.
- Fork the repository and submit a pull request with your improvements.

**Please try to follow existing coding style and ensure tests pass with your changes.**

## Contact
*Giselly Oliveira* - **E-mail: gioliveira@protonmail.com**
Project Link: https://github.com/GisellyOliveira/smart-data-wrangle-cli.git