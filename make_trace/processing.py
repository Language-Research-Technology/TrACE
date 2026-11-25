import base64
import csv
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
import zlib
from datetime import date
from pathlib import Path
import logging
from markdown2.markdown2 import Markdown

logger = logging.getLogger(__name__)

# The page template, compressed and encoded in base64. template_data.py is not
# part of the source code: build/package.py generates it from
# TrACE_template.html when building make_trace.pyz, so that the .pyz is
# completely standalone. To run make_trace, build the .pyz first.
from template_data import TRACE_TEMPLATE

############################### FUNCTIONS ######################################

# ======================== Processing functions ================================

def create_speakers_file(input_csv, output_js):
    """
    Create speakers.js file from a CSV

    The function outputs a list of dictionaries: each row is a list element,
    and each column corresponds to an entry in the dictionary for this row.

    The list is saved to the output file as a JavaScript constant `speakers`, 
    so that the web-interface can import the JS file and use that constant 
    directly.

    Args:
        input_csv: Path to the input CSV file
        output_js: Path to the output JS file

    Returns:
        Nothing
    """
    logger.info("Generating speakers data...")
    logger.info(f"Speakers information: {input_csv}")

    # utf-8-sig skips the byte order mark which Excel adds to CSV files;
    # otherwise it would stick to the name of the first column. The csv
    # module needs newline="" to read line breaks inside cells correctly
    with open(Path(input_csv), encoding="utf-8-sig", newline="") as file:
        speakers_dat = csv.DictReader(file)
        speakers_js = list(speakers_dat)

    # Write out as JS array
    with open(Path(output_js), "w", encoding="utf-8") as f:
        # Write the first line so that the file stores a JavaScript constant,
        # and can be loaded as a script
        f.write("const speakers = ")
        f.write(json.dumps(speakers_js, indent=2, ensure_ascii=False))

    logger.info(f"Speakers data saved to: {output_js}")


def extract_elan_annotations(input_file):
    """
    Extract annotations from an ELAN file

    Args:
        input_file: ELAN file with annotations

    Returns:
        list: a list of dictionaries, where each entry corresponds to a single 
            annotation and contains the following fields:

            + *ANNOTATION_ID*
            + *TIER_ID*
            + *content* -- annotation text
            + *start* -- start time stamp in milliseconds
            + *end* -- end timestamp in milliseconds
    """

    tree = ET.parse(Path(input_file))
    root = tree.getroot()

    # Build time slot map
    #
    # .//TIME_SLOT finds TIME_SLOT nodes at any depth within the root, not
    # just as immediate children
    time_slots = {ts.attrib["TIME_SLOT_ID"]: int(ts.attrib["TIME_VALUE"])
        for ts in root.findall(".//TIME_SLOT")}

    tiers = root.findall('TIER')
    tier_ids = [t.attrib.get('TIER_ID', 'UNKNOWN') for t in tiers]

    annotations = []

    for tier in tiers:
        tier_id = tier.attrib.get('TIER_ID', 'UNKNOWN')
        for ann in tier.findall('.//ALIGNABLE_ANNOTATION'):
            ann_id = ann.attrib.get('ANNOTATION_ID')
            start = time_slots.get(ann.attrib['TIME_SLOT_REF1'])
            end = time_slots.get(ann.attrib['TIME_SLOT_REF2'])
            value_elem = ann.find('ANNOTATION_VALUE')
            value = value_elem.text if value_elem is not None else ''
            annotations.append({
                'ANNOTATION_ID': ann_id,
                'TIER_ID': tier_id,
                'content': value,
                'start': start,
                'end': end
            })

    logger.info(f"\tELAN file: {Path(input_file).name}")
    logger.info(f"\t\tTiers: {', '.join(tier_ids)}")
    return annotations

def extract_elan_speakers(input_file, ann_note_tier = ""):
    """
    Extract speakers from an ELAN file

    For now, speakers are equated with Elan tiers, with the exception that
    notes tier (whose name can be specified in `ann_note_tier` argument) is
    excluded from this list.

    Args:
        input_file: ELAN file with annotations
        ann_note_tier: Name of Elan tier containing notes

    Returns:
        list: list of strings, each corresponding to a tier name in the input
          file
    """
    tree = ET.parse(Path(input_file))
    root = tree.getroot()

    tiers = root.findall('TIER')
    tier_ids = [t.attrib.get('TIER_ID', 'UNKNOWN') for t in tiers]

    speaker_tiers = []

    for tier_id in tier_ids:

        # Do not include notes tier in the list
        if tier_id == ann_note_tier:
            continue

        speaker_tiers.append(tier_id)

    logger.info(f"\tELAN file: {Path(input_file).name}")
    logger.info(f"\t\tSpeaker tiers: {', '.join(speaker_tiers)}")

    return(speaker_tiers)


def create_transcripts_record(audio_file, elan_file, display_name,
                              ann_note_tier = ""):
    """
    Create a single transcript (typically corresponding to a single file)

    Args:
        audio_file: path to audio file (absolute or relative to the location
            of the HTML file for the interface. This is the path where the
            interface will be looking for the audio)

        elan_file: ABSOLUTE path to the corresponding ELAN file with 
            annotations. This will will not be used by the interface directly --
            this function will extract annotations and save them in a JS file.

        display_name: display name for this recording in the interface

        ann_note_tier: Name of Elan tier containing notes

    Returns:
        dict: a dictionary with three entries: path to audio file, display name,
        and a list with annotations as produced by `extract_elan_annotations()`
    """

    annotations = extract_elan_annotations(elan_file)
    speakers = extract_elan_speakers(elan_file, ann_note_tier)

    return ({
        'filename': Path(audio_file).as_posix(),
        'displayName': display_name,
        'speakers': speakers,
        'annotations': annotations
    })


def create_transcripts_file(input_csv, output_js, elan_dir,
                            ann_note_tier = ""):
    """
    Create transcripts.js file using information from a CSV

    The input CSV is assumed to have at least these three columns:

    + audio_file: name of the audio file. It will be appended to the `audio_dir`

    + elan_file: name of the corresponding ELAN file with annotations. It will
        be appended to `elan_dir`. ELAN file will not be used by the interface 
        directly -- this function will extract annotations and save them 
        in a JS file.

    + display_name: display name for this recording in the interface

    The function outputs a list of dictionaries, where each element corresponds
    to an item produced by `create_transcripts_record()`

    Args:
        input_csv: Path to the input CSV file
        output_js: Path to the output JS file
        audio_dir: Path to the folder where the interface HTML file is looking
            for the audios (by default, it's "audio" in the same folder as the
            HTML file). Audios are assumed to be located in this directory.
        ann_note_tier: Name of Elan tier containing notes
    Returns:
        Nothing
    """
    logger.info("Generating tranhscripts data...")
    logger.info(f"Recordings information: {input_csv}")
    logger.info(f"ELAN folder: {elan_dir}")

    # Read like the speakers CSV, see create_speakers_file()
    with open(Path(input_csv), encoding="utf-8-sig", newline="") as file:
        recordings_info = list(csv.DictReader(file))

    transcripts_data = []

    for row in recordings_info:
        relative_audio_path = Path("audio").joinpath(row["audio_file"])
        relative_elan_path = Path(elan_dir).joinpath(row["elan_file"])

        transcripts_data.append(create_transcripts_record(relative_audio_path, 
                                                          relative_elan_path, 
                                                          row["display_name"],
                                                          ann_note_tier)
                                                         )

    # Write to JS file
    with open(output_js, 'w', encoding='utf-8') as f:
        f.write('const transcripts = ')
        json.dump(transcripts_data, f, indent=2, ensure_ascii=False)
        f.write(';')

    logger.info(f"Transcripts data saved to: {output_js}")
    

# ======================== Logo functions ======================================

class InvalidLogo(Exception):
    pass


def encode_logo_image(image_file):
    """
    Turn a local logo image into a base64 data URI for the `src` attribute of
    an <img> tag. This embeds the image into the HTML, so that the HTML does
    not depend on the location of the image files.

    Args:
        image_file: path to a local image file

    Returns:
        Data URI

    Raises:
        InvalidLogo: if the file does not exist or is not a supported image
    """
    # Image types which can be used as logos
    LOGO_MIME_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }
    
    # Check image file
    image_file = Path(image_file)
    
    if not image_file.is_file():
        raise InvalidLogo(f"Logo image not found: {image_file}")

    # Check that MIME type is on the allowed list
    mime_type = LOGO_MIME_TYPES.get(image_file.suffix.lower())
    if mime_type is None:
        raise InvalidLogo(
            f"Unsupported logo image type: {image_file} (supported: " +
            ", ".join(LOGO_MIME_TYPES) + ")"
        )
    
    # Read image
    data = image_file.read_bytes()
    
    # Warn about images larger than 300kB, as we are embedding them in the 
    # page
    if len(data) > 300 * 1024:
        logger.warning(f"Logo image is large ({len(data) // 1024} KB) and " +
                       f"will make the HTML file bigger: {image_file}")

    # Encode image into base64 for embedding in the template
    return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"


def make_logo(base_dir, image, text, url, title):
    """
    Create a single logo entry for the `headerLogos` template variable.
    Empty fields are left out.

    Args:
        base_dir: folder which relative image paths are resolved against
        image: path to the image file, or an empty string
        text: text to show instead of an image, or an empty string
        url: page to open when the logo is clicked, or an empty string
        title: text shown on mouse hover, or an empty string

    Returns:
        Logo dictionary

    Raises:
        InvalidLogo: if the logo has neither an image nor a text, or the image
            is invalid
    """
    if not image and not text:
        raise InvalidLogo("Each logo needs either an image or a text")

    if image:
        logo = {"image": encode_logo_image(Path(base_dir).joinpath(image))}
    else:
        logo = {"text": text}
    if url:
        logo["url"] = url
    if title:
        logo["title"] = title

    return logo


def read_logos(logos_file):
    """
    Read header logos from a CSV file.

    The CSV file should have a header row with any of the columns "image",
    "text", "url" and "title"; each further row describes one logo. Each logo
    needs either an image or a text. Relative image paths are resolved
    relative to the folder of the CSV file.

    Problems with the logos do not stop the processing: they are reported in 
    the log, and invalid logos are skipped. Links which do not start with
    http://, https:// or mailto: are reported and left out, but the logo
    itself is kept.

    Args:
        logos_file: path to the CSV file with logos, or None

    Returns:
        List of valid logo dictionaries (empty if there is no logos file)
    """
    if not logos_file:
        return []

    logos_file = Path(logos_file)

    if not logos_file.is_file():
        logger.warning(f"Logos file not found, no logos added: {logos_file}")
        return []

    try:
        # utf-8-sig skips the byte order mark which Excel adds to CSV files
        with open(logos_file, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            columns = [c.strip().lower() for c in (reader.fieldnames or [])]

            if "image" not in columns and "text" not in columns:
                logger.warning(
                    "Logos file should have an 'image' or a 'text' column, " 
                    f"no logos added: {logos_file}"
                )
                return []

            result = []
            for row_num, row in enumerate(reader, start=2):
                # Normalise column names and values
                row = {k.strip().lower(): (v or "").strip() 
                       for k, v in row.items() if k}

                # Skip empty rows
                if not any(row.values()):
                    continue

                # Only keep links to web pages and email addresses
                url = row.get("url", "")
                if url and not re.match(r"^(https?://|mailto:)", url,
                                        flags=re.IGNORECASE):
                    logger.warning(
                        f"Ignored logo link in {logos_file}, row {row_num}: " 
                        "links should start with http://, https:// or " 
                        f"mailto: ({url})"
                    )
                    url = ""

                try:
                    result.append(make_logo(base_dir=logos_file.parent,
                                            image=row.get("image", ""),
                                            text=row.get("text", ""),
                                            url=url,
                                            title=row.get("title", "")))
                except InvalidLogo as e:
                    logger.warning(f"Skipped logo in {logos_file}, " +
                                   f"row {row_num}: {e}")

    except (OSError, UnicodeDecodeError, csv.Error) as e:
        logger.warning(f"Could not read logos file, no logos added: " +
                       f"{logos_file} ({e})")
        return []

    return result


# ==================== Template rendering functions ============================

def js_value(value):
    """
    Convert a Python value to a JavaScript literal which is safe to put inside
    a <script> block in the HTML template.

    `</` is escaped, so that a value containing `</script>` does not close the
    script block early.
    """
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
   

def write_template_option(option, option_value, template_str):
    """
    Write a value for an option inside HTML template.

    Args:
        option: pattern to identify the option in HTML template. It is assumed 
            that (1) each option sits on its own line in HTML; (2) the 
            pattern contains one capture group, which captures the option,
             e.g., "^(.*const pageTitle = ).*$"
        option_value: option value to be inserted. It is inserted verbatim: 
            backslashes are not interpreted by re.sub.
        template_str: Full HTML template

    Returns:
        Modified HTML template with the new option value
    """
    return re.sub(option, lambda m: m.group(1) + option_value, template_str,
                  flags=re.MULTILINE)
                  
                  
def read_template_option(option, template_str):
    """
    Read back a value written with `write_template_option()`: the rest of
    the line that the pattern matches, after the pattern's group, without
    the closing ";"
    
    Args:
        option: pattern to identify the option in HTML template. It is assumed 
            that (1) each option sits on its own line in HTML; (2) the 
            pattern contains one capture group, which captures the option,
             e.g., "^(.*const pageTitle = ).*$"
        template_str: Full HTML template


    Returns:
        str, or None if no line matches
    """
    match = re.search(option, template_str, flags=re.MULTILINE)
    if match is None:
        return None
        
    return (template_str[match.end(1):match.end()]
                .strip()
                .removesuffix(";")
                .strip())


def insert_template_md(md_file, placeholder, template_str):
    """
    Read a markdown file, convert to HTML, and insert into the TrACE HTML 
    template. 

    This is used to insert help and licence texts.

    Args:
        md_file: path to the file with Markdown text; assumed to be in UTF-8
        placeholder: pattern to identify the placeholder in HTML template. It is 
            assumed that (1) each placeholder sits on its own line in HTML; 
            (2) the pattern contains one capture group, which captures 
            the placeholder, e.g., "^(.*helpHTML = `)`.*$"
        template_str: Full HTML template

    Returns:
        Modified HTML template with the new option value
    """
    if md_file is not None and Path(md_file).is_file():

        with open(Path(md_file), encoding='utf-8') as f:
            md_text = f.read()

        # Convert Markdown to HTML and escape symbols which might break the 
        # HTML template
        html_text = (Markdown().convert(md_text)
                     .replace("\\", "\\\\")
                     .replace("`", "\\`")
                     .replace("${", "\\${")
                     .replace("</", "<\\/"))

        out = write_template_option(placeholder, f'`{html_text}`;', 
                                    template_str)
        
        return(out)
    
    else:
        # If Markdown file does not exist, return input template without changes
        return(template_str)

def decode_template():
    """The TrACE page template, decoded from TRACE_TEMPLATE (see the top)"""
    return zlib.decompress(
        base64.b64decode(TRACE_TEMPLATE.encode("utf-8"))
    ).decode("utf-8")


def render_template(template_str, 
                    title, 
                    header, 
                    ann_note_tier, 
                    primary_color,
                    ann_highlight_color,
                    filter_match_color, 
                    help_file,
                    licence_file,
                    header_logos,
                    kept_texts=None):

    """
    Fill in the TrACE page template with the given options and info
    sections

    Args:
        template_str: HTML template as a multi-line string
        title: Page title (shown when mouse hovers over the browser tab, 
            when adding to bookmarks etc.)
        header: Interface header (shown at the top of the page)
        ann_note_tier: Name of the TIER_ID associated with notes/remarks in 
            the annotations. If such a tier exists, annotations from it will be 
            differently highlighted.
        primary_color: Main interface color
        ann_higlight_color: Annotation highlight color (for highligting 
            annotations which are currently playing)
        filter_match_color: Filter match color (for highlighting record buttons
            which match the current filters)
        help_file: path to Markdown file with help text, or None
        licence_file: path to Markdown file with licence text, or None
        header_logos: list of logos for the header, as produced by 
            `read_logos()`, or None
        kept_texts: help and licence texts to keep from an existing page,
            under the name of the option they belong to ("help_file",
            "licence_file"), as produced by `read_TrACE_info_sections()`; used 
            if the help or licence file is not given or not found

    Returns:
        str: the page
    """

    out = template_str

    # Page options: title, header, notes tier and colors
    values = {"title": title, "header": header,
              "ann_note_tier": ann_note_tier, "primary_color": primary_color,
              "ann_highlight_color": ann_highlight_color,
              "filter_match_color": filter_match_color}

    for option, (pattern, value_format) in PAGE_OPTIONS.items():
        value = values[option]
        if value_format == "js":
            value = js_value(value)
        out = write_template_option(pattern, f'{value};', out)

    # Header logos
    out = write_template_option(LOGOS_PATTERN,
                                f'{js_value(header_logos)};',
                                out)

    # Help and licence texts: from the Markdown files, or kept from an
    # existing page
    for option, md_file in [("help_file", help_file),
                            ("licence_file", licence_file)]:
        pattern = INFO_TEXT_PATTERNS[option][0]
        if md_file and Path(md_file).is_file():
            out = insert_template_md(md_file, pattern, out)
        elif kept_texts and option in kept_texts:
            out = write_template_option(pattern, f'{kept_texts[option]};',
                                        out)

    return out

# ======================== Reading an existing page ===========================

# Page options: the settings of the page itself. Each is written on a line
# of its own in the template, matched by the pattern, as a JavaScript value
# ("js") or a CSS color ("css"). The same table is used to read them back
# from an existing page
PAGE_OPTIONS = {
    # option                 pattern in the template                format
    "title":               (r"^(.*const pageTitle = ).*$",          "js"),
    "header":              (r"^(.*const pageHeader = ).*$",         "js"),
    "ann_note_tier":       (r"^(.*const annNoteTier = ).*$",        "js"),
    "primary_color":       (r"^(.*--primary-color: ).*$",           "css"),
    "ann_highlight_color": (r"^(.*--ann-highlight-color: ).*$",     "css"),
    "filter_match_color":  (r"^(.*--filter-match-color: ).*$",      "css"),
}

# Info sections: the informational parts of the page (help text, licence
# text and logos), from the optional files. The logos are a
# JavaScript list on one line. The help and licence texts are JavaScript
# template literals, `...`, over several lines (backticks in them are
# escaped as \`), so they are written with one pattern and read back with
# another, which matches the whole literal
LOGOS_PATTERN = r"^(.*const headerLogos = ).*$"
INFO_TEXT_PATTERNS = {
    # option: (pattern to write it, pattern to read it back)
    "help_file": (r"^(.*helpHTML = ).*$",
                  r"helpHTML = (`(?:\\.|[^`\\])*`)"),
    "licence_file": (r"^(.*licenceHTML = ).*$",
                     r"licenceHTML = (`(?:\\.|[^`\\])*`)"),
}

def normalize_color(color):
    """
    Write a hex color in one way, so that colors can be compared

    E.g. "#F00", "#f00" and "#FF0000" all become "#ff0000".

    Returns:
        str: the color as "#rrggbb" in lower case, or None if it's not a hex
        color (e.g. a color name like "red")
    """
    color = color.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", color):
        return "#" + "".join(c * 2 for c in color[1:])
    if re.fullmatch(r"#[0-9a-f]{6}", color):
        return color
    return None
    
    
def get_TrACE_file(output_dir, final_dir="TrACE"):
    """Path of the TrACE page in an output folder"""
    return Path(output_dir).joinpath(final_dir, "TrACE.html")


def read_TrACE_file(html_file):
    """
    The text of an existing TrACE page, or None if there is no page yet or
    it can't be read
    """
    if not Path(html_file).is_file():
        return None
        
    try:
        with open(Path(html_file), "r", newline="", encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        # E.g. no permission to read it, or not saved as UTF-8
        return None


def read_TrACE_options(html_file):
    """
    Read the page options (title, colors, ...) from an existing TrACE page

    Options that can't be found are left out. Same for those that can't be
    read (e.g. after a hand edit which broke the line, or a color written
    as a name), with a warning. Colors are normalized (see
    `normalize_color()`).

    Args:
        html_file: path to the TrACE page

    Returns:
        dict: option name -> value; empty if the page doesn't exist
    """
    text = read_TrACE_file(html_file)
    if text is None:
        return {}

    options = {}
    for option, (pattern, value_format) in PAGE_OPTIONS.items():
        raw = read_template_option(pattern, text)
        if raw is None:
            continue

        if value_format == "js":
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = None
            if not isinstance(value, str):
                value = None
        else:
            value = normalize_color(raw)

        if value is None:
            logger.warning(f"Could not read the {option} from {html_file}: "
                           f"{raw}")
        else:
            options[option] = value

    return options


def read_TrACE_info_sections(html_file):
    """
    Read the info sections (help text, licence text and logos) of an
    existing TrACE page

    They are kept when a page is created again without the files they came
    from (see `keep_existing_info_section()`).

    Args:
        html_file: path to the TrACE page

    Returns:
        dict with the info sections the page has, under the name of the
        option they come from: "help_file" and "licence_file" (the texts, as
        JavaScript literals ready to be inserted again), and "logos_file"
        (the list of logos); empty if the page doesn't exist
    """
    text = read_TrACE_file(html_file)
    if text is None:
        return {}

    info_sections = {}
    for option, (_, read_pattern) in INFO_TEXT_PATTERNS.items():
        match = re.search(read_pattern, text)
        # An empty literal means that the page has no such text
        if match and match.group(1) != "``":
            info_sections[option] = match.group(1)

    raw = read_template_option(LOGOS_PATTERN, text)
    if raw is not None:
        try:
            logos = json.loads(raw)
        except json.JSONDecodeError:
            logos = None
        if isinstance(logos, list) and logos:
            info_sections["logos_file"] = logos

    return info_sections


def keep_existing_info_section(what, file, existing_section):
    """
    Decide whether to keep an info section (help text, licence text or
    logos) of an existing page, and say so in the log

    Args:
        what: which info section it is, e.g. "help text"
        file: path to the file with the new section; None if not given, or
            an empty string to remove the section
        existing_section: the section in the existing page, or None

    Returns:
        bool: True if the section of the existing page should be kept
    """
    if not existing_section or file == "":
        return False

    if file is None:
        logger.info(f"Kept the {what} from the existing page")
        return True

    if not Path(file).is_file():
        logger.warning(f"File not found: {file}; kept the {what} from the "
                       "existing page")
        return True

    return False

# ======================== Settings of the last run ============================

# The settings of the last successful run are saved next to the TrACE folder,
# never inside it (that folder is published, and the settings contain paths
# on this computer), to fill in the next run
LAST_RUN_FILE = "TrACE_last_successful_run.json"

# Options saved, in two sections: the files, and a backup of the page
# options (which are read from the page itself, when there is one). The
# output folder is where the file is, and the processing steps are chosen
# for each run
FILEPATH_OPTIONS = ["audio_dir", "elan_dir", "speakers_info_file",
                    "recordings_info_file", "help_file", "licence_file",
                    "logos_file"]
                
SAVED_OPTIONS = FILEPATH_OPTIONS + list(PAGE_OPTIONS)


def read_last_run(output_dir):
    """
    Read the settings of the last successful run in an output folder

    Args:
        output_dir: the output folder (which contains the TrACE folder)

    Returns:
        dict: option name -> value (a string, or None); empty if there are
        no saved settings, or they can't be read (with a warning)
    """
    path = Path(output_dir).joinpath(LAST_RUN_FILE)
    if not path.is_file():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.warning(f"Could not read {path}, so it is not used: {e}")
        return {}

    # The file may have been edited by hand, so anything unexpected in it is
    # ignored rather than trusted
    if not isinstance(data, dict):
        return {}

    # Combine the two sections, "files" and "page_backup", into one dict
    settings = {}
    for section in ["files", "page_backup"]:
        values = data.get(section)
        if isinstance(values, dict):
            settings.update(values)

    # Keep only known options, with a text value or None (a file that was
    # not given)
    usable = {}
    for option, value in settings.items():
        if option not in SAVED_OPTIONS:
            continue
        if value is None or isinstance(value, str):
            usable[option] = value

    return usable


def save_last_run(output_dir, settings):
    """
    Save the settings of a successful run in the output folder

    Args:
        output_dir: the output folder (which contains the TrACE folder)
        settings: dict with the values of SAVED_OPTIONS
    """
    path = Path(output_dir).joinpath(LAST_RUN_FILE)
    data = {
        "about": ("Settings of the last successful run of TrACE "
                  "preparation, used to fill in the next run. This file is "
                  "not part of the TrACE folder: it contains paths on this "
                  "computer, so don't publish it."),
        "files": {option: settings.get(option) for option in FILEPATH_OPTIONS},
        "page_backup": {
            "about": ("A copy of the page's title, header, notes tier and "
                      "colors. They are only used when there is no TrACE "
                      "page yet; otherwise they are read from the page."),
            **{option: settings.get(option) for option in PAGE_OPTIONS},
        },
    }
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    except OSError as e:
        logger.warning(f"Could not save the settings to {path}: {e}")


def read_previous_settings(output_dir, final_dir="TrACE"):
    """
    Settings to start a new run from

    The page options (title, colors, ...) come from the existing TrACE page,
    so that they show what the page has now, even if someone else updated
    it. The locations of the files come from the settings of the last
    successful run in the output folder, since they can't be read from the
    page; so do the page options if there is no page yet (or a value can't
    be read from it).

    Args:
        output_dir: the output folder (which contains the TrACE folder)
        final_dir: name of the TrACE folder

    Returns:
        tuple: the settings (dict: option name -> value), and where each
        comes from (dict: option name -> "the existing page" or
        LAST_RUN_FILE)
    """
    last_run = read_last_run(output_dir)
    TrACE_options = read_TrACE_options(get_TrACE_file(output_dir, final_dir))

    settings, origins = {}, {}
    for option in SAVED_OPTIONS:
        if option in TrACE_options:
            settings[option] = TrACE_options[option]
            origins[option] = "the existing page"
        elif option in last_run:
            settings[option] = last_run[option]
            origins[option] = LAST_RUN_FILE

    return settings, origins

# ======================== Edited page detection ===============================


def fingerprint(text):
    """A short hash of the text"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def add_fingerprint(html):
    """Add the fingerprint of a generated page to its end"""
    return (f"{html}\n<!-- Generated by TrACE preparation; "
            f"fingerprint: {fingerprint(html)} -->\n")

def may_have_hand_edits(html_file):
    """
    Whether a page may contain hand edits that shouldn't be overwritten
    unasked

    False if the page doesn't exist, or its fingerprint shows that it's
    unchanged since it was created. True if it was changed, and also if
    that can't be told (the page can't be read, or has no fingerprint, e.g.
    because it was created by an older version), to be on the safe side
    """
    
    # The generated page ends with a fingerprint of its contents, so that later
    # runs can tell whether it was edited by hand, and avoid overwriting the 
    # edits
    FINGERPRINT_RE = re.compile(
        r"\n<!-- Generated by TrACE preparation; fingerprint: ([0-9a-f]{16}) -->\n\Z"
    )
    
    if not Path(html_file).is_file():
        return False

    text = read_TrACE_file(html_file)
    if text is None:
        return True

    match = FINGERPRINT_RE.search(text)
    if match is None:
        return True

    return fingerprint(text[:match.start()]) != match.group(1)

def backup_file(path):
    """Copy a file to 'name (backup YYYY-MM-DD).ext' next to it"""

    path = Path(path)
    stem = f"{path.stem} (backup {date.today().isoformat()})"
    backup = path.with_name(stem + path.suffix)
    n = 2
    while backup.exists():
        backup = path.with_name(f"{stem} {n}{path.suffix}")
        n += 1

    shutil.copy2(path, backup)
    return backup

# ======================== Validation functions ================================

class InvalidPaths(Exception):
    def __init__(self, message, paths):
        # Pass the message to the base Exception class
        super().__init__(message)
        # Store custom attributes
        self.paths = paths

def validate_paths(audio_dir, elan_dir, output_dir,
                   speakers_info_file, recordings_info_file,
                   copy_audio, generate_data, generate_html):
    
    paths_to_check = {}

    if copy_audio:
        paths_to_check["audio_dir"] = audio_dir

    if generate_data:
        paths_to_check["elan_dir"] = elan_dir
        paths_to_check["speakers_info_file"] = speakers_info_file
        paths_to_check["recordings_info_file"] = recordings_info_file

    invalid_paths = {}
    for name, path in paths_to_check.items():
        if (path is None) or (not Path(path).exists()):
            invalid_paths[name] = path

    if invalid_paths:
        invalid_paths_list = '\n\t'.join(f'{k}: {v}' for k, v in invalid_paths.items())
        message = ("Some of the required paths do not exist:\n\t" +
                   invalid_paths_list)
        raise InvalidPaths(message, invalid_paths)

# =================== Top level processing functions ===========================

def prepare_data(output_dir, elan_dir,
                 speakers_info_file, recordings_info_file,
                 ann_note_tier = ""):

    # Output files
    speakers_js_file = Path(output_dir).joinpath("speakers.js")
    transcripts_js_file = Path(output_dir).joinpath("transcripts.js")

    create_speakers_file(input_csv=speakers_info_file, 
                         output_js=speakers_js_file)

    create_transcripts_file(input_csv=recordings_info_file, 
                            output_js=transcripts_js_file, 
                            elan_dir=elan_dir,
                            ann_note_tier = ann_note_tier)

def create_TrACE_html(html_file, confirm_replace_callback, title, header,
                      ann_note_tier, primary_color, ann_highlight_color,
                      filter_match_color, help_file, licence_file, logos_file):
    """
    Create the TrACE page, without overwriting hand edits unasked

    Replacing a page with hand edits:

    + The callback is only called if the existing page may have hand edits
      (see `may_have_hand_edits()`), i.e. not for a new page, nor for a
      page that is unchanged since it was created. It is called once, with
      the path of the page.
    + If it returns True, the page is copied to a dated backup next to it
      (see `backup_file()`), and then replaced.
    + If it returns False, or no callback is given (None), the page is left
      as it is, and "kept" is returned. The data and audio are still
      updated by `do_processing()`.
    + The callback is the place to ask the user, or to tell them what
      happens: the GUI shows a dialog, with "Keep my page" as the default;
      the CLI replaces the page with --force_html, and otherwise prints how
      to replace it.

    The info sections (help, licence and logos) come from the given files.
    If a file is not given (None) or not found, the section of the existing
    page is kept; an empty string removes the section.

    Args:
        html_file: path to the page, TrACE.html
        confirm_replace_callback: function called with the path of a page
            that may have hand edits, before replacing it; returns True to
            replace it. None keeps such a page (see above)
        title ... logos_file: as for `do_processing()`

    Returns:
        tuple: what happened to the page ("created", "replaced" or "kept"),
        and the path of the backup of a replaced edited page, or None
    """
    html_existed = Path(html_file).exists()
    backup_path = None

    # Don't overwrite manual changes to the page without asking
    if may_have_hand_edits(html_file):
        if not (confirm_replace_callback and
                confirm_replace_callback(html_file)):
            logger.info("TrACE.html was changed since it was created, so "
                        "it was kept")
            return "kept", None
            
        backup_path = backup_file(html_file)
        logger.info(f"Edited page backed up to: {backup_path}")
    
    # Decide whether to keep existing info sections (help, licence, logos)
    info_sections = read_TrACE_info_sections(html_file) if html_existed else {}

    kept_texts = {}

    # Help text
    if keep_existing_info_section("help text", help_file,
                                  info_sections.get("help_file")):
        kept_texts["help_file"] = info_sections["help_file"]
    
    # Licence text
    if keep_existing_info_section("licence text", licence_file,
                                  info_sections.get("licence_file")):
        kept_texts["licence_file"] = info_sections["licence_file"]

    # Logos
    if keep_existing_info_section("logos", logos_file,
                                  info_sections.get("logos_file")):
        header_logos = info_sections["logos_file"]
    else:
        # Invalid logos are reported in the log and skipped
        header_logos = read_logos(logos_file)

    html = render_template(decode_template(),
                           title = title,
                           header = header,
                           ann_note_tier = ann_note_tier,
                           primary_color = primary_color,
                           ann_highlight_color = ann_highlight_color,
                           filter_match_color = filter_match_color,
                           help_file = help_file,
                           licence_file = licence_file,
                           header_logos = header_logos,
                           kept_texts = kept_texts)

    # Add fingerprint -- it will later tell whether the page was edited
    with open(html_file, "w", newline="", encoding="utf-8") as f:
        f.write(add_fingerprint(html))

    return ("replaced" if html_existed else "created"), backup_path

def do_processing(audio_dir, elan_dir, output_dir,
                  speakers_info_file, recordings_info_file,
                  title, header, ann_note_tier, primary_color,
                  ann_highlight_color, filter_match_color,
                  help_file, licence_file, logos_file,
                  copy_audio, generate_data, generate_html,
                  report_callback, confirm_replace_callback=None,
                  final_dir = "TrACE"):
    """
    Prepare all TrACE files

    If TrACE.html may have hand edits, it is only replaced if
    confirm_replace_callback(path) returns True (a backup is kept then);
    see `create_TrACE_html()`.

    Returns:
        dict: output_dir; html: "created", "replaced", "kept" or
        "skipped"; backup: path of the backup of the replaced page, or
        None. The settings of a successful run are saved in
        LAST_RUN_FILE, next to the TrACE folder.

        None if processing stopped because of a problem (invalid
        input paths, or audio files that couldn't be copied); the problem
        is passed to report_callback().
    """

    logger.info("Started preparing TrACE data")

    try:
        validate_paths(audio_dir, elan_dir, output_dir,
                       speakers_info_file, recordings_info_file,
                       copy_audio, generate_data, generate_html)

    except InvalidPaths as e:
        logger.error("Some of the required input paths do not exist")
        report_callback(e)
        return

    output_root = Path(output_dir)
    output_dir = output_root.joinpath(final_dir)

    # Create output dir if not exists
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")

    result = {"output_dir": output_dir, "html": "skipped", "backup": None}

    if copy_audio:
        logger.info("Started copying audio files")
        audio_target_dir = output_dir.joinpath("audio")

        if not audio_target_dir.exists():
            audio_target_dir.mkdir(exist_ok=True)
            logger.info(f"Created output audio directory: {audio_target_dir}")

        # If some files can't be copied (e.g. the disk is full), stop: the
        # TrACE folder could otherwise keep old versions of them unnoticed
        try:
            shutil.copytree(audio_dir, audio_target_dir, dirs_exist_ok=True)
            logger.info("Successfully copied audio")
        except shutil.Error as e:
            # copytree() copies what it can, then lists the files that failed
            failed = [f"{Path(source).name}: {reason}"
                      for source, target, reason in e.args[0]]
            message = ("Some audio files could not be copied, so the TrACE "
                       "folder may contain old versions of them or none at "
                       "all:\n\t" + "\n\t".join(failed[:10]))
            if len(failed) > 10:
                message += f"\n\t... and {len(failed) - 10} more"
            logger.error("Some audio files could not be copied")
            report_callback(message)
            return
        except OSError as e:
            logger.error("The audio files could not be copied")
            report_callback(f"The audio files could not be copied: {e}")
            return


    if generate_data:
        logger.info("Started generating data")
        prepare_data(output_dir, 
                     elan_dir=elan_dir,
                     speakers_info_file=speakers_info_file,
                     recordings_info_file=recordings_info_file,
                     ann_note_tier = ann_note_tier
                     )
        logger.info("Successfully generated data")

    if generate_html:
        result["html"], result["backup"] = create_TrACE_html(
            get_TrACE_file(output_root, final_dir),
            confirm_replace_callback=confirm_replace_callback,
            title=title,
            header=header,
            ann_note_tier=ann_note_tier,
            primary_color=primary_color,
            ann_highlight_color=ann_highlight_color,
            filter_match_color=filter_match_color,
            help_file=help_file,
            licence_file=licence_file,
            logos_file=logos_file)

    # Remember the settings of this run, to fill in the next one. Paths are
    # saved in full, so that they don't depend on the current folder
    settings = {"audio_dir": audio_dir, "elan_dir": elan_dir,
                "speakers_info_file": speakers_info_file,
                "recordings_info_file": recordings_info_file,
                "help_file": help_file, "licence_file": licence_file,
                "logos_file": logos_file, "title": title, "header": header,
                "ann_note_tier": ann_note_tier,
                "primary_color": primary_color,
                "ann_highlight_color": ann_highlight_color,
                "filter_match_color": filter_match_color}
                
    for option in FILEPATH_OPTIONS:
        if settings[option]:
            settings[option] = str(Path(settings[option]).resolve())
            
    save_last_run(output_root, settings)

    return result
