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
