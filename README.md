# Godkey Control Core

This repository contains a variety of legal documents and related files.
To organize the documents into folders by file type, run `file_these.py`.
It creates a `Filed/` directory with subfolders such as `pdf/`, `tiff/`,
`jpg/`, etc. Files matching certain keywords like `"42 USC 1983"` are
grouped under `federal_us_civil_rights`.

Example usage:

```bash
python file_these.py --dry-run      # preview
python file_these.py                # move files
```
