# TrACE

Transcribed Audio Collection Explorer (**TrACE**) is a simple web-interface for 
exploring audio recordings and associated transcripts. TrACE is built with HTML 
and JavaScript without any dependencies, and does not require internet access.

**Main features:**

+ Synchronized audio and transcripts
+ Transcript search
+ Filters: find recordings with a certain type of speakers 

**Demo:** https://precariousoralhistories.com/TrACE_demo/

## Overview

To create a TrACE, you need at least the following files:

+ `TrACE_template.html` contains the TrACE itself. You can open the file in 
any browser, as long as it has access to the data, as described below. You can
rename the file as needed.
+ Audio files
+ Two data files holding annotations and speakers information, see details
[below](#data-structure)

Data files have simple structure and can be created in any way you want. 
However, to facilitate TrACE packaging, we provide a `make_trace.pyz` script. 
It can be run both in a point-and-click mode, or as a command line program,
as described in the next section. 

## Creating new TrACE

### Starting example

`make_trace.pyz` requires Python 3.9 or later to run. Point-and-click mode 
requires Tcl/Tk, which is usually included with Python; if you don't have it, 
see [below]() on how to get it.

To build the example TrACE page, first download the data and the scripts, by 
running the following in the command line:

```sh
git clone https://github.com/Language-Research-Technology/TrACE
cd TrACE
```

Next, run `make_trace.pyz` to prepare TrACE. To use a point-and-click 
interface, run:

```sh
python make_trace.pyz
```

Use the interface to provide the following settings:

+ Audio folder: examples/audio
+ ELAN folder: examples/elan
+ Speakers CSV file: examples/speakers_info.csv
+ Recordings CSV file: examples/recordings_info.csv
+ Help file: examples/help_text.txt
+ Logos file: examples/logos.csv

Then click Run. A new TrACE folder will be created, holding all the 
necessary files. To open the interface, open the `TrACE.html` file inside that
folder.

Alternatively, all processing can be done from command line:

```sh
python make_trace.pyz \
        --audio_dir examples/audio \
        --elan_dir examples/elan \
        --speaker_info examples/speakers_info.csv \
        --recordings_info examples/recordings_info.csv \
        --help_file examples/help_text.txt \
        --logos_file examples/logos.csv \
        --output_dir .
```

### Re-running TrACE

`make_trace.pyz` tries to remember processing options that you used and will
re-use them if you don't provide new values to the script.

If a TrACE output folder exists, the script will read appearance options 
(described [below](#customising-the-interface)) from the existing TrACE HTML 
page.

Furthermore, it saves input file paths and appearance options to 
`TrACE_last_successful_run.json`. File paths will be re-used on the next re-run. 
Appearance options will be re-used if no existing TrACE page is found, e.g., if 
you have removed it.

### Processing options

Run `python make_trace.pyz -h` for a description of all processing options. In
the point-and-click interface, hover over fields and buttons to see their
description.

## Customising the interface

Some aspects of the interface appearance can be customized by providing options
to `make_trace.pyz`.

+ **Title**: page title as shown in the browser tab, bookmarks etc.
+ **Header**: main header of the page
+ **Colors**: 
    + Primary color of the interface (default: #228be6)
    + Highlight of the current annotation (default: #faffa1)
    + Highlight for the filter matches (default: #c2fad2)

### Licence and help files

You can provide custom licence and/or help files. You can write them in plain
text or in Markdown (see `examples/help_text.txt` for an example). If you 
include them, they can be opened with buttons in the top left corner of the 
screen.

Licence text will be shown once at the beginning of each session; users need
to click "Accept" to dismiss the message and start working with TrACE.

### Header logos

Logos of your project, partners or funders can be shown under the page header.
When preparing TrACE with `make_trace.pyz`, you can list them in a CSV file
(`--logos_file` in the command line, or "Logos CSV file" in the graphical 
interface). 

The CSV file needs to contain the folowing columns (see `examples/logos.csv` for
an example):

+ *image* -- path to the image file, relative to the CSV file. Supported 
    formats: PNG, JPEG, GIF, SVG, WebP.
+ *text* -- text to show instead of an image, for logos without an image
+ *url* -- page to open when the logo is clicked (optional)
+ *title* -- text shown when hovering the mouse over the logo (optional)

Each logo needs either an *image* or a *text* value. Logos are embedded 
into the HTML file, so they don't need to be copied together with it.

## Technical details

### Data structure

The interface assumes the existence of three data sources: 

+ Folder with audio files
+ `speakers.js` -- information about speakers
+ `transcripts.js` -- time-stamped transcripts

It is assumed that all of them are in the same folder with the TrACE HTML page.

#### speakers.js

The file should contain a Java Script constant named `speakers`. The constant
should hold a JSON list, where each element is a JSON dictionary holding info
about a single speaker. Each speaker should have at least one field "Name". 
Any other fields can have arbitrary names.

<details>
<summary><b>Show example</b></summary>

```
const speakers = [
  {
    "Name": "Dawn",
    "Gender": "Female",
    "Age Group": "36-50"
  },
  {
    "Name": "Dustin",
    "Gender": "Male",
    "Age Group": "66+"
  }
```
</details>

#### transcripts.js

The file should contain a Java Script constant named `transcripts`. The
constant should hold a JSON list, where each element is a JSON dictionary 
holding annotations for a single transcript. The dictionary should have the
following fields:

+ *filename* -- path to the audio file
+ *displayName* -- display name for the audio in the list of recordings
+ *speakers* -- a list of speakers present in the recording. Names of the speakers should match the names in the `speakers.js` file.
+ *annotations* -- a list of dictionaries, where each entry corresponds to a
    single annotation and contains the following fields:
    + *ANNOTATION_ID*
    + *TIER_ID* (contains a speaker's name)
    + *content* -- annotation text
    + *start* -- start timestamp in milliseconds
    + *end* -- end timestamp in milliseconds

<details>
<summary><b>Show example</b></summary>

```
const transcripts = [
  {
    "filename": "audio/Bwd1.mp3",
    "displayName": "Martha",
    "speakers": [
      "Martha"
    ],
    "annotations": [
      {
        "ANNOTATION_ID": "a1",
        "TIER_ID": "Martha",
        "content": "and when he got over there to find that they weren't there, it was like, oh my God.",
        "start": 0,
        "end": 4500
      },
      {
        "ANNOTATION_ID": "a2",
        "TIER_ID": "Martha",
        "content": "Where are they? What? We couldn't see where they'd been",
        "start": 4500,
        "end": 7220
      }
    ] 
  }
]
```
</details>

### Building make_trace.pyz

`make_trace.pyz` is an executable zip archive (see 
https://docs.python.org/3/library/zipapp.html). The code for it is stored in
the `make_trace` folder. 

To build `make_trace.pyz`, run `python build/package.py` in the repo 
directory. The HTML template is embedded directly into `make_trace.pyz` at this
step, so that the script can be used completely on its own to generate TrACE. 

## Credits

TrACE was created by Wolfgang Barth and Anton Malko, as part of
[LDaCA](https://www.ldaca.edu.au/) team at the Australian National University.
