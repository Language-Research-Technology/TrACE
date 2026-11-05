import tkinter as tk
import tkinter.font as tkFont
from tkinter import colorchooser, filedialog, ttk
from pathlib import Path
import csv
import os

from constants import HELP_STRINGS, DEFAULTS
from processing import do_processing

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".opus"}
RECORDINGS_COLUMNS = ["audio_file", "elan_file", "display_name"]

# ------------------------------------------------------------------
# PATH CHECKS
#
# Each check returns a (status, info) tuple, where status is one of
# "ok", "warn" or "error", and info is a short text shown next to the path
# ------------------------------------------------------------------

def shorten_path(path, max_len=40):
    """Shorten a path from the left, keeping as many trailing parts as fit"""

    if len(path) <= max_len:
        return path

    parts = Path(path).parts
    tail = parts[-1]

    if len(tail) + 2 > max_len:
        return "…" + tail[-(max_len - 1):]

    for part in reversed(parts[1:-1]):
        candidate = os.path.join(part, tail)
        if len(candidate) + 2 > max_len:
            break
        tail = candidate

    return os.path.join("…", tail)

def plural(n, noun):
    return f"{n} {noun}{'' if n == 1 else 's'}"

def read_csv(path):
    """Read a CSV the same way processing does; return (columns, rows)"""

    with open(Path(path), mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        return (reader.fieldnames or []), rows

def check_folder(path, extensions, noun):
    folder = Path(path)
    if not folder.is_dir():
        return "error", "folder not found"

    n = sum(1 for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in extensions)
    if n == 0:
        return "warn", f"no {noun} files found"

    return "ok", plural(n, f"{noun} file")

def check_speakers(path):
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
    if not Path(path).is_file():
        return "error", "file not found"

    return "ok", ""

def check_output(path):
    if not Path(path).is_dir():
        return "error", "folder not found"

    if Path(path).joinpath("TrACE").is_dir():
        return "ok", "existing TrACE/ will be updated"

    return "ok", "TrACE/ will be created here"

def run_gui():

    def report(message, type="info"):
        tk.messagebox.showerror(type, message)

    def on_run(gui_vars):
        input_vars = {k:v.get() for k,v in gui_vars.items()}

        paths = ["audio_dir", "elan_dir", "output_dir", 
                 "speakers_info_file", "recordings_info_file",
                 "help_file", "licence_file", "logos_file"]
        for v in paths:
            if input_vars[v].strip() == "":
                input_vars[v] = None

        input_vars["report_callback"] = report

        do_processing(**input_vars)


    def browse_file(var, filetypes):
        """Select a file"""

        cur_value = var.get()

        if (cur_value and Path(cur_value).is_file()):
            initial_dir = Path(cur_value).parent
        else:
            initial_dir = Path.cwd()

        choice = filedialog.askopenfilename(title="Select File",
                                            filetypes=filetypes +
                                                [('All Files', '*.*')],
                                            initialdir=initial_dir)

        if choice:
            var.set(choice)

    def browse_folder(var):
        """Select a folder"""

        cur_value = var.get()
        if (cur_value and Path(cur_value).is_dir()):
            initial_dir = Path(cur_value)
        else:
            initial_dir = Path.cwd()


        choice = filedialog.askdirectory(title="Select Folder",
                                        initialdir=initial_dir
                                        )

        if choice:
            var.set(choice)

    def pick_color(color_var, button):
        """Open colour picker"""
        color = colorchooser.askcolor()[1]
        if color:
            color_var.set(color)
            button.configure(bg=color)

    # https://stackoverflow.com/questions/3221956/how-do-i-display-tooltips-in-tkinter
    class Tooltip:
        '''
        It creates a tooltip for a given widget as the mouse goes on it.

        see:

        http://stackoverflow.com/questions/3221956/
            what-is-the-simplest-way-to-make-tooltips-
            in-tkinter/36221216#36221216

        http://www.daniweb.com/programming/software-development/
            code/484591/a-tooltip-class-for-tkinter

        - Originally written by vegaseat on 2014.09.09.

        - Modified to include a delay time by Victor Zaccardo on 2016.03.25.

        - Modified
            - to correct extreme right and extreme bottom behavior,
            - to stay inside the screen whenever the tooltip might go out on
            the top but still the screen is higher than the tooltip,
            - to use the more flexible mouse positioning,
            - to add customizable background color, padding, waittime and
            wraplength on creation
        by Alberto Vassena on 2016.11.05.

        Tested on Ubuntu 16.04/16.10, running Python 3.5.2
        '''

        def __init__(self, widget,
                    *,
                    bg='#FFFFEA',
                    pad=(5, 3, 5, 3),
                    text='widget info',
                    waittime=400,
                    wraplength=250):

            self.waittime = waittime  # in miliseconds, originally 500
            self.wraplength = wraplength  # in pixels, originally 180
            self.widget = widget
            self.text = text
            self.widget.bind("<Enter>", self.onEnter)
            self.widget.bind("<Leave>", self.onLeave)
            self.widget.bind("<ButtonPress>", self.onLeave)
            self.bg = bg
            self.pad = pad
            self.id = None
            self.tw = None

        def onEnter(self, event=None):
            self.schedule()

        def onLeave(self, event=None):
            self.unschedule()
            self.hide()

        def schedule(self):
            self.unschedule()
            self.id = self.widget.after(self.waittime, self.show)

        def unschedule(self):
            id_ = self.id
            self.id = None
            if id_:
                self.widget.after_cancel(id_)

        def show(self):
            def tip_pos_calculator(widget, label,
                                *,
                                tip_delta=(10, 5), pad=(5, 3, 5, 3)):

                w = widget

                s_width, s_height = w.winfo_screenwidth(), w.winfo_screenheight()

                width, height = (pad[0] + label.winfo_reqwidth() + pad[2],
                                pad[1] + label.winfo_reqheight() + pad[3])

                mouse_x, mouse_y = w.winfo_pointerxy()

                x1, y1 = mouse_x + tip_delta[0], mouse_y + tip_delta[1]
                x2, y2 = x1 + width, y1 + height

                x_delta = x2 - s_width
                if x_delta < 0:
                    x_delta = 0
                y_delta = y2 - s_height
                if y_delta < 0:
                    y_delta = 0

                offscreen = (x_delta, y_delta) != (0, 0)

                if offscreen:

                    if x_delta:
                        x1 = mouse_x - tip_delta[0] - width

                    if y_delta:
                        y1 = mouse_y - tip_delta[1] - height

                offscreen_again = y1 < 0  # out on the top

                if offscreen_again:
                    # No further checks will be done.

                    # TIP:
                    # A further mod might automagically augment the
                    # wraplength when the tooltip is too high to be
                    # kept inside the screen.
                    y1 = 0

                return x1, y1

            bg = self.bg
            pad = self.pad
            widget = self.widget

            # creates a toplevel window
            self.tw = tk.Toplevel(widget)

            # Leaves only the label and removes the app window
            self.tw.wm_overrideredirect(True)

            win = tk.Frame(self.tw,
                        background=bg,
                        borderwidth=0)
            label = tk.Label(win,
                            text=self.text,
                            justify=tk.LEFT,
                            background=bg,
                            relief=tk.SOLID,
                            borderwidth=0,
                            wraplength=self.wraplength)

            label.grid(padx=(pad[0], pad[2]),
                    pady=(pad[1], pad[3]),
                    sticky=tk.NSEW)
            win.grid()

            x, y = tip_pos_calculator(widget, label)

            self.tw.wm_geometry("+%d+%d" % (x, y))

        def hide(self):
            tw = self.tw
            if tw:
                tw.destroy()
            self.tw = None

    def unfocus_entry(event):
        # Shift focus to the root window to clear the Entry cursor
        root.focus_set()

    # Overall config
    root = tk.Tk()
    gui_vars = {}

    root.title("TrACE preparation")
    root.geometry("950x600")
    root.minsize(950,600)

    default_font = tkFont.nametofont("TkDefaultFont")
    default_font.configure(size=10)

    style = ttk.Style()
    style.theme_use('clam') 

    bg_color = "#f5f6f8"

    root.configure(bg=bg_color)
    style.configure(".", background=bg_color)

    style.configure(
        "Custom.TLabelframe", 
        # background="lightgray", 
        bordercolor="navyblue", 
        borderwidth=4,
    )

    style.configure("Custom.TLabelframe.Label", foreground="navyblue")

    style.configure(
        'Small.TButton', 
        padding=(6, 0), 
        focusthickness=0,
        focuscolor=bg_color
    ) 

    style.configure(
        "Custom.TButton", 
        focusthickness=0,
        focuscolor=bg_color
    ) 

    style.configure("TCheckbutton", focuscolor=bg_color)

    # Main layout
    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill="both", expand=True)

    # Labelled groups
    paths_frame = ttk.LabelFrame(
        main_frame,
        text="1. Input files",
        padding=10,
        style="Custom.TLabelframe"
    )

    options_frame = ttk.LabelFrame(
        main_frame,
        text="2. TrACE HTML options",
        padding=10,
        style="Custom.TLabelframe"
    )

    outputs_frame = ttk.LabelFrame(
        main_frame,
        text="3. Output options",
        padding=10,
        style="Custom.TLabelframe"
    )

    paths_frame.grid(
        row=0,
        column=0,
        sticky="nsew",
        padx=(10, 10),
        pady=(10, 10)
    )

    options_frame.grid(
        row=1,
        column=0,
        sticky="nsew",
        padx=(10, 10),
        pady=(10, 10)
    )

    outputs_frame.grid(
        row=2,
        column=0,
        sticky="nsew",
        padx=(10, 10),
        pady=(10, 10)
    )

    main_frame.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # FILE SELECTORS
    # ------------------------------------------------------------------

    # Names of the vars here and below match names of the main processing
    # function, so that they can be easily unpacked later
    #
    # Each path is shown as a read-only checklist row:
    #   status icon | label | path (click to choose) | info | [remove]
    #
    # Only problems are coloured; rows that are fine stay quiet

    csv_types = [('CSV Files', '*.csv')]
    md_types = [('Markdown Files', '*.md'), ('Text Files', '*.txt')]

    status_icons = {
        "ok": ("✓", "#adb5bd"),
        "warn": ("!", "#e67700"),
        "error": ("✗", "#c92a2a"),
    }
    muted_color = "#868e96"
    link_color = "#1c6fc4"
    label_minsize = 160

    bold_font = default_font.copy()
    bold_font.configure(weight="bold")
    underline_font = default_font.copy()
    underline_font.configure(underline=True)

    def check_path(var_name, value):
        if var_name == "audio_dir":
            return check_folder(value, AUDIO_EXTENSIONS, "audio")
        if var_name == "elan_dir":
            return check_folder(value, {".eaf"}, "ELAN")
        if var_name == "speakers_info_file":
            return check_speakers(value)
        if var_name == "recordings_info_file":
            return check_recordings(value, gui_vars["audio_dir"].get(),
                                    gui_vars["elan_dir"].get())
        if var_name == "output_dir":
            return check_output(value)
        return check_markdown(value)

    path_rows = {}

    # Filled in when the Run button is created at the bottom
    run_controls = {}

    def refresh_paths(*args):
        # All rows are refreshed together, since the recordings check
        # depends on the audio and ELAN folders
        missing = []
        has_errors = False

        for var_name, row in path_rows.items():
            value = gui_vars[var_name].get().strip()
            noun = "folder" if row["filetypes"] is None else "file"

            if value:
                status, info = check_path(var_name, value)
                full_path = str(Path(value).resolve())
                row["path"].configure(text=shorten_path(full_path),
                                      foreground="")
                row["path_tip"].text = (f"{full_path}\n\n" +
                                        f"Click to choose a different {noun}")
                icon, color = status_icons[status]
                row["icon"].configure(text=icon, foreground=color)
                row["info"].configure(
                    text=info,
                    foreground=muted_color if status == "ok" else color
                )
                has_errors = has_errors or status == "error"
            else:
                row["path"].configure(text="Choose…", foreground=link_color)
                row["path_tip"].text = f"Click to choose a {noun}"
                row["icon"].configure(text="")
                row["info"].configure(text="")
                if row["required"]:
                    # Lowercase "Audio folder", but not "ELAN folder"
                    label = row["label"]
                    if not label[:2].isupper():
                        label = label[0].lower() + label[1:]
                    missing.append(label)

            if "remove" in row:
                if value:
                    row["remove"].grid()
                else:
                    row["remove"].grid_remove()

        if "button" not in run_controls:
            return

        if missing:
            if len(missing) > 1:
                missing = [", ".join(missing[:-1]), missing[-1]]
            hint = f"To continue, choose the {' and '.join(missing)}."
        elif has_errors:
            hint = "To continue, fix the problems marked ✗."
        else:
            hint = "Tip: hover over any name for an explanation."

        run_controls["hint"].configure(text=hint)
        run_controls["button"].state(
            ["disabled"] if (missing or has_errors) else ["!disabled"]
        )

    def add_path_row(parent, i, var_name, label_text, filetypes, required):
        """Add a checklist row for one path to a grid in `parent`"""

        if (var_name == "output_dir"):
            var = tk.StringVar(value=DEFAULTS[var_name])
        else:
            var = tk.StringVar()

        gui_vars[var_name] = var
        row = {"label": label_text, "filetypes": filetypes,
               "required": required}

        row["icon"] = ttk.Label(parent, width=2, font=bold_font,
                                anchor="center")
        row["icon"].grid(row=i, column=0, pady=2)

        label = ttk.Label(parent, text=label_text)
        label.grid(row=i, column=1, sticky="w", padx=(0, 10), pady=2)
        Tooltip(label, text=HELP_STRINGS[var_name], waittime=50)

        if filetypes is None:
            command = lambda v=var: browse_folder(v)
        else:
            command = lambda v=var, t=filetypes: browse_file(v, t)

        # The path itself works as a link that opens the file dialog
        row["path"] = ttk.Label(parent, cursor="hand2", font=default_font)
        row["path"].grid(row=i, column=2, sticky="w", padx=5, pady=2)
        row["path_tip"] = Tooltip(row["path"], text="", waittime=300)
        # add="+" keeps the tooltip's own bindings
        row["path"].bind("<Enter>",
                         lambda e: e.widget.configure(font=underline_font),
                         add="+")
        row["path"].bind("<Leave>",
                         lambda e: e.widget.configure(font=default_font),
                         add="+")
        row["path"].bind("<Button-1>", lambda e, c=command: c(), add="+")

        row["info"] = ttk.Label(parent)
        row["info"].grid(row=i, column=3, sticky="w", padx=5, pady=2)

        if not required:
            row["remove"] = ttk.Label(parent, text="✕", cursor="hand2",
                                      foreground=muted_color)
            row["remove"].grid(row=i, column=4, sticky="e", padx=5, pady=2)
            row["remove"].bind("<Button-1>", lambda e, v=var: v.set(""))
            Tooltip(row["remove"], text="Remove", waittime=50)

        path_rows[var_name] = row
        var.trace_add("write", refresh_paths)

    def configure_path_columns(parent):
        parent.columnconfigure(1, minsize=label_minsize)
        parent.columnconfigure(3, weight=1)

    for i, spec in enumerate([
        ("audio_dir", "Audio folder", None, True),
        ("elan_dir", "ELAN folder", None, True),
        ("speakers_info_file", "Speakers CSV file", csv_types, True),
        ("recordings_info_file", "Recordings CSV file", csv_types, True),
    ]):
        add_path_row(paths_frame, i, *spec)

    ttk.Label(
        paths_frame,
        text="Optional",
        foreground=muted_color
    ).grid(row=4, column=1, sticky="w", pady=(10, 2))

    for i, spec in enumerate([
        ("help_file", "Help file", md_types, False),
        ("licence_file", "Licence file", md_types, False),
        ("logos_file", "Logos CSV file", csv_types, False),
    ]):
        add_path_row(paths_frame, 5 + i, *spec)

    configure_path_columns(paths_frame)

    # ------------------------------------------------------------------
    # HTML CONFIGURATION OPTIONS
    # ------------------------------------------------------------------
    
    # TITLES

    titles_frame = ttk.Frame(options_frame, height=150)
    titles_frame.grid(row=0, column=0, sticky="w", pady=5)

    text_vars = ["title", "header", "ann_note_tier"]
    text_labels = ["TrACE browser title", "TrACE header", "Notes tier in ELAN"]
    text_tooltips = [
        HELP_STRINGS["title"], 
        HELP_STRINGS["header"], 
        HELP_STRINGS["ann_note_tier"]
        ]

    text_defaults = [
        DEFAULTS["title"], 
        DEFAULTS["header"],
        DEFAULTS["ann_note_tier"]
        ]

    for i, var_name in enumerate(text_vars):
        label = ttk.Label(titles_frame, text=text_labels[i])
        label.grid(
            row=i, column=0, sticky="w", pady=5
        )
        Tooltip(label, text=text_tooltips[i], waittime=50)

        var = tk.StringVar()
        gui_vars[var_name] = var

        entry = ttk.Entry(
            titles_frame,
            textvariable=var,
            width=60
        )
        entry.grid(row=i, column=1, pady=5, padx=5)
        # Unfocus on Enter key
        entry.bind("<Return>", unfocus_entry)

        # Default values
        entry.insert(0, text_defaults[i])

    # VERTICAL LINE
    vertical_line = ttk.Separator(options_frame, orient=tk.VERTICAL)
    vertical_line.grid(row=0, column=2, sticky="ns", padx=15, pady=10)

    # COLOR PICKERS
    color_frame = ttk.Frame(options_frame, height=150)
    color_frame.grid(row=0, column=3, sticky="w", pady=5)

    colour_vars = ["primary_color", "ann_highlight_color", "filter_match_color"]
    color_labels = ["Primary interface color", "Current annotation color", 
                    "Filter match color"]
    color_tooltips = [
        HELP_STRINGS["primary_color"], 
        HELP_STRINGS["ann_highlight_color"],
        HELP_STRINGS["filter_match_color"]
        ]
    default_colors = [
        DEFAULTS["primary_color"], 
        DEFAULTS["ann_highlight_color"],
        DEFAULTS["filter_match_color"]
    ]

    def update_square_from_text(var, square):
        hex_code = var.get().strip()
        if len(hex_code) == 7 and hex_code.startswith('#'):
            try:
                square.config(bg=hex_code)
            except tk.TclError:
                pass 

    def pick_colour(event, var, square):
        colour = colorchooser.askcolor(color=var.get())[1]
        if colour:
            var.set(colour)
            square.config(bg=colour)

    def reset_colors():
        for k in colour_vars:
            gui_vars[k].set(DEFAULTS[k])

    for i, var_name in enumerate(colour_vars):

        label = ttk.Label(
            color_frame,
            text=color_labels[i]
        )
        label.grid(row=i, column=0, sticky="w", pady=5)
        Tooltip(label, text=color_tooltips[i])

        colour_var = tk.StringVar(value=default_colors[i])
        gui_vars[var_name] = colour_var

        # Clickable colour square
        colour_square = tk.Label(
            color_frame,
            bg=default_colors[i],
            width=4,
            height=1,
            relief="solid",
            cursor="hand2"
        )
        colour_square.grid(row=i, column=1, padx=5)

        # Text field showing hex value
        entry = ttk.Entry(
            color_frame,
            textvariable=colour_var,
            width=12
        )
        entry.grid(row=i, column=2, padx=5)
        # Unfocus on Enter key
        entry.bind("<Return>", unfocus_entry)

        # Connect entry fields and color swatches
        colour_var.trace_add(
            "write", 
            lambda *args, v=colour_var, s=colour_square: update_square_from_text(v, s)
        )

        colour_square.bind(
            "<Button-1>", 
            lambda event, v=colour_var, s=colour_square: pick_colour(event, v, s)
        )

    ttk.Button(
        color_frame,
        text="Reset colors", 
        style="Small.TButton",
        command=reset_colors,
    ).grid(column=2, row=3, pady=(10,0), sticky="e")
    
    # ------------------------------------------------------------------
    # OUTPUT OPTIONS
    # ------------------------------------------------------------------

    output_path_frame = ttk.Frame(outputs_frame)
    output_path_frame.grid(row=0, column=0, sticky="ew")
    add_path_row(output_path_frame, 0,
                 "output_dir", "Output folder", None, True)
    configure_path_columns(output_path_frame)
    outputs_frame.columnconfigure(0, weight=1)

    checkbox_frame = ttk.Frame(outputs_frame, height=100)
    checkbox_frame.grid(row=1, column=0, sticky="w", pady=5)

    checkbox_vars = ["copy_audio", "generate_data", "generate_html"]
    checkbox_labels = ["Copy audio files", 
                        "Recreate data", 
                        "Recreate HTML file"]

    checkbox_tooltips = [
        ("If checked, audio files will be copied from the input audio folder to " +
        "TrACE audio folder. Uncheck if the audios already have been copied and " +
        "don't need to be updated."),

        ("If checked, data files will be re-created. As data creation is " +
        "typically fast, this option can remain checked most of the time."),

        ("If checked, TrACE HTML page will be re-created from scratch. Uncheck " +
        "if you made manual modifications to the HTML template that you want to " +
        "preserve.")
    ]

    for i, var_name in enumerate(checkbox_vars):
        var = tk.BooleanVar(value=True)
        gui_vars[var_name] = var

        chk = ttk.Checkbutton(
            checkbox_frame,
            text=f"{checkbox_labels[i]}",
            variable=var
        )
        
        chk.grid(row=0, column=i, padx=10)

        Tooltip(chk, text=checkbox_tooltips[i], waittime=50)

    # ------------------------------------------------------------------
    # Bottom-right Run button
    # ------------------------------------------------------------------

    button_frame = ttk.Frame(root, padding=10)

    button_frame.pack(fill="x")

    run_controls["button"] = ttk.Button(
        button_frame,
        text="Run",
        style="Custom.TButton",
        command=lambda v=gui_vars: on_run(v)
    )
    run_controls["button"].pack(side="right")

    run_controls["hint"] = ttk.Label(button_frame, foreground=muted_color)
    run_controls["hint"].pack(side="right", padx=10)

    refresh_paths()

    root.mainloop()