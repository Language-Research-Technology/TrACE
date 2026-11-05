import tkinter as tk
import tkinter.font as tkFont
from tkinter import colorchooser, filedialog, ttk
from pathlib import Path
import ctypes
import sys
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
                    bg='#343a40',
                    pad=(9, 6, 9, 6),
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
                            foreground='white',
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

    # Without this, Windows draws the window at 100% and stretches it on
    # screens with display scaling, which makes everything blurry
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass

    root = tk.Tk()
    gui_vars = {}

    root.title("TrACE preparation")

    # Fonts scale with the display, but sizes given in pixels don't, so
    # spacing is scaled with px()
    scale = max(1.0, root.winfo_fpixels("1i") / 96)

    def px(n):
        return round(n * scale)

    default_font = tkFont.nametofont("TkDefaultFont")
    default_font.configure(size=10)
    tkFont.nametofont("TkTextFont").configure(size=10)

    style = ttk.Style()
    style.theme_use('clam') 

    # The window is a light grey background with white cards on it. Section
    # headings are plain bold text, and only the Run button is coloured
    bg_color = "#f5f6f8"
    card_bg = "#ffffff"
    card_border = "#dee2e6"
    button_bg = "#f1f3f5"
    button_hover = "#e9ecef"
    text_color = "#343a40"
    muted_color = "#868e96"
    accent_color = "#228be6"
    font_family = default_font.cget("family")

    root.configure(bg=bg_color)
    style.configure(".", background=bg_color, foreground=text_color)

    style.configure("Title.TLabel", font=(font_family, 16, "bold"))
    style.configure("Section.TLabel", font=(font_family, 11, "bold"))
    style.configure("Muted.TLabel", foreground=muted_color)

    style.configure("Card.TFrame", background=card_bg)
    style.configure("Card.TLabel", background=card_bg,
                    foreground=muted_color)
    style.configure("CardText.TLabel", background=card_bg)
    style.configure("CardTitle.TLabel", background=card_bg,
                    font=(font_family, 10, "bold"))

    # Flat grey buttons inside cards
    style.configure(
        "Card.TButton",
        background=button_bg,
        bordercolor=card_border,
        lightcolor=button_bg,
        darkcolor=button_bg,
        padding=(px(10), px(3)),
        focusthickness=0,
        focuscolor=button_bg
    )
    style.map(
        "Card.TButton",
        background=[("active", button_hover)],
        lightcolor=[("active", button_hover)],
        darkcolor=[("active", button_hover)]
    )

    # Borderless button, e.g. for removing a chosen path
    style.configure(
        "Ghost.TButton",
        background=card_bg,
        foreground=muted_color,
        bordercolor=card_bg,
        lightcolor=card_bg,
        darkcolor=card_bg,
        padding=(px(6), px(3)),
        focusthickness=0,
        focuscolor=card_bg
    )
    style.map(
        "Ghost.TButton",
        background=[("active", button_hover)],
        bordercolor=[("active", button_hover)],
        lightcolor=[("active", button_hover)],
        darkcolor=[("active", button_hover)]
    ) 

    # Flat checkboxes: a grey outline, or blue with a white tick when checked
    style.configure(
        "Card.TCheckbutton",
        background=card_bg,
        focuscolor=card_bg,
        indicatorbackground=card_bg,
        indicatorforeground="white",
        upperbordercolor="#adb5bd",
        lowerbordercolor="#adb5bd",
        indicatormargin=(0, 0, px(8), 0),
        padding=(0, px(2))
    )
    style.map(
        "Card.TCheckbutton",
        background=[("active", card_bg)],
        indicatorbackground=[("selected", accent_color)],
        upperbordercolor=[("selected", accent_color), 
                          ("active", accent_color)],
        lowerbordercolor=[("selected", accent_color),
                          ("active", accent_color)]
    )

    style.configure(
        "TEntry",
        fieldbackground=card_bg,
        bordercolor=card_border,
        lightcolor=card_bg,
        darkcolor=card_bg,
        padding=(px(6), px(4)),
        selectbackground="#d0ebff",
        selectforeground=text_color
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", accent_color)],
        lightcolor=[("focus", accent_color)]
    ) 

    style.configure("TSeparator", background=card_border)

    def make_card(parent, padding=12):
        """A white frame with a thin border"""
        return tk.Frame(parent, bg=card_bg, highlightthickness=1,
                        highlightbackground=card_border,
                        highlightcolor=card_border,
                        padx=px(padding), pady=px(padding))

    # Blue button for the main action
    style.configure(
        "Accent.TButton",
        background=accent_color,
        foreground="white",
        bordercolor=accent_color,
        lightcolor=accent_color,
        darkcolor=accent_color,
        padding=(px(18), px(5)),
        focusthickness=0,
        focuscolor=accent_color
    )
    style.map(
        "Accent.TButton",
        background=[("disabled", "#ced4da"), ("pressed", "#1971c2"),
                    ("active", "#1c7ed6")],
        foreground=[("disabled", "#f8f9fa")],
        bordercolor=[("disabled", "#ced4da")],
        lightcolor=[("disabled", "#ced4da"), ("active", "#1c7ed6")],
        darkcolor=[("disabled", "#ced4da"), ("active", "#1c7ed6")]
    )

    # Header
    header_frame = ttk.Frame(root, padding=(px(20), px(16), px(20), 0))
    header_frame.pack(fill="x")
    ttk.Label(
        header_frame,
        text="TrACE preparation",
        style="Title.TLabel"
    ).pack(anchor="w")
    ttk.Label(
        header_frame,
        text="Turn your recordings and ELAN transcripts into a TrACE page.",
        style="Muted.TLabel"
    ).pack(anchor="w")

    # Main layout
    main_frame = ttk.Frame(root, padding=(px(16), 0, px(16), px(16)))
    main_frame.pack(fill="both", expand=True)

    # Sections: a bold heading followed by a frame for the contents
    def add_section(i, title):
        ttk.Label(
            main_frame,
            text=title,
            style="Section.TLabel"
        ).grid(row=2 * i, column=0, sticky="w", padx=px(4),
               pady=(px(16), px(6)))

        frame = ttk.Frame(main_frame)
        frame.grid(row=2 * i + 1, column=0, sticky="nsew")
        return frame

    paths_frame = add_section(0, "1. Input files")
    options_frame = add_section(1, "2. TrACE page options")
    outputs_frame = add_section(2, "3. Output")

    main_frame.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # FILE SELECTORS
    # ------------------------------------------------------------------

    # Names of the vars here and below match names of the main processing
    # function, so that they can be easily unpacked later
    #
    # Each path is shown as a card:
    #
    #   [icon]  Audio folder                 [Change] [✕]
    #           …/project/audio
    #           ✓ 12 audio files
    #
    # Warnings and errors tint the border of the card

    csv_types = [('CSV Files', '*.csv')]
    md_types = [('Markdown Files', '*.md'), ('Text Files', '*.txt')]

    # (card border color, status icon, status text color)
    status_styles = {
        "ok": (card_border, "✓", muted_color),
        "warn": ("#f59f00", "!", "#e67700"),
        "error": ("#e03131", "✗", "#c92a2a"),
        "empty": (card_border, "", muted_color),
    }
    # (main color, lighter color for the folded corner of files)
    icon_colors = {"set": ("#a5b8cc", "#d2dce6"),
                   "empty": ("#dee2e6", "#eef0f2")}

    icon_font = tkFont.Font(family=font_family, size=-px(8), weight="bold")

    def draw_icon(canvas, filetypes, colors):
        """
        Draw a flat folder or document icon

        Only rectangles are used, since Tk draws slanted edges jagged
        """

        color, light = colors
        canvas.delete("all")
        if filetypes is None:
            canvas.create_rectangle(2, 6, 13, 10, fill=color, width=0)
            canvas.create_rectangle(2, 9, 30, 27, fill=color, width=0)
        else:
            canvas.create_rectangle(6, 2, 27, 30, fill=color, width=0)
            canvas.create_rectangle(21, 2, 27, 8, fill=light, width=0)
        canvas.scale("all", 0, 0, scale, scale)

        if filetypes is not None:
            # Show the extension of the first file type, e.g. "CSV"
            ext = filetypes[0][1].lstrip("*.").upper()
            canvas.create_text(px(16), px(19), text=ext, fill="white",
                               font=icon_font)

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

    path_cards = {}

    # Filled in when the Run button is created at the bottom
    run_controls = {}

    def refresh_paths(*args):
        # All cards are refreshed together, since the recordings check
        # depends on the audio and ELAN folders
        missing = []
        has_errors = False

        for var_name, card in path_cards.items():
            value = gui_vars[var_name].get().strip()

            if value:
                status, info = check_path(var_name, value)
                full_path = str(Path(value).resolve())
                card["path"].configure(text=shorten_path(full_path, 38))
                card["path_tip"].text = full_path
                card["choose"].configure(text="Change…")
                card["remove"].grid()
                has_errors = has_errors or status == "error"
            else:
                status, info = "empty", ""
                card["path"].configure(text="Not chosen yet")
                card["path_tip"].text = "Not chosen yet"
                card["choose"].configure(text="Choose…")
                card["remove"].grid_remove()
                if card["required"]:
                    # Lowercase "Audio folder", but not "ELAN folder"
                    label = card["label"]
                    if not label[:2].isupper():
                        label = label[0].lower() + label[1:]
                    missing.append(label)

            border, icon, status_color = status_styles[status]
            card["frame"].configure(highlightbackground=border,
                                    highlightcolor=border)
            draw_icon(card["icon"], card["filetypes"],
                      icon_colors["set" if value else "empty"])
            card["status"].configure(
                text=f"{icon} {info}" if info else " ",
                foreground=status_color
            )

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

    def add_path_card(parent, row, column,
                      var_name, label_text, filetypes, required):
        """Add a card for one path to a grid in `parent`"""

        if (var_name == "output_dir"):
            var = tk.StringVar(value=DEFAULTS[var_name])
        else:
            var = tk.StringVar()

        gui_vars[var_name] = var
        card = {"label": label_text, "filetypes": filetypes,
                "required": required}

        frame = make_card(parent)
        frame.grid(row=row, column=column, sticky="nsew", padx=px(4),
                   pady=px(4))
        card["frame"] = frame

        card["icon"] = tk.Canvas(frame, width=px(32), height=px(32),
                                 bg=card_bg, highlightthickness=0)
        card["icon"].grid(row=0, column=1, rowspan=3, padx=(0, px(12)))

        title = ttk.Label(frame, text=label_text, style="CardTitle.TLabel")
        title.grid(row=0, column=2, sticky="w")
        Tooltip(title, text=HELP_STRINGS[var_name], waittime=50)

        card["path"] = ttk.Label(frame, style="Card.TLabel")
        card["path"].grid(row=1, column=2, sticky="w")
        card["path_tip"] = Tooltip(card["path"], text="", waittime=50)

        card["status"] = ttk.Label(frame, style="Card.TLabel")
        card["status"].grid(row=2, column=2, sticky="w")

        buttons = tk.Frame(frame, bg=card_bg)
        buttons.grid(row=0, column=3, rowspan=3, padx=(px(8), 0))

        if filetypes is None:
            command = lambda v=var: browse_folder(v)
        else:
            command = lambda v=var, t=filetypes: browse_file(v, t)

        card["choose"] = ttk.Button(buttons, width=8, style="Card.TButton",
                                    command=command)
        card["choose"].grid(row=0, column=0)

        card["remove"] = ttk.Button(buttons, text="✕", width=2,
                                    style="Ghost.TButton",
                                    command=lambda v=var: v.set(""))
        card["remove"].grid(row=0, column=1, padx=(px(4), 0))
        Tooltip(card["remove"], text="Remove", waittime=50)

        frame.columnconfigure(2, weight=1)

        path_cards[var_name] = card
        var.trace_add("write", refresh_paths)

    for i, spec in enumerate([
        ("audio_dir", "Audio folder", None, True),
        ("elan_dir", "ELAN folder", None, True),
        ("speakers_info_file", "Speakers CSV file", csv_types, True),
        ("recordings_info_file", "Recordings CSV file", csv_types, True),
    ]):
        add_path_card(paths_frame, i // 2, i % 2, *spec)

    ttk.Label(
        paths_frame,
        text="Optional",
        style="Muted.TLabel"
    ).grid(row=2, column=0, sticky="w", padx=px(4), pady=(px(10), 0))

    for i, spec in enumerate([
        ("help_file", "Help file", md_types, False),
        ("licence_file", "Licence file", md_types, False),
        ("logos_file", "Logos CSV file", csv_types, False),
    ]):
        add_path_card(paths_frame, 3 + i // 2, i % 2, *spec)

    paths_frame.columnconfigure((0, 1), weight=1, uniform="cards")

    # ------------------------------------------------------------------
    # HTML CONFIGURATION OPTIONS
    # ------------------------------------------------------------------
    
    # TITLES

    # All page options share one card: texts on the left, colors on the right
    options_card = make_card(options_frame, padding=14)
    options_card.grid(row=0, column=0, sticky="ew", padx=px(4), pady=px(4))
    options_frame.columnconfigure(0, weight=1)

    titles_frame = ttk.Frame(options_card, style="Card.TFrame")
    titles_frame.grid(row=0, column=0, sticky="nsew")
    titles_frame.columnconfigure(1, weight=1)
    options_card.columnconfigure(0, weight=1)

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
        label = ttk.Label(titles_frame, text=text_labels[i],
                          style="CardText.TLabel")
        label.grid(
            row=i, column=0, sticky="w", padx=(0, px(12)), pady=px(4)
        )
        Tooltip(label, text=text_tooltips[i], waittime=50)

        var = tk.StringVar()
        gui_vars[var_name] = var

        entry = ttk.Entry(
            titles_frame,
            textvariable=var,
            width=40
        )
        entry.grid(row=i, column=1, sticky="ew", pady=px(4))
        # Unfocus on Enter key
        entry.bind("<Return>", unfocus_entry)

        # Default values
        entry.insert(0, text_defaults[i])

    # VERTICAL LINE
    vertical_line = ttk.Separator(options_card, orient=tk.VERTICAL)
    vertical_line.grid(row=0, column=1, sticky="ns", padx=px(24))

    # COLOR PICKERS
    color_frame = ttk.Frame(options_card, style="Card.TFrame")
    color_frame.grid(row=0, column=2, sticky="nw")

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
            text=color_labels[i],
            style="CardText.TLabel"
        )
        label.grid(row=i, column=0, sticky="w", padx=(0, px(12)), pady=px(4))
        Tooltip(label, text=color_tooltips[i])

        colour_var = tk.StringVar(value=default_colors[i])
        gui_vars[var_name] = colour_var

        # Clickable colour square
        colour_square = tk.Label(
            color_frame,
            bg=default_colors[i],
            width=4,
            height=1,
            highlightthickness=1,
            highlightbackground=card_border,
            cursor="hand2"
        )
        colour_square.grid(row=i, column=1, padx=(0, px(6)))

        # Text field showing hex value
        entry = ttk.Entry(
            color_frame,
            textvariable=colour_var,
            width=10
        )
        entry.grid(row=i, column=2, pady=px(4))
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
        style="Card.TButton",
        command=reset_colors,
    ).grid(column=2, row=3, pady=(px(6), 0), sticky="e")
    
    # ------------------------------------------------------------------
    # OUTPUT OPTIONS
    # ------------------------------------------------------------------

    # Output folder card on the left, a card with checkboxes on the right,
    # lined up with the input cards above
    add_path_card(outputs_frame, 0, 0,
                  "output_dir", "Output folder", None, True)
    outputs_frame.columnconfigure((0, 1), weight=1, uniform="cards")

    checkbox_frame = make_card(outputs_frame)
    checkbox_frame.grid(row=0, column=1, sticky="nsew", padx=px(4),
                        pady=px(4))

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
            variable=var,
            style="Card.TCheckbutton"
        )
        
        chk.grid(row=i, column=0, sticky="w", pady=px(1))

        Tooltip(chk, text=checkbox_tooltips[i], waittime=50)

    # ------------------------------------------------------------------
    # Bottom bar with the Run button
    # ------------------------------------------------------------------

    # A white bar with a thin line above it; the right edge lines up with
    # the cards
    footer = tk.Frame(root, bg=card_bg)
    footer.pack(fill="x", side="bottom")
    tk.Frame(footer, height=1, bg=card_border).pack(fill="x")

    button_frame = ttk.Frame(footer, style="Card.TFrame",
                             padding=(px(20), px(12), px(20), px(12)))
    button_frame.pack(fill="x")

    run_controls["button"] = ttk.Button(
        button_frame,
        text="Run",
        style="Accent.TButton",
        width=10,
        command=lambda v=gui_vars: on_run(v)
    )
    run_controls["button"].pack(side="right")

    run_controls["hint"] = ttk.Label(button_frame, style="Card.TLabel")
    run_controls["hint"].pack(side="right", padx=px(12))

    refresh_paths()

    # Fit the window to its contents, and don't allow it to get smaller
    root.update_idletasks()
    root.minsize(max(px(900), root.winfo_reqwidth()), root.winfo_reqheight())

    root.mainloop()