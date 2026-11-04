import argparse
import textwrap
from pathlib import Path

from constants import DEFAULTS, HELP_STRINGS
from processing import do_processing


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
        "without any parameters."
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
                              "\n  Default: None")
                        )

data_group.add_argument("-e", "--elan_dir",
                        dest="elan_dir",
                        type=Path,
                        metavar="",
                        help=(HELP_STRINGS["elan_dir"] + 
                              "\n  Default: None")
                        )

data_group.add_argument("-s", "--speaker_info",
                        dest="speakers_info_file",
                        type=Path,
                        metavar="",
                        help=(HELP_STRINGS["speakers_info_file"] + 
                              "\n  Default: None")
                        )

data_group.add_argument("-r", "--recordings_info",
                        dest="recordings_info_file",
                        type=Path,
                        metavar="",
                        help=(HELP_STRINGS["recordings_info_file"] + 
                              "\n  Default: None")
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
                            default=DEFAULTS["title"],
                            help=(HELP_STRINGS["title"] + 
                                  f"\n  Default: {DEFAULTS['title']}")
                            )

template_group.add_argument("--header",
                            dest="header",
                            type=str,
                            metavar="",
                            default=DEFAULTS["header"],
                            help=(HELP_STRINGS["header"] + 
                                  f"\n  Default: {DEFAULTS['header']}")
                            )

template_group.add_argument("--ann_note_tier",
                            dest="ann_note_tier",
                            type=str,
                            metavar="",
                            default=DEFAULTS["ann_note_tier"],
                            help=(HELP_STRINGS["ann_note_tier"] + 
                                  f"\n  Default: {DEFAULTS['ann_note_tier']}")
                            )

template_group.add_argument("--primary_color",
                            dest="primary_color",
                            type=str,
                            metavar="",
                            default=DEFAULTS["primary_color"],
                            help=(HELP_STRINGS["primary_color"] + 
                                  f"\n  Default: {DEFAULTS['primary_color']}")
                            )

template_group.add_argument("--ann_highlight_color",
                            dest="ann_highlight_color",
                            type=str,
                            metavar="",
                            default=DEFAULTS["ann_highlight_color"],
                            help=(HELP_STRINGS["ann_highlight_color"] + 
                                f"\n  Default: {DEFAULTS['ann_highlight_color']}")
                            )

template_group.add_argument("--filter_match_color",
                            dest="filter_match_color",
                            type=str,
                            metavar="",
                            default=DEFAULTS["filter_match_color"],
                            help=(HELP_STRINGS["filter_match_color"] + 
                                f"\n  Default: {DEFAULTS['filter_match_color']}\n")
                            )

template_group.add_argument("--help_file",
                            dest="help_file",
                            type=Path,
                            metavar="",
                            help=(HELP_STRINGS["help_file"] + 
                                "\n  Default: None\n")
                            )

template_group.add_argument("--licence_file",
                            dest="licence_file",
                            type=Path,
                            metavar="",
                            help=(HELP_STRINGS["licence_file"] + 
                                "\n  Default: None\n")
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

processing_group.add_argument("--no_html",
                              dest="generate_html",
                              action="store_false", 
                              help=("Do not re-create TrACE HTML file from " +
                                    "scratch (e.g., if you made manual " +
                                    "changes to it that you want to preserve.")
                              )


def run_cli():

    def report(message, type="info"):
        logging.error(message)

    # Parse arguments
    args = parser.parse_args()

    # Convert to dict to pass into the function in one go
    args_dict = vars(args)
    args_dict["report_callback"] = report
    print(args_dict)
    do_processing(**args_dict)