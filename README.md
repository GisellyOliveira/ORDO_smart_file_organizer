# ORDO
## Smart File Organizer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/tests-29 passing-brightgreen" alt="Tests Passing">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License">
</p>

A robust command-line utility to intelligently organize files from a source directory into categorized subdirectories, featuring recursive processing, smart deduplication, and interactive user-driven configuration.

---

## 🌟 Key Features

*   **🗂️ Recursive Organization**: Scans the entire source directory, including all nested subfolders, to find every file.
*   **🧩 Extension-Based Categorization**: Sorts files into logical category folders (e.g., "Images", "Documents", "Archives") based on their file extensions.
*   **💡 Smart Deduplication**:
    *   Uses **SHA256 hashing** to accurately detect identical files.
    *   Skips moving files if a true duplicate already exists at the destination.
    *   Automatically renames files (e.g., `document(1).pdf`) if a file with the same name but different content exists.
*   **⚙️ Interactive & Persistent Configuration**:
    *   On first run with a new file type, the tool **interactively prompts** you to decide which folder it belongs to.
    *   Allows you to **review and modify** existing mappings on the fly.
    *   Saves your custom mappings to a persistent config file, so the tool learns and adapts to your workflow.
*   **🔬 Safe Dry-Run Mode**: Use the `--dry-run` flag to preview the entire organization plan without moving a single file, ensuring complete peace of mind.
*   **✅ Fully Tested**: Comes with a comprehensive suite of **29 unit and integration tests** ensuring reliability and maintainability.

---

## 🛠️ Tech Stack

*   **Language**: Python 3.8+
*   **Core Libraries**: `pathlib`, `shutil`, `hashlib`, `argparse`, `logging`, `json`
*   **User Configuration**: `platformdirs` (for cross-platform config file placement)
*   **Testing**: `unittest` (Framework), `unittest.mock` (Mocking)

---

## 🚀 Getting Started

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/GisellyOliveira/smart-data-wrangle-cli.git
    cd smart-data-wrangle-cli
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate

    # For Windows
    python -m venv .venv
    .\.venv\Scripts\activate
    ```
    
3.  **Install dependencies:**
    The only external dependency is `platformdirs`, which is used for smart config file placement.
    ```bash
    pip install -r requirements.txt
    ```

### Usage

The script is run from the command line, providing a source and a destination directory.

```bash
python -m file_organizer <source_directory> <destination_directory> [options]
```

**Examples:**

*   **Organize your messy Downloads folder:**
    ```bash
    python -m file_organizer ~/Downloads ~/OrganizedDocuments
    ```

*   **Perform a safe dry-run to see what would happen:**
    ```bash
    python -m file_organizer /path/to/messy_folder /path/to/clean_folder --dry-run
    ```

*   **Run with verbose logging for detailed output:**
    ```bash
    python -m file_organizer ./source ./destination -v
    ```

---

## 🧪 Running Tests

The project is backed by a robust test suite to ensure quality and prevent regressions.

To run all 29 tests, execute the following command from the root directory:
```bash
python -m unittest discover -v
```

---

## 🎯 Future Enhancements

This project has a strong foundation for exciting future developments:

*   **🧠 Machine Learning-Powered Classification**:
    *   Implement a feature to analyze file content, not just extensions, for more intelligent categorization.
    *   **For text documents (`.pdf`, `.docx`):** Use Natural Language Processing (NLP) techniques (e.g., with libraries like `scikit-learn` or `spaCy`) to classify them into folders like "Invoices", "Contracts", or "Research Papers" based on their text.
    *   **For images (`.jpg`, `.png`):** Use computer vision models (e.g., with `TensorFlow` or `PyTorch`) to sort images into categories like "Landscapes", "Portraits", or even "Screenshots".

*   **🖥️ Graphical User Interface (GUI)**:
    *   Develop a user-friendly desktop application using a framework like **PyQt**, **Tkinter**, or **Kivy**.
    *   A GUI would make the tool accessible to non-technical users and provide visual feedback, drag-and-drop functionality, and an easier way to manage custom rules.

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Please feel free to open an issue or submit a pull request.

---

## 📧 Contact

Giselly Oliveira - gioliveira@protonmail.com