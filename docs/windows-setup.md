# Windows setup

This guide covers the local Python scripts in this repository on 64-bit Windows 10/11.
The plugin itself is designed for Claude Code; these steps install the command-line
tools needed by its PDF production scripts.

## 1. Install Python

Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/windows/).
During setup, enable **Add python.exe to PATH**.

Open a new PowerShell window and verify:

```powershell
py --version
```

The version must be 3.11 or newer. Python 3.11+ includes `tomllib`; no extra
Python package is needed for TOML parsing.

## 2. Install Typst

In PowerShell, run:

```powershell
winget install --id Typst.Typst
```

Close and reopen PowerShell, then verify:

```powershell
typst --version
```

If `winget` is unavailable, use the Windows executable download on the
[official Typst installation page](https://typst.app/open-source/), extract it,
and add the folder containing `typst.exe` to your user PATH.

## 3. Install Poppler for Windows

The PDF checks need three Poppler commands: `pdfinfo`, `pdftotext`, and
`pdffonts`.

1. Open the [Poppler Windows releases](https://github.com/oschwartz10612/poppler-windows/releases/latest).
2. Download the latest ZIP asset for Windows.
3. Extract it to a permanent folder, for example `C:\Tools\poppler`.
4. Find the extracted `Library\bin` folder. It contains the Poppler `.exe` files.
5. Add that exact `Library\bin` folder to your **user PATH** in Windows Environment Variables.
6. Close and reopen PowerShell.

Verify all three commands:

```powershell
pdfinfo -v
pdftotext -v
pdffonts -v
```

If PowerShell says a command is not recognized, the Poppler `Library\bin`
folder is not on PATH yet. Do not continue until all three commands work.

## 4. Verify the complete environment

Run:

```powershell
py --version
typst --version
pdfinfo -v
pdftotext -v
pdffonts -v
```

All five commands must respond before running the PDF pipeline.

## 5. Run the project scripts

Open PowerShell in the book project folder — the folder containing `book.toml` —
and run the scripts from the plugin repository. For example:

```powershell
py C:\path\to\KDP-Publishing-Plugin\scripts\build-interior.py
py C:\path\to\KDP-Publishing-Plugin\scripts\preflight.py
py C:\path\to\KDP-Publishing-Plugin\scripts\build-cover.py
py C:\path\to\KDP-Publishing-Plugin\scripts\kdp-package.py
```

Replace `C:\path\to\KDP-Publishing-Plugin` with the actual location where
you downloaded or cloned this repository.

Build the interior first, run preflight, then build the cover. The cover must
be built from the finished interior because its spine width depends on the
measured page count.

## Troubleshooting

- **`py` not found:** reinstall Python and enable the PATH option, or use the
  full path to `python.exe`.
- **`typst` not found:** reopen PowerShell after installation; otherwise add
  the folder containing `typst.exe` to PATH.
- **`pdfinfo`, `pdftotext`, or `pdffonts` not found:** add Poppler's
  `Library\bin` folder to PATH and reopen PowerShell.
- **A script says `book.toml` is missing:** run it from inside the book project
  folder, or pass the project path using `--project`.
- **A PDF check fails:** read the reported error and fix the source or PDF before
  uploading. A successful mechanical preflight does not replace checking the
  book in KDP's Print Previewer and reviewing a proof copy.
