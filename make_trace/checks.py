"""
Checks of the paths chosen in the GUI

They run as soon as a path is chosen, before anything is processed, so that
problems can be shown next to the path, and the Run button can stay disabled
until they are fixed. They don't use tkinter.
"""

import csv
from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".opus"}
RECORDINGS_COLUMNS = ["audio_file", "elan_file", "display_name"]
# Image types that can be used as logos (as in processing.encode_logo_image)
LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

# ------------------------------------------------------------------
# PATH CHECKS
#
# Each check returns a (status, info) tuple, where status is one of
# "ok", "warn" or "error", and info is a short text shown next to the path
# ------------------------------------------------------------------

def plural(n, noun):
    """Return e.g. '1 speaker' or '5 speakers'"""
    return f"{n} {noun}{'' if n == 1 else 's'}"

def read_csv(path):
    """
    Read a CSV file the same way processing does

    Args:
        path: path to the CSV file

    Returns:
        tuple: list of column names, and list of rows as dictionaries

    Raises:
        OSError, UnicodeDecodeError, csv.Error: if the file can't be read
    """

    with open(Path(path), mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        return (reader.fieldnames or []), rows

def check_folder(path, extensions, noun):
    """
    Check that a folder exists and contains files of the given types

    Args:
        path: path to the folder
        extensions: set of file extensions to count, e.g. {".eaf"}
        noun: what the files are called in the info, e.g. "ELAN"

    Returns:
        tuple: status ("ok", "warn" or "error") and a short info text, e.g. "12 ELAN files"
    """
    folder = Path(path)
    if not folder.is_dir():
        return "error", "folder not found"

    n = sum(1 for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in extensions)
    if n == 0:
        return "warn", f"no {noun} files found"

    return "ok", plural(n, f"{noun} file")

def check_speakers(path):
    """
    Check the speakers CSV: it must be readable and have a 'Name' column

    Args:
        path: path to the CSV file

    Returns:
        tuple: status ("ok", "warn" or "error") and a short info text, e.g. "5 speakers"
    """
    if not Path(path).is_file():
        return "error", "file not found"

    try:
        columns, rows = read_csv(path)
    except (OSError, UnicodeDecodeError, csv.Error):
        return "error", "cannot read as UTF-8 CSV"

    if "Name" not in columns:
        return "error", "no 'Name' column"

    return "ok", plural(len(rows), "speaker")

def check_recordings(path, audio_dir, elan_dir):
    """
    Check the recordings CSV and the files it refers to

    The CSV must be readable and have all the RECORDINGS_COLUMNS. If the
    audio and ELAN folders are valid, the audio and ELAN files of each
    recording are looked up in them; missing files give a warning.

    Args:
        path: path to the CSV file
        audio_dir: path to the audio folder, or an empty string
        elan_dir: path to the ELAN folder, or an empty string

    Returns:
        tuple: status ("ok", "warn" or "error") and a short info text, e.g. "12 recordings" or
        "12 recordings · missing 1 audio"
    """
    if not Path(path).is_file():
        return "error", "file not found"

    try:
        columns, rows = read_csv(path)
    except (OSError, UnicodeDecodeError, csv.Error):
        return "error", "cannot read as UTF-8 CSV"

    missing_columns = [c for c in RECORDINGS_COLUMNS if c not in columns]
    if missing_columns:
        return "error", f"no column(s): {', '.join(missing_columns)}"

    info = plural(len(rows), "recording")

    # Cross-check against the selected folders, if they are valid
    missing = []
    for column, folder, noun in [("audio_file", audio_dir, "audio"),
                                 ("elan_file", elan_dir, "ELAN")]:
        if folder and Path(folder).is_dir():
            n = sum(1 for row in rows
                    if not Path(folder).joinpath(row[column] or "").is_file())
            if n:
                missing.append(f"{n} {noun}")

    if missing:
        return "warn", f"{info} · missing {', '.join(missing)}"

    return "ok", info

def check_markdown(path):
    """
    Check that a help or licence file exists

    Args:
        path: path to the file

    Returns:
        tuple: status ("ok", "warn" or "error") and a short info text (empty for an existing file)
    """
    if not Path(path).is_file():
        return "error", "file not found"

    return "ok", ""

def check_logos(path):
    """
    Check a logos CSV the way processing.read_logos() reads it

    A file without an 'image' or a 'text' column is an error, since no
    logos would be added. Rows that processing would skip (no image or
    text, or a missing or unsupported image) give a warning.

    Args:
        path: path to the CSV file

    Returns:
        tuple: status ("ok", "warn" or "error") and a short info text, e.g. "3 logos" or
        "2 logos · 1 skipped"
    """

    if not Path(path).is_file():
        return "error", "file not found"

    try:
        # utf-8-sig skips the byte order mark which Excel adds to CSV files
        with open(Path(path), encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            columns = [c.strip().lower() for c in (reader.fieldnames or [])]
            rows = [{k.strip().lower(): (v or "").strip()
                     for k, v in row.items() if k}
                    for row in reader]
    except (OSError, UnicodeDecodeError, csv.Error):
        return "error", "cannot read as UTF-8 CSV"

    if "image" not in columns and "text" not in columns:
        return "error", "no 'image' or 'text' column"

    # Rows that processing would skip: no image or text, or a missing or
    # unsupported image (relative to the CSV file)
    logos = skipped = 0
    for row in rows:
        if not any(row.values()):
            continue
        image = row.get("image", "")
        if image:
            image_file = Path(path).parent.joinpath(image)
            usable = (image_file.is_file() and
                      image_file.suffix.lower() in LOGO_EXTENSIONS)
        else:
            usable = bool(row.get("text", ""))
        if usable:
            logos += 1
        else:
            skipped += 1

    if skipped:
        return "warn", f"{plural(logos, 'logo')} · {skipped} skipped"
    if logos == 0:
        return "warn", "no logos in the file"

    return "ok", plural(logos, "logo")

def check_output(path):
    """
    Check the output folder, and whether it already has TrACE files

    Args:
        path: path to the folder, in which a TrACE folder will be created

    Returns:
        tuple: status ("ok", "warn" or "error") and a short info text
    """
    if not Path(path).is_dir():
        return "error", "folder not found"

    if Path(path).joinpath("TrACE").is_dir():
        return "ok", "existing TrACE files will be updated"

    return "ok", "TrACE files will be created here"
