# README

Transcribed Audio Collection Explorer (TrACE) is a simple web-interface for 
exploring audio recordings and associated transcripts, built with pure
HTML and JavaScript without any dependencies.

## Interface

All the code for the interface is contained in `TrACE_template.html`. You can
just open the file in any browser, as long it has access to the data as 
described below. You can also rename the file itself as needed.

Interface color and title can be changed by editing the values in the 
TEMPLATE VARIABLES section at the top of the file. Values which may be of the
immediate interest:

+ `pageHeader` -- header at the top of the page
+ `annNoteTier` -- tierID associated with notes or remarks (as opposed to, for
    example, direct utterances by the speakers). Annotations in this tier will
    have a separate highlighting.
+ `--primary-color` -- color of the interface. Can be a valid color name or a 
    HEX string. Interface elements will be coloured with shades of this color.

## Data structure

The interface assumes the existence of three data sources: 

+ Folder with audio files
+ `speakers.js` -- information about speakers
+ `transcripts.js` -- time-stamped transcripts

It is assumed that all of them are in the same folder with 
`TrACE_template.html`.

### speakers

The file should contain a Java Script constant named `speakers`. The constant
should hold a JSON list, where each element is a JSON dictionary holding info
about a single speaker. Each speaker should have at least one field "Name". 
Any other fields can have arbitrary names.

See an example file in the examples folder.

### transcripts

The file should contain a Java Script constant named `transcripts`. The
constant should hold a JSON list, where each element is a JSON dictionary 
holding annotations for a single transcript. The dictionary should have the
following fields:

+ *filename* -- path to the audio file
+ *displayName* -- display name for the audio in the list of recordings
+ *speakers* -- a list of speakers present in the recording. Names of the spakers should match the names in the `speakers.js` file.
+ *annotations* -- a list of dictionaries, where each entry corresponds to a
    single annotation and contains the following fields:
    + *ANNOTATION_ID*
    + *TIER_ID* (contains a speaker's name)
    + *content* -- annotation text
    + *start* -- start timestamp in milliseconds
    + *end* -- end timestamp in milliseconds

See an example file in the examples folder.

## Header logos

Logos of your project, partners or funders can be shown under the page header.
When preparing TrACE with `make_trace`, you can list them in a CSV file
(`--logos_file` in the command line, or "Logos CSV file" in the graphical 
interface). Each row corresponds to one logo, shown from left to right:

```csv
image,text,url,title
logos/anu.png,,https://www.anu.edu.au/,Australian National University
,My Project,https://example.org/,
```

+ *image* -- path to the image file, relative to the CSV file. Supported 
    formats: PNG, JPEG, GIF, SVG, WebP.
+ *text* -- text to show instead of an image, for logos without an image
+ *url* -- page to open when the logo is clicked (optional)
+ *title* -- text shown when hovering the mouse over the logo (optional)

Each logo needs either an *image* or a *text*. Image files are embedded into
the HTML file, so they don't need to be copied together with it.

## Credits

TrACE was created by Wolfgang Barth and Anton Malko, as part of
[LDaCA](https://www.ldaca.edu.au/) team at the Australian National University.
