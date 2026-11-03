HELP_STRINGS = {
    "audio_dir": 
        ("Path to the input audio directory. By default, files will be " + 
         "automatically copied into a subfolder within the output directory"),
    "elan_dir": 
        ("Path to the input directory with Elan files. They will only be " +
         "used to extract annotations and will not be included in the output"),
    "output_dir": 
        ("Path to the output directory. A subdirectory 'TrACE' will be " +
          "created within it, containing all the files for the interface"),
    "speakers_info_file": 
        ("Path to CSV file with speaker information. Each row corresponds to " +
         "a speaker. At least a column 'Name' should be present. All other " +
         "columns will be used as additonal speaker attributes to be " +
         "displayed in the speaker cards in the interface. Addtional " +
         "attributes can contain several values, separated by ';'.)"),
    "recordings_info_file": 
        ("Path to CSV file with recordings information. Each row corresponds " +
         "to a recording. Three columns should be present: 'audio_file' -- " +
         "name of the audio file within the audio folder; 'elan_file' -- " +
         "same for Elan file; 'display_name' -- name shown in the interface."),
    "title":
        "Page title (shown in the browser tab, when adding to bookmarks etc.)",
    "header": 
        "Interface header (shown at the top of the page)",
    "ann_note_tier":
        ("Name of the TIER_ID associated with notes/remarks in the " +
         "annotations. If such a tier exists, annotations from it will be " +
         "differently highlighted."),
    "primary_color": 
        "Main color of the interface",
    "ann_highlight_color": 
        "Highlight of the currently playing annotation",
    "filter_match_color":
        "Highlight for record buttons which match the current filters"
}

DEFAULTS = {
    "output_dir": ".",
    "title": "TrACE", 
    "header": "Transcribed Audio Collection Explorer (TrACE)", 
    "ann_note_tier": "NOTE", 
    "primary_color": "#228be6",
    "ann_highlight_color": "#faffa1",
    "filter_match_color": "#c2fad2" 
}