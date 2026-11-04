import base64
import csv
import json
import re
import shutil
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
import logging
from markdown2.markdown2 import Markdown

logger = logging.getLogger(__name__)

############################### HTML TEMPLATE ##################################

# The entire code of the template, compressed and encoded in base64. This makes
# the current script self-contained: it can just output this code as HTML, 
# optionally making adjustments to configurable parameters
TRACE_TEMPLATE = "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"

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

    with open(Path(input_csv), mode='r', encoding='utf-8') as file:
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


def create_transcripts_record(audio_file, elan_file, display_name):
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

    Returns:
        dict: a dictionary with three entries: path to audio file, display name,
        and a list with annotations as produced by `extract_elan_annotations()`
    """
    annotations = extract_elan_annotations(elan_file)

    return ({
        'filename': Path(audio_file).as_posix(),
        'displayName': display_name,
        'annotations': annotations
    })


def create_transcripts_file(input_csv, output_js, elan_dir):
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
    Returns:
        Nothing
    """
    logger.info("Generating tranhscripts data...")
    logger.info(f"Recordings information: {input_csv}")
    logger.info(f"ELAN folder: {elan_dir}")

    with open(Path(input_csv), mode='r', encoding='utf-8') as file:
        recordings_info = list(csv.DictReader(file))

    transcripts_data = []

    for row in recordings_info:
        relative_audio_path = Path("audio").joinpath(row["audio_file"])
        relative_elan_path = Path(elan_dir).joinpath(row["elan_file"])

        transcripts_data.append(create_transcripts_record(relative_audio_path, 
                                                          relative_elan_path, 
                                                          row["display_name"]))

    # Write to JS file
    with open(output_js, 'w', encoding='utf-8') as f:
        f.write('const transcripts = ')
        json.dump(transcripts_data, f, indent=2, ensure_ascii=False)
        f.write(';')

    logger.info(f"Transcripts data saved to: {output_js}")


def render_template(template_str, 
                    output_file,
                    title, 
                    header, 
                    ann_note_tier, 
                    primary_color,
                    ann_highlight_color,
                    filter_match_color, 
                    help_file,
                    licence_file):

    """
    Take an HTML template and replace configurable options with provided values

    Args:
        template_str: HTML template as a multi-line string
        output_file: file to save the final template to
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

    Returns:
        Nothing
    """

    out = template_str

    # Page title 
    out = re.sub('^(.*const pageTitle = ).*$', 
                 f'\\1"{title}"',
                 out,
                 flags=re.MULTILINE)

    # Interface header 
    out = re.sub('^(.*const pageHeader = ).*$', 
                 f'\\1"{header}"',
                 out,
                 flags=re.MULTILINE)

    # Note tier
    out = re.sub('^(.*const annNoteTier = ).*$', 
                 f'\\1"{ann_note_tier}"',
                 out,
                 flags=re.MULTILINE)

    # Main interface color
    out = re.sub('^(.*--primary-color: ).*$', 
                 f'\\1{primary_color};',
                 out,
                 flags=re.MULTILINE)

    # Annotation highlight color 
    out = re.sub('^(.*--ann-highlight-color: ).*$', 
                 f'\\1{ann_highlight_color};',
                 out,
                 flags=re.MULTILINE)

    # Filter match color
    out = re.sub('^(.*--filter-match-color: ).*$', 
                 f'\\1{filter_match_color};',
                 out,
                 flags=re.MULTILINE)

    # Help markdown text
    if help_file is not None and Path(help_file).is_file():

        with open(Path(help_file)) as f:
            help_text = f.read()

        md = Markdown()

        out = re.sub('^(.*helpHTML = `)`.*$', 
                    f'\\1{md.convert(help_text)}`;',
                    out,
                    flags=re.MULTILINE)

    # Licence markdown text
    if licence_file is not None and Path(licence_file).is_file():

        with open(Path(licence_file)) as f:
            licence_text = f.read()

        md = Markdown()

        out = re.sub('^(.*licenceHTML = `)`.*$', 
                    f'\\1{md.convert(licence_text)}`;',
                    out,
                    flags=re.MULTILINE)

    with open(Path(output_file), "w", newline="", encoding="utf-8") as f:
        f.write(out)

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

def prepare_html(output_file, title, header, ann_note_tier, primary_color,
                 ann_highlight_color, filter_match_color, help_file, 
                 licence_file):
    # Decode template
    TRACE_HTML = zlib.decompress(
        base64.b64decode(TRACE_TEMPLATE.encode("utf-8"))
    ).decode("utf-8")

    render_template(TRACE_HTML, 
                    output_file = output_file, 
                    title = title, 
                    header = header, 
                    ann_note_tier = ann_note_tier, 
                    primary_color = primary_color,
                    ann_highlight_color = ann_highlight_color,
                    filter_match_color = filter_match_color,
                    help_file = help_file,
                    licence_file = licence_file
                    )

def prepare_data(output_dir, elan_dir,
                 speakers_info_file, recordings_info_file):

    # Output files
    speakers_js_file = Path(output_dir).joinpath("speakers.js")
    transcripts_js_file = Path(output_dir).joinpath("transcripts.js")

    create_speakers_file(input_csv=speakers_info_file, 
                         output_js=speakers_js_file)

    create_transcripts_file(input_csv=recordings_info_file, 
                            output_js=transcripts_js_file, 
                            elan_dir=elan_dir)

def do_processing(audio_dir, elan_dir, output_dir,
                  speakers_info_file, recordings_info_file,
                  title, header, ann_note_tier, primary_color,
                  ann_highlight_color, filter_match_color,
                  help_file, licence_file,
                  copy_audio, generate_data, generate_html,
                  report_callback, final_dir = "TrACE"):

    logger.info("Started preparing TrACE data")

    try:
        validate_paths(audio_dir, elan_dir, output_dir,
                       speakers_info_file, recordings_info_file,
                       copy_audio, generate_data, generate_html)

    except InvalidPaths as e:
        logger.error("Some of the required input paths do not exist")
        report_callback(e)
        return

    output_dir = Path(output_dir).joinpath(final_dir)

    # Create output dir if not exists
    if not output_dir.exists:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")

    if copy_audio:
        logger.info("Started copying audio files")
        audio_target_dir = output_dir.joinpath("audio")

        if not audio_target_dir.exists:
            audio_target_dir.mkdir(exist_ok=True)
            logger.info(f"Created output audio directory: {audio_target_dir}")

        try:
            shutil.copytree(audio_dir, audio_target_dir, dirs_exist_ok=True)
            logger.info("Successfully copied audio")
        except Exception as e:
            logger.warning(f"Error while copying audio files: {e}")


    if generate_data:
        logger.info("Started generating data")
        prepare_data(output_dir, 
                     elan_dir=elan_dir,
                     speakers_info_file=speakers_info_file,
                     recordings_info_file=recordings_info_file
                     )
        logger.info("Successfully generated data")

    if generate_html:
        prepare_html(output_file = output_dir.joinpath("TrACE.html"), 
                     title = title, 
                     header = header, 
                     ann_note_tier = ann_note_tier, 
                     primary_color = primary_color,
                     ann_highlight_color = ann_highlight_color,
                     filter_match_color = filter_match_color,
                     help_file = help_file,
                     licence_file = licence_file)
