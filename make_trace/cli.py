import argparse
import logging
import textwrap
from pathlib import Path

from constants import DEFAULTS, HELP_STRINGS
from processing import (do_processing, get_TrACE_file,
                        read_TrACE_info_sections, read_previous_settings,
                        LAST_RUN_FILE, SAVED_OPTIONS)


# Wrap the help text and print defalut values in the CLI help message
class CustomWidthFormatter(argparse.RawDescriptionHelpFormatter):
    def _fill_text(self, text, width, indent):
            # This handles the main header description text
            formatted_lines = []
            for line in text.splitlines():
                if line.strip() == "":
                    formatted_lines.append("")
                else:
                    wrapped = textwrap.wrap(line, width=80 - len(indent))
                    formatted_lines.extend(wrapped)
            return "".join(indent + line + "\n" for line in formatted_lines).rstrip("\n")

    def _split_lines(self, text, width):
        # This handles the argument help texts
        formatted_lines = []
        for line in text.splitlines():
            if line.strip() == "":
                formatted_lines.append("")
            else:
                # Wrap each line of the variable description to fit the width
                wrapped = textwrap.wrap(line, width=80)
                formatted_lines.extend(wrapped)
        return formatted_lines

parser = argparse.ArgumentParser(
    description=(
        "Transcribed Audio Collection Explorer (TrACE) preparation script" +
        "\n\n" +
        "A script to prepare audio data with transcripts for viewing in an " +
        "HTML interface. "+
        "To launch a graphical user interface, run the script " +
        "without any parameters." +
        "\n\n" +
        "Page options (title, header, notes tier and colors) that are " +
        "not given are taken from the existing TrACE page. Files that are " +
        "not given are taken from the last successful run with the same " +
        "output folder (saved in " + LAST_RUN_FILE + ", next to the TrACE " +
        "folder)."
    ),
    add_help=True,
    formatter_class=CustomWidthFormatter
    )

# Add parser arguments

data_group = parser.add_argument_group(
    "Data files",
    description=("These arguments specify files needed to produce the data " +
                 "for TrACE.")
    )

data_group.add_argument("-a", "--audio_dir",
                        dest="audio_dir",
                        type=Path,
                        metavar="",
                        help=(HELP_STRINGS["audio_dir"] + 
                              "\n  Default: as in the last run")
                        )

data_group.add_argument("-e", "--elan_dir",
                        dest="elan_dir",
                        type=Path,
                        metavar="",
                        help=(HELP_STRINGS["elan_dir"] + 
                              "\n  Default: as in the last run")
                        )

data_group.add_argument("-s", "--speaker_info",
                        dest="speakers_info_file",
                        type=Path,
                        metavar="",
                        help=(HELP_STRINGS["speakers_info_file"] + 
                              "\n  Default: as in the last run")
                        )

data_group.add_argument("-r", "--recordings_info",
                        dest="recordings_info_file",
                        type=Path,
                        metavar="",
                        help=(HELP_STRINGS["recordings_info_file"] + 
                              "\n  Default: as in the last run")
                        )

data_group.add_argument("-o", "--output_dir",
                        dest="output_dir",
                        type=Path,
                        metavar="",
                        default=DEFAULTS["output_dir"],
                        help=(HELP_STRINGS["output_dir"] + 
                              f"\n  Default: {DEFAULTS['output_dir']}")
                        )

template_group = parser.add_argument_group(
    "Template Settings",
    description="These arguments configure the output HTML file."
    )

template_group.add_argument("--title",
                            dest="title",
                            type=str,
                            metavar="",
                            default=None,
                            help=(HELP_STRINGS["title"] + 
                                  f"\n  Default: as in the existing page, or {DEFAULTS['title']}")
                            )

template_group.add_argument("--header",
                            dest="header",
                            type=str,
                            metavar="",
                            default=None,
                            help=(HELP_STRINGS["header"] + 
                                  f"\n  Default: as in the existing page, or {DEFAULTS['header']}")
                            )

template_group.add_argument("--ann_note_tier",
                            dest="ann_note_tier",
                            type=str,
                            metavar="",
                            default=None,
                            help=(HELP_STRINGS["ann_note_tier"] + 
                                  f"\n  Default: as in the existing page, or {DEFAULTS['ann_note_tier']}")
                            )

template_group.add_argument("--primary_color",
                            dest="primary_color",
                            type=str,
                            metavar="",
                            default=None,
                            help=(HELP_STRINGS["primary_color"] + 
                                  f"\n  Default: as in the existing page, or {DEFAULTS['primary_color']}")
                            )

template_group.add_argument("--ann_highlight_color",
                            dest="ann_highlight_color",
                            type=str,
                            metavar="",
                            default=None,
                            help=(HELP_STRINGS["ann_highlight_color"] + 
                                f"\n  Default: as in the existing page, or {DEFAULTS['ann_highlight_color']}")
                            )

template_group.add_argument("--filter_match_color",
                            dest="filter_match_color",
                            type=str,
                            metavar="",
                            default=None,
                            help=(HELP_STRINGS["filter_match_color"] + 
                                f"\n  Default: as in the existing page, or {DEFAULTS['filter_match_color']}\n")
                            )

# The info sections (help, licence and logos) are kept from an existing
# page, unless a file is given (see processing.create_page())
KEPT_SECTION_HELP = ("\n  Default: kept from the existing TrACE page, if " +
                     "any. Give an empty value (\"\") to remove it.\n")

template_group.add_argument("--help_file",
                            dest="help_file",
                            # Not Path: Path("") would turn into "."
                            type=str,
                            metavar="",
                            help=(HELP_STRINGS["help_file"] + 
                                  KEPT_SECTION_HELP)
                            )

template_group.add_argument("--licence_file",
                            dest="licence_file",
                            # Not Path: Path("") would turn into "."
                            type=str,
                            metavar="",
                            help=(HELP_STRINGS["licence_file"] + 
                                  KEPT_SECTION_HELP)
                            )

template_group.add_argument("--logos_file",
                            dest="logos_file",
                            # Not Path: Path("") would turn into "."
                            type=str,
                            metavar="",
                            help=(HELP_STRINGS["logos_file"] + 
                                  KEPT_SECTION_HELP)
                            )

processing_group = parser.add_argument_group(
    "Processing Settings",
    description="These arguments allow to skip processing steps."
    )

processing_group.add_argument("--no_audio",
                              dest="copy_audio",
                              action="store_false",
                              help=("Do not copy audio from the input audio " +
                                    "to the TrACE audio folder (e.g., if the " +
                                    "audios have already been copied and " +
                                    "don't need to be updated).")
                             )

processing_group.add_argument("--no_data",
                              dest="generate_data",
                              action="store_false",
                              help="Do not re-create data."
                             )

# Replacing an edited page, or not touching the page at all: one or the
# other
html_group = processing_group.add_mutually_exclusive_group()

html_group.add_argument("--force_html",
                        dest="force_html",
                        action="store_true",
                        help=("Replace TrACE.html even if it was changed " +
                              "by hand since it was created (a backup copy " +
                              "is kept). Without this, an edited page is " +
                              "kept as it is.")
                        )

html_group.add_argument("--no_html",
                        dest="generate_html",
                        action="store_false",
                        help=("Leave TrACE.html completely untouched, and " +
                              "only update the audio and data. (Hand edits " +
                              "to the page are kept anyway, unless " +
                              "--force_html is given.)")
                        )


def run_cli():

    def report(message, type="info"):
        logging.error(message)

    # Parse arguments
    args = parser.parse_args()

    # Convert to dict to pass into the function in one go
    args_dict = vars(args)
    args_dict["report_callback"] = report

    # Options that are not given: page options from the existing page, and
    # files from the last successful run (see read_previous_settings()), or
    # else the defaults
    previous, origins = read_previous_settings(args_dict["output_dir"])

    reused = {}
    for option in SAVED_OPTIONS:
        if args_dict[option] is None:
            if previous.get(option) is not None:
                args_dict[option] = previous[option]
                reused.setdefault(origins[option], []).append(option)
            elif option in DEFAULTS:
                args_dict[option] = DEFAULTS[option]
    for origin, options in reused.items():
        print(f"Using settings from {origin}: {', '.join(options)}")

    # Whether to replace a TrACE page with hand edits: only with
    # --force_html. Without it, the page is kept, with a hint about the
    # option
    def keep_edited_page(html_file):
        print(f"{html_file.name} was changed since it was created, so it "
              "was kept. To replace it (a backup will be kept), use "
              "--force_html.")
        return False

    if args_dict.pop("force_html"):
        args_dict["confirm_replace_callback"] = lambda html_file: True
    else:
        args_dict["confirm_replace_callback"] = keep_edited_page

    # Say which info sections of the existing page are kept
    if args_dict["generate_html"]:
        info_sections = read_TrACE_info_sections(
            get_TrACE_file(args_dict["output_dir"]))
        for option, what in [("help_file", "Help text"),
                             ("licence_file", "Licence text"),
                             ("logos_file", "Logos")]:
            if args_dict[option] is None and option in info_sections:
                print(f"{what}: kept from the existing page (use "
                      f"--{option} to replace it, or --{option} \"\" to "
                      "remove it)")
    do_processing(**args_dict)