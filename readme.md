# 🚀 Account Analysis Tool

A Python utility to automatically process, clean, and analyze bank movement reports. This tool reads raw `.xls` bank statements, extracts relevant data, finds unpaid single-installment purchases, and archives the processed files.

## ✨ Features

* **Automated Cleaning:** Reads complex, multi-header bank `.xls` files.
* **Data Transformation:** Extracts only the necessary columns, converts data types, and formats dates.
* **Payment Matching:** Implements a 1-to-1 matching logic to find purchases that do not have a corresponding payment of the same amount.
* **Command-Line Interface (CLI):** Easy to run from the terminal with simple arguments.
* **File Archiving:** Automatically renames and archives both the raw input file and the clean output file with unique timestamps to prevent clutter and keep a historical record.
* **Configurable:** Easily adapt to changes in the bank's file format by modifying the `config.py` file.

---

## 📂 Project Structure

account_analyzer/
|
|-- .gitignore
|-- main.py           (Main executable script - CLI entry point)
|-- preprocessing.py  (Data cleaning and transformation logic)
|-- analysis.py       (Payment matching and reporting logic)
|-- config.py         (All settings and configurations)
|-- utils.py          (Helper functions - e.g., currency formatting)
|-- requirements.txt  (Project dependencies)
|
|-- pre-process-data/ (FOLDER: Place your raw .xls files here)
|
|-- data/             (FOLDER: Cleaned .xlsx reports are saved here)
|
|-- processed-archive/ (FOLDER: Processed raw files are archived here)

---

## 🔧 Installation & Setup

1.  **Clone or Download:**
    Get the project files and navigate into the main directory.
    ```bash
    git clone <your-repo-url>
    cd account_analyzer
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    Install all required Python libraries from `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

---

## ⚙️ How to Use

Place your raw bank `.xls` file into the `pre-process-data/` folder. Then, run the tool from your terminal.

The main script requires one argument:
* `input_file`: The path to your raw file.

It also accepts one optional argument:
* `-o, --output`: An optional prefix for your output files.

### Example 1: Basic Usage (Default Prefixes)

This command will use the default prefixes (`cleaned-movements` and `movements`) for the output files.

**Command:**
```bash
python main.py "pre-process-data/2025-11-pre-process.xls"

