"""
Graphical interface for TrACE preparation (tkinter)

The window has a header, two sections (input files and TrACE page options)
and a bottom bar with the output folder and the Run button. The fields are
defined in tables at the top of this file, followed by the colors; the
layout is built in run_gui(). The checks of the chosen paths are in
checks.py.
"""

import tkinter as tk
import tkinter.font as tkFont
from tkinter import colorchooser, filedialog, messagebox, ttk
from pathlib import Path
import ctypes
import sys
import os

from constants import HELP_STRINGS, DEFAULTS
from processing import (do_processing, get_TrACE_file,
                        read_TrACE_info_sections, read_TrACE_options,
                        read_previous_settings, normalize_color,
                        LAST_RUN_FILE)
from checks import (AUDIO_EXTENSIONS, check_folder, check_speakers,
                    check_recordings, check_markdown, check_logos,
                    check_output)

# ------------------------------------------------------------------
# FIELDS
#
# Change the titles, order or file types of the fields here. Each variable
# name matches an argument of do_processing(), so that the values can be
# passed on directly; the tooltips are the HELP_STRINGS in constants.py
# ------------------------------------------------------------------

# File types for the file dialogs ("All Files" is always added)
FOLDER = None
CSV_FILES = [("CSV Files", "*.csv")]
# One filter for both Markdown and plain text, so that neither is hidden
TEXT_FILES = [("Markdown or Text Files", ("*.md", "*.markdown", "*.txt"))]

# Required input files: cards in two columns
INPUT_FILES = [
    # variable name           title                   file type
    ("audio_dir",             "Audio folder",         FOLDER),
    ("elan_dir",              "ELAN folder",          FOLDER),
    ("speakers_info_file",    "Speakers CSV file",    CSV_FILES),
    ("recordings_info_file",  "Recordings CSV file",  CSV_FILES),
]

# Optional files: smaller cards below the input files, in two columns
OPTIONAL_FILES = [
    # variable name           title                   file type
    ("help_file",             "Help file",            TEXT_FILES),
    ("licence_file",          "Licence file",         TEXT_FILES),
    ("logos_file",            "Logos CSV file",       CSV_FILES),
]

# The output folder, in the bottom bar
OUTPUT_FOLDER = ("output_dir", "Output folder")

# Texts of the TrACE page: a grid with two fields per row, followed by the
# colors
PAGE_TEXTS = [
    # variable name           title
    ("title",                 "Browser tab title"),
    ("header",                "Page header"),
    ("ann_note_tier",         "Notes tier in ELAN"),
]

# Colors of the TrACE page: clickable swatches
PAGE_COLORS = [
    # variable name           title
    ("primary_color",         "Interface color"),
    ("ann_highlight_color",   "Current annotation color"),
    ("filter_match_color",    "Filter match color"),
]

# ------------------------------------------------------------------
# COLORS
#
# The window is a light grey background with white cards on it. Section
# headings are plain bold text, and only the Run button (and problems) are
# colored. Change the colors here
# ------------------------------------------------------------------

# Window and cards
BG_COLOR = "#f5f6f8"
CARD_BG = "#ffffff"
CARD_BORDER = "#dee2e6"

# Text
TEXT_COLOR = "#343a40"
# Secondary text: the lightest grey with enough contrast for reading
# (4.5:1, WCAG AA) on both the white cards and the grey background
MUTED_COLOR = "#687078"
DISABLED_TEXT_COLOR = "#adb5bd"
SELECTION_COLOR = "#d0ebff"

# Grey buttons
BUTTON_BG = "#f1f3f5"
BUTTON_HOVER = "#e9ecef"

# Blue: the Run button and checked checkboxes
ACCENT_COLOR = "#228be6"
ACCENT_HOVER = "#1c7ed6"
ACCENT_PRESSED = "#1971c2"
ACCENT_TEXT = "white"
ACCENT_DISABLED = "#ced4da"
ACCENT_DISABLED_TEXT = "#f8f9fa"
CHECKBOX_BORDER = "#adb5bd"
CHECKBOX_TICK = "white"

# Problems with paths: card border and status text
WARNING_BORDER = "#f59f00"
WARNING_TEXT = "#e67700"
ERROR_BORDER = "#e03131"
ERROR_TEXT = "#c92a2a"

# Folder and file icons: main color and the folded corner of files, for
# chosen and empty paths
ICON_COLOR = "#a5b8cc"
ICON_FOLD = "#d2dce6"
ICON_EMPTY = "#dee2e6"
ICON_EMPTY_FOLD = "#eef0f2"
ICON_TEXT = "white"

# Tooltips
TOOLTIP_BG = "#343a40"
TOOLTIP_TEXT = "white"

# ------------------------------------------------------------------
# DISPLAY HELPERS
# ------------------------------------------------------------------

def shorten_path(path, max_len=40):
    """
    Shorten a path from the left, keeping as many trailing parts as fit

    E.g. "/home/user/fieldwork/project/audio" becomes "…/project/audio".

    Args:
        path: path as a string
        max_len: maximum length of the result, in characters

    Returns:
        str: the path, or a shortened version starting with "…"
    """

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

def run_gui():
    """
    Build the TrACE preparation window and run it until it is closed

    The values of the fields are kept in tkinter variables (gui_vars), named
    after the arguments of processing.do_processing(), which gets them all
    when Run is clicked.
    """

    def report(message, type="info"):
        """Show a problem reported by processing in an error dialog"""
        messagebox.showerror("TrACE preparation", str(message))

    def confirm_replace_html(html_file):
        """Ask whether to replace a page that was edited by hand"""

        answer = {"replace": False}

        dialog = tk.Toplevel(root, bg=CARD_BG, padx=px(20), pady=px(16))
        dialog.title("TrACE page was edited")
        dialog.transient(root)
        dialog.resizable(False, False)

        ttk.Label(
            dialog,
            text="TrACE.html has been edited since it was created",
            style="CardTitle.TLabel"
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(
            dialog,
            text=("Replacing it will discard those edits; a backup copy "
                  "will be kept next to it.\n\n"
                  "If you keep it, changes to the title, header, colors, "
                  "help, licence or logos won't be applied."),
            style="CardText.TLabel",
            wraplength=px(380),
            justify="left"
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(px(6), 0))

        def close(replace):
            answer["replace"] = replace
            dialog.destroy()

        ttk.Button(
            dialog,
            text="Replace page",
            style="Card.TButton",
            command=lambda: close(True)
        ).grid(row=2, column=0, sticky="e", pady=(px(16), 0))

        # Keeping the page is the safe choice, so it's the default
        keep = ttk.Button(
            dialog,
            text="Keep my page",
            style="Accent.TButton",
            command=lambda: close(False)
        )
        keep.grid(row=2, column=1, sticky="e", padx=(px(8), 0),
                  pady=(px(16), 0))
        dialog.columnconfigure(0, weight=1)

        dialog.bind("<Return>", lambda event: close(False))
        dialog.bind("<Escape>", lambda event: close(False))
        dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))

        # Show it in the middle of the main window
        dialog.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() -
                                  dialog.winfo_reqwidth()) // 2
        y = root.winfo_rooty() + (root.winfo_height() -
                                  dialog.winfo_reqheight()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        keep.focus_set()
        dialog.grab_set()
        root.wait_window(dialog)

        return answer["replace"]

    def on_run(gui_vars):
        """Pass the values of all fields to processing (the Run button)"""
        input_vars = {k:v.get() for k,v in gui_vars.items()}

        # Empty paths are passed on as None
        paths = [field[0] for field in INPUT_FILES + OPTIONAL_FILES]
        for v in paths + [OUTPUT_FOLDER[0]]:
            if input_vars[v].strip() == "":
                input_vars[v] = None

        # An optional file that is not chosen keeps the info section of the
        # existing page (None), unless it was removed with ✕ ("")
        for var_name, _, _ in OPTIONAL_FILES:
            if (input_vars[var_name] is None and
                    not path_widgets[var_name].get("keep")):
                input_vars[var_name] = ""

        # All steps are always run from the GUI: copying the audio and
        # recreating the data are quick for typical collections, and edited
        # pages are only replaced after asking
        input_vars.update(copy_audio=True, generate_data=True,
                          generate_html=True)
        input_vars["report_callback"] = report
        input_vars["confirm_replace_callback"] = confirm_replace_html

        root.configure(cursor="watch")
        root.update_idletasks()
        try:
            result = do_processing(**input_vars)
        except Exception as e:
            report(f"Something went wrong: {e}")
            return
        finally:
            root.configure(cursor="")

        if result is None:
            # The problem was already reported
            return

        message = f"Your TrACE page is in:\n{result['output_dir']}"
        if result["html"] == "kept":
            message += ("\n\nYour edited TrACE.html was kept, so changes to "
                        "the title, header, colors, help, licence or logos "
                        "were not applied.")
        elif result["backup"] is not None:
            message += ("\n\nThe previous page was saved as:\n" +
                        result["backup"].name)
        # The page now matches the fields
        read_existing_page()

        messagebox.showinfo("TrACE is ready", message)


    # Folder of the last file or folder chosen with a dialog. The files of a
    # collection are usually kept together, so dialogs for empty fields
    # start there instead of where make_trace was started (see
    # dialog_start_dir())
    browse_state = {"last_dir": None}

    def dialog_start_dir(var):
        """
        Folder a file or folder dialog starts in: where the field's own path
        is, else where the last choice was made, else the folder make_trace
        was started in
        """
        value = var.get().strip()
        if value:
            path = Path(value)
            if path.is_dir():
                return path
            if path.is_file():
                return path.parent

        last_dir = browse_state["last_dir"]
        if last_dir is not None and last_dir.is_dir():
            return last_dir

        return Path.cwd()

    def remember_choice(choice):
        """
        Remember where a choice was made, for the next dialog: the folder
        that contains the chosen file or folder. For a folder, that is its
        parent, which shows it together with the folders next to it (e.g.
        "audio" next to "elan")
        """
        browse_state["last_dir"] = Path(choice).parent

    def browse_file(var, filetypes):
        """Select a file"""

        choice = filedialog.askopenfilename(title="Select File",
                                            filetypes=filetypes +
                                                [('All Files', '*.*')],
                                            initialdir=dialog_start_dir(var))

        if choice:
            var.set(choice)
            remember_choice(choice)

    def browse_folder(var):
        """Select a folder"""

        choice = filedialog.askdirectory(title="Select Folder",
                                         initialdir=dialog_start_dir(var))

        if choice:
            var.set(choice)
            remember_choice(choice)

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
                    bg=TOOLTIP_BG,
                    pad=(9, 6, 9, 6),
                    text='widget info',
                    waittime=400,
                    wraplength=None):

            self.waittime = waittime  # in miliseconds, originally 500
            # in pixels, originally 180; wide enough for a few short lines
            self.wraplength = wraplength or px(420)
            self.widget = widget
            self.text = text
            # Optional: a color, shown as a small square where the text says
            # "{color}"
            self.color = None
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
            # Nothing to show, e.g. for a hidden ↶
            if not self.text:
                return

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
            if self.color and "{color}" in self.text:
                label = self.text_with_color(win, bg)
            else:
                label = tk.Label(win,
                                text=self.text,
                                justify=tk.LEFT,
                                background=bg,
                                foreground=TOOLTIP_TEXT,
                                relief=tk.SOLID,
                                borderwidth=0,
                                wraplength=self.wraplength)

            label.grid(padx=(pad[0], pad[2]),
                    pady=(pad[1], pad[3]),
                    sticky=tk.NSEW)
            win.grid()

            x, y = tip_pos_calculator(widget, label)

            self.tw.wm_geometry("+%d+%d" % (x, y))

        def text_with_color(self, parent, bg):
            """
            The text, line by line, with a small square in self.color where
            it says "{color}" (a label can't show it inside its text)
            """
            def add_text(row, text):
                if text:
                    tk.Label(row, text=text, background=bg,
                             foreground=TOOLTIP_TEXT, borderwidth=0, padx=0,
                             pady=0).pack(side="left")

            content = tk.Frame(parent, background=bg)
            for i, line in enumerate(self.text.split("\n")):
                row = tk.Frame(content, background=bg)
                row.grid(row=i, column=0, sticky="w")

                before, placeholder, after = line.partition("{color}")
                add_text(row, before)
                if placeholder:
                    try:
                        tk.Frame(row, background=self.color, width=px(12),
                                 height=px(12), highlightthickness=1,
                                 highlightbackground=TOOLTIP_TEXT
                                 ).pack(side="left", padx=(0, px(4)))
                    except tk.TclError:
                        # Not a color that tkinter knows: no square
                        pass
                add_text(row, after)
            return content

        def hide(self):
            tw = self.tw
            if tw:
                tw.destroy()
            self.tw = None

    def unfocus_entry(event):
        """Move the focus away from a text field, e.g. on Enter"""
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
        """Scale a size in pixels for the display (e.g. 150% on Windows)"""
        return round(n * scale)

    default_font = tkFont.nametofont("TkDefaultFont")
    default_font.configure(size=10)
    tkFont.nametofont("TkTextFont").configure(size=10)

    style = ttk.Style()
    style.theme_use('clam') 

    font_family = default_font.cget("family")

    root.configure(bg=BG_COLOR)
    style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR)

    style.configure("Title.TLabel", font=(font_family, 16, "bold"))
    style.configure("Section.TLabel", font=(font_family, 11, "bold"))
    style.configure("Muted.TLabel", foreground=MUTED_COLOR)

    style.configure("Card.TFrame", background=CARD_BG)
    style.configure("Card.TLabel", background=CARD_BG,
                    foreground=MUTED_COLOR)
    style.configure("CardText.TLabel", background=CARD_BG)
    # Small grey uppercase captions, e.g. "SAVE TO"
    style.configure("Caption.TLabel", background=CARD_BG,
                    foreground=MUTED_COLOR, font=(font_family, 8, "bold"))
    style.configure("CardTitle.TLabel", background=CARD_BG,
                    font=(font_family, 10, "bold"))

    # Flat grey buttons inside cards
    style.configure(
        "Card.TButton",
        background=BUTTON_BG,
        bordercolor=CARD_BORDER,
        lightcolor=BUTTON_BG,
        darkcolor=BUTTON_BG,
        padding=(px(10), px(3)),
        focusthickness=0,
        focuscolor=BUTTON_BG
    )
    # Disabled buttons keep their shape, with lighter text and no hover
    style.map(
        "Card.TButton",
        foreground=[("disabled", DISABLED_TEXT_COLOR)],
        background=[("disabled", BUTTON_BG), ("active", BUTTON_HOVER)],
        lightcolor=[("disabled", BUTTON_BG), ("active", BUTTON_HOVER)],
        darkcolor=[("disabled", BUTTON_BG), ("active", BUTTON_HOVER)]
    )

    # Borderless blue symbol button, e.g. ↶ (undo) for a changed page option
    style.configure(
        "Link.TButton",
        background=CARD_BG,
        foreground=ACCENT_COLOR,
        bordercolor=CARD_BG,
        lightcolor=CARD_BG,
        darkcolor=CARD_BG,
        font=(font_family, 12),
        padding=(px(4), 0),
        focusthickness=0,
        focuscolor=CARD_BG
    )
    style.map(
        "Link.TButton",
        foreground=[("pressed", ACCENT_PRESSED), ("active", ACCENT_HOVER)],
        background=[("active", BUTTON_BG)],
        bordercolor=[("active", BUTTON_BG)],
        lightcolor=[("active", BUTTON_BG)],
        darkcolor=[("active", BUTTON_BG)]
    )

    # Borderless button, e.g. for removing a chosen path
    style.configure(
        "Ghost.TButton",
        background=CARD_BG,
        foreground=MUTED_COLOR,
        bordercolor=CARD_BG,
        lightcolor=CARD_BG,
        darkcolor=CARD_BG,
        padding=(px(6), px(3)),
        focusthickness=0,
        focuscolor=CARD_BG
    )
    style.map(
        "Ghost.TButton",
        background=[("active", BUTTON_HOVER)],
        bordercolor=[("active", BUTTON_HOVER)],
        lightcolor=[("active", BUTTON_HOVER)],
        darkcolor=[("active", BUTTON_HOVER)]
    )

    # Flat checkboxes: a grey outline, or blue with a white tick when checked
    style.configure(
        "Card.TCheckbutton",
        background=CARD_BG,
        focuscolor=CARD_BG,
        indicatorbackground=CARD_BG,
        indicatorforeground=CHECKBOX_TICK,
        upperbordercolor=CHECKBOX_BORDER,
        lowerbordercolor=CHECKBOX_BORDER,
        indicatormargin=(0, 0, px(8), 0),
        padding=(0, px(2))
    )
    style.map(
        "Card.TCheckbutton",
        background=[("active", CARD_BG)],
        indicatorbackground=[("selected", ACCENT_COLOR)],
        upperbordercolor=[("selected", ACCENT_COLOR), 
                          ("active", ACCENT_COLOR)],
        lowerbordercolor=[("selected", ACCENT_COLOR),
                          ("active", ACCENT_COLOR)]
    )

    style.configure(
        "TEntry",
        fieldbackground=CARD_BG,
        bordercolor=CARD_BORDER,
        lightcolor=CARD_BG,
        darkcolor=CARD_BG,
        padding=(px(6), px(4)),
        selectbackground=SELECTION_COLOR,
        selectforeground=TEXT_COLOR
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", ACCENT_COLOR)],
        lightcolor=[("focus", ACCENT_COLOR)]
    ) 

    style.configure("TSeparator", background=CARD_BORDER)

    def make_card(parent, padding=12):
        """A white frame with a thin border"""
        return tk.Frame(parent, bg=CARD_BG, highlightthickness=1,
                        highlightbackground=CARD_BORDER,
                        highlightcolor=CARD_BORDER,
                        padx=px(padding), pady=px(padding))

    # Blue button for the main action
    style.configure(
        "Accent.TButton",
        background=ACCENT_COLOR,
        foreground=ACCENT_TEXT,
        bordercolor=ACCENT_COLOR,
        lightcolor=ACCENT_COLOR,
        darkcolor=ACCENT_COLOR,
        padding=(px(18), px(5)),
        focusthickness=0,
        focuscolor=ACCENT_COLOR
    )
    style.map(
        "Accent.TButton",
        background=[("disabled", ACCENT_DISABLED), ("pressed", ACCENT_PRESSED),
                    ("active", ACCENT_HOVER)],
        foreground=[("disabled", ACCENT_DISABLED_TEXT)],
        bordercolor=[("disabled", ACCENT_DISABLED)],
        lightcolor=[("disabled", ACCENT_DISABLED), ("active", ACCENT_HOVER)],
        darkcolor=[("disabled", ACCENT_DISABLED), ("active", ACCENT_HOVER)]
    )

    # Header
    header_frame = ttk.Frame(root, padding=(px(20), px(16), px(20), 0))
    header_frame.pack(fill="x")
    ttk.Label(
        header_frame,
        text="TrACE preparation",
        style="Title.TLabel"
    ).grid(row=0, column=0, sticky="w")
    ttk.Label(
        header_frame,
        text="Turn your recordings and ELAN transcripts into a TrACE page.",
        style="Muted.TLabel"
    ).grid(row=1, column=0, sticky="w")

    # Tell people that the names have explanations, on the line of the
    # subtitle: grey text like the subtitle, with only the icon in blue, so
    # it's easy to find without competing with the Run button. The header has
    # the same side margins as the cards (main frame padding + card padding)
    tip_frame = ttk.Frame(header_frame)
    tip_frame.grid(row=1, column=1, sticky="e")
    ttk.Label(
        tip_frame,
        text="ⓘ",
        foreground=ACCENT_COLOR
    ).grid(row=0, column=0, padx=(0, px(6)))
    ttk.Label(
        tip_frame,
        text="Hover over titles like “Audio folder” for an explanation",
        style="Muted.TLabel"
    ).grid(row=0, column=1)
    header_frame.columnconfigure(1, weight=1)

    # Main layout
    #
    # The sections are inside a canvas, so that they can scroll when the
    # window doesn't fit on the screen (e.g. on laptops). The header and the
    # bottom bar stay in place, and the scrollbar only appears when needed
    body = ttk.Frame(root)
    body.pack(fill="both", expand=True)

    body_canvas = tk.Canvas(body, bg=BG_COLOR, highlightthickness=0,
                            borderwidth=0)
    body_canvas.grid(row=0, column=0, sticky="nsew")
    body_scrollbar = ttk.Scrollbar(body, orient="vertical",
                                   command=body_canvas.yview)
    body_scrollbar.grid(row=0, column=1, sticky="ns")
    body_canvas.configure(yscrollcommand=body_scrollbar.set)
    body.rowconfigure(0, weight=1)
    body.columnconfigure(0, weight=1)

    main_frame = ttk.Frame(body_canvas, padding=(px(16), 0, px(16), px(16)))
    main_window = body_canvas.create_window(0, 0, window=main_frame,
                                            anchor="nw")

    def needs_scrolling():
        return main_frame.winfo_reqheight() > body_canvas.winfo_height()

    def update_scrolling(event=None):
        """Show the scrollbar only when the sections don't fit"""
        body_canvas.configure(scrollregion=(0, 0, 
                                            main_frame.winfo_reqwidth(),
                                            main_frame.winfo_reqheight()))
        if needs_scrolling():
            body_scrollbar.grid()
        else:
            body_scrollbar.grid_remove()
            body_canvas.yview_moveto(0)

    def on_canvas_resize(event):
        # The sections always fill the width of the window
        body_canvas.itemconfigure(main_window, width=event.width)
        update_scrolling()

    main_frame.bind("<Configure>", update_scrolling)
    body_canvas.bind("<Configure>", on_canvas_resize)

    def on_mouse_wheel(event):
        """Scroll the sections with the mouse wheel, if they don't fit"""
        if not needs_scrolling():
            return
        if event.num == 4:
            step = -1
        elif event.num == 5:
            step = 1
        elif sys.platform == "darwin":
            step = -event.delta
        else:
            step = -event.delta // 120
        body_canvas.yview_scroll(step, "units")

    # Linux sends Button-4/5 for the mouse wheel, other systems MouseWheel
    for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        root.bind_all(sequence, on_mouse_wheel)

    # Sections: a bold heading followed by a frame for the contents
    def add_section(i, title):
        """Add section number i: a heading and a frame for its contents"""
        ttk.Label(
            main_frame,
            text=title,
            style="Section.TLabel"
        ).grid(row=2 * i, column=0, sticky="w", padx=px(4),
               pady=(px(14), px(6)))

        frame = ttk.Frame(main_frame)
        frame.grid(row=2 * i + 1, column=0, sticky="nsew")
        return frame

    paths_frame = add_section(0, "1. Input files")
    options_frame = add_section(1, "2. TrACE page")

    main_frame.columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # PATHS
    # ------------------------------------------------------------------

    # Names of the vars here and below match names of the main processing
    # function, so that they can be easily unpacked later
    #
    # Paths are shown in three ways:
    #
    # + "card" for the main inputs:
    #
    #     [icon]  Audio folder                         12 audio files
    #             …/project/audio                   [Change…] [✕]
    #
    # + "row" for the optional files, as smaller one-line cards:
    #
    #     Help file  optional   …/help.md  [Change…] [✕]
    #
    # + "bar" for the output folder, in the bottom bar, showing the TrACE
    #   folder that will be created inside it:
    #
    #     [icon]  SAVE TO           [Change…]
    #             …/project/TrACE
    #
    # Warnings and errors tint the border of a card, or the path text

    # (card border color, status icon, status text color)
    status_styles = {
        "ok": (CARD_BORDER, "✓", MUTED_COLOR),
        "warn": (WARNING_BORDER, "!", WARNING_TEXT),
        "error": (ERROR_BORDER, "✗", ERROR_TEXT),
        "empty": (CARD_BORDER, "", MUTED_COLOR),
    }
    # (main color, lighter color for the folded corner of files)
    icon_colors = {"set": (ICON_COLOR, ICON_FOLD),
                   "empty": (ICON_EMPTY, ICON_EMPTY_FOLD)}

    icon_font = tkFont.Font(family=font_family, size=-px(8), weight="bold")

    def draw_icon(canvas, filetypes, colors, size=32):
        """
        Draw a flat folder or document icon

        Only rectangles are used, since Tk draws slanted edges jagged. Icons
        smaller than 32 pixels have no file type label, as it'd be unreadable
        """

        color, light = colors
        canvas.delete("all")
        if filetypes is None:
            canvas.create_rectangle(2, 6, 13, 10, fill=color, width=0)
            canvas.create_rectangle(2, 9, 30, 27, fill=color, width=0)
        else:
            canvas.create_rectangle(6, 2, 27, 30, fill=color, width=0)
            canvas.create_rectangle(21, 2, 27, 8, fill=light, width=0)
        canvas.scale("all", 0, 0, scale * size / 32, scale * size / 32)

        if filetypes is not None and size >= 32:
            # Show the extension of the first file type, e.g. "CSV". A file
            # type can have one pattern ("*.csv") or several ("*.md", "*.txt")
            patterns = filetypes[0][1]
            if not isinstance(patterns, str):
                patterns = patterns[0]
            ext = patterns.lstrip("*.").upper()
            canvas.create_text(px(16), px(19), text=ext, fill=ICON_TEXT,
                               font=icon_font)

    def check_path(var_name, value):
        """Run the check for a path field; see checks.py"""
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
        if var_name == "logos_file":
            return check_logos(value)
        return check_markdown(value)

    path_widgets = {}

    # Filled in when the Run button is created at the bottom
    run_controls = {}

    # The page options of the existing page (see read_existing_page()). If
    # a field differs from them, ↶ is shown next to it
    existing_page = {"options": {}}

    # Results of the last check of the paths (see refresh_paths()), used by
    # update_run_hint()
    path_state = {"missing": [], "has_errors": False}

    def refresh_paths(*args):
        """
        Check all paths and show the results: status, path and buttons of
        each field, and the hint and state of the Run button
        """
        # All paths are refreshed together, since the recordings check
        # depends on the audio and ELAN folders
        missing = []
        has_errors = False

        for var_name, widget in path_widgets.items():
            value = gui_vars[var_name].get().strip()
            kind = widget["kind"]

            if value:
                status, info = check_path(var_name, value)
                full_path = str(Path(value).resolve())
                has_errors = has_errors or status == "error"
            else:
                status, info, full_path = "empty", "", ""
                if widget["required"]:
                    # Lowercase "Audio folder", but not "ELAN folder"
                    label = widget["label"]
                    if not label[:2].isupper():
                        label = label[0].lower() + label[1:]
                    missing.append(label)

            border, icon, status_color = status_styles[status]
            tip = f"{full_path}\n\n{info}" if info else full_path

            if "frame" in widget:
                widget["frame"].configure(highlightbackground=border,
                                          highlightcolor=border)

            # Info section of the existing page, kept when no file is chosen
            kept = not value and widget.get("keep", False)

            if "icon" in widget:
                draw_icon(widget["icon"], widget["filetypes"],
                          icon_colors["set" if value or kept else "empty"],
                          widget["icon_size"])

            if kind == "card":
                widget["status"].configure(
                    text=f"{icon} {info}" if info else "",
                    foreground=status_color
                )
                widget["path"].configure(
                    text=shorten_path(full_path, 34) if value
                         else "Not chosen yet"
                )
            else:
                # Rows and the bottom bar have no room for the info, so
                # it goes into the tooltip, and only problems are colored
                max_len = 18 if kind == "row" else 32
                shown_path = full_path
                if kind == "bar" and value:
                    shown_path = str(Path(full_path).joinpath("TrACE"))
                if kept:
                    text = "Kept from the existing page"
                    tip = ("The content already in TrACE.html is kept. "
                           "Choose a file to replace it, or ✕ to remove "
                           "it.")
                elif not value:
                    text = "Not chosen"
                elif status == "ok":
                    text = shorten_path(shown_path, max_len)
                else:
                    text = f"{icon} {shorten_path(shown_path, max_len)}"
                widget["path"].configure(
                    text=text,
                    foreground=status_color if status in ("warn", "error")
                               else widget["path_color"]
                )

            widget["path_tip"].text = tip or "Not chosen yet"
            widget["choose"].configure(text="Change…" if value
                                       else "Choose…")
            if "remove" in widget:
                if value or kept:
                    widget["remove"].grid()
                else:
                    widget["remove"].grid_remove()

        path_state["missing"] = missing
        path_state["has_errors"] = has_errors
        update_run_hint()

    def differs_from_page(option):
        """
        Whether a page option differs from the existing page; colors are
        compared in any hex form (e.g. "#F00" is "#ff0000")
        """
        if option not in existing_page["options"]:
            return False
        value = gui_vars[option].get()
        if option in dict(PAGE_COLORS):
            value = normalize_color(value) or value
        return value != existing_page["options"][option]

    def update_change_markers(*args):
        """
        Show ↶ next to the page options (texts and colors) that differ from
        the existing page, with the page's value in its tooltip
        """
        # Not all markers are created yet
        if len(change_markers) < len(PAGE_TEXTS) + len(PAGE_COLORS):
            return

        color_titles = dict(PAGE_COLORS)
        for option, _ in PAGE_TEXTS + PAGE_COLORS:
            button, tip = change_markers[option]
            if differs_from_page(option):
                button.configure(text="↶")
                button.state(["!disabled"])
                page_value = existing_page["options"][option]
                # The colors share one label, so say which color it is, and
                # show it
                if option in color_titles:
                    tip.text = (f"Changed: the page's "
                                f"{color_titles[option].lower()} is "
                                f"{{color}}{page_value}.\n"
                                "Click to restore it.")
                    tip.color = page_value
                else:
                    tip.text = (f"Changed: the page has “{page_value}”.\n"
                                "Click to restore it.")
            else:
                button.configure(text="")
                button.state(["disabled"])
                tip.text = ""

    def update_run_hint(*args):
        """
        Show the hint next to Run, and enable Run if the paths are fine

        Uses the results of the last check of the paths (see
        refresh_paths()).
        """
        if "button" not in run_controls:
            return

        def join(names):
            """E.g. 'audio folder, ELAN folder and speakers CSV file'"""
            if len(names) > 1:
                return ", ".join(names[:-1]) + " and " + names[-1]
            return names[0]

        missing = path_state["missing"]
        has_errors = path_state["has_errors"]
        if missing:
            hint = f"To continue, choose the {join(missing)}."
        elif has_errors:
            hint = "To continue, fix the problems marked ✗."
        else:
            hint = "Ready to create your TrACE page."

        run_controls["hint"].configure(text=hint)
        run_controls["button"].state(
            ["disabled"] if (missing or has_errors) else ["!disabled"]
        )

    def add_path_var(var_name, label_text, filetypes, required, kind):
        """Create the variable for a path, and the common widget info"""

        if (var_name == "output_dir"):
            var = tk.StringVar(value=DEFAULTS[var_name])
        else:
            var = tk.StringVar()
        gui_vars[var_name] = var
        var.trace_add("write", refresh_paths)

        if filetypes is None:
            command = lambda v=var: browse_folder(v)
        else:
            command = lambda v=var, t=filetypes: browse_file(v, t)

        widget = {"kind": kind, "label": label_text, "filetypes": filetypes,
                  "required": required, "path_color": MUTED_COLOR}
        path_widgets[var_name] = widget
        return var, command, widget

    def remove_path(var, widget):
        """Remove a chosen file, and the info section kept from the page
        (✕)"""
        widget["keep"] = False
        var.set("")

    def add_choose_buttons(parent, var, command, widget, row, column,
                           removable=True):
        """Add the Choose/Change button, and optionally the ✕ button"""
        widget["choose"] = ttk.Button(parent, width=8, style="Card.TButton",
                                      command=command)
        widget["choose"].grid(row=row, column=column, padx=(px(8), 0))

        if removable:
            widget["remove"] = ttk.Button(parent, text="✕", width=2,
                                          style="Ghost.TButton",
                                          command=lambda v=var, w=widget:
                                              remove_path(v, w))
            widget["remove"].grid(row=row, column=column + 1,
                                  padx=(px(2), 0))
            Tooltip(widget["remove"], text="Remove", waittime=50)

    def add_path_card(parent, row, column,
                      var_name, label_text, filetypes, required):
        """A card with an icon, the name, the status and the path"""

        var, command, widget = add_path_var(var_name, label_text, filetypes,
                                            required, "card")

        frame = make_card(parent)
        frame.grid(row=row, column=column, sticky="nsew", padx=px(4),
                   pady=px(4))
        widget["frame"] = frame

        widget["icon"] = tk.Canvas(frame, width=px(32), height=px(32),
                                   bg=CARD_BG, highlightthickness=0)
        widget["icon"].grid(row=0, column=0, rowspan=2, padx=(0, px(12)))
        widget["icon_size"] = 32

        title = ttk.Label(frame, text=label_text, style="CardTitle.TLabel")
        title.grid(row=0, column=1, sticky="w")
        Tooltip(title, text=HELP_STRINGS[var_name], waittime=50)

        widget["status"] = ttk.Label(frame, style="Card.TLabel")
        widget["status"].grid(row=0, column=2, columnspan=3, sticky="e")

        widget["path"] = ttk.Label(frame, style="Card.TLabel")
        widget["path"].grid(row=1, column=1, columnspan=2, sticky="w")
        widget["path_tip"] = Tooltip(widget["path"], text="", waittime=50)

        add_choose_buttons(frame, var, command, widget, row=1, column=3)

        frame.columnconfigure(2, weight=1)

    def add_path_row(parent, row, column, var_name, label_text, filetypes):
        """A smaller one-line card for an optional file"""

        var, command, widget = add_path_var(var_name, label_text, filetypes,
                                            False, "row")

        frame = make_card(parent)
        frame.configure(pady=px(6))
        frame.grid(row=row, column=column, sticky="nsew", padx=px(4),
                   pady=px(4))
        widget["frame"] = frame

        # A smaller icon, centered in a column as wide as the big icons
        # (plus spacing), so that the names line up with the card titles above
        widget["icon"] = tk.Canvas(frame, width=px(20), height=px(20),
                                   bg=CARD_BG, highlightthickness=0)
        widget["icon"].grid(row=0, column=0, padx=(0, px(12)))
        widget["icon_size"] = 20
        frame.columnconfigure(0, minsize=px(32 + 12))

        title = ttk.Label(frame, text=label_text, style="CardTitle.TLabel")
        title.grid(row=0, column=1, sticky="w", padx=(0, px(6)))
        Tooltip(title, text=HELP_STRINGS[var_name], waittime=50)

        ttk.Label(frame, text="optional", style="Card.TLabel").grid(
            row=0, column=2, sticky="w", padx=(0, px(12))
        )

        widget["path"] = ttk.Label(frame, style="Card.TLabel")
        widget["path"].grid(row=0, column=3, sticky="w")
        widget["path_tip"] = Tooltip(widget["path"], text="", waittime=50)

        add_choose_buttons(frame, var, command, widget, row=0, column=4)
        frame.columnconfigure(3, weight=1)

    # Cards in two columns: the input files, then the optional files
    for i, (var_name, title, filetypes) in enumerate(INPUT_FILES):
        add_path_card(paths_frame, i // 2, i % 2, var_name, title, filetypes,
                      required=True)

    first_row = (len(INPUT_FILES) + 1) // 2
    for i, (var_name, title, filetypes) in enumerate(OPTIONAL_FILES):
        add_path_row(paths_frame, first_row + i // 2, i % 2, var_name, title,
                     filetypes)

    paths_frame.columnconfigure((0, 1), weight=1, uniform="cards")

    # ------------------------------------------------------------------
    # PAGE OPTIONS
    # ------------------------------------------------------------------

    # One card with a grid of fields, two per row, ending with the colors:
    #
    #   Browser tab title [      ] ↶    Page header [      ] ↶
    #   Notes tier in ELAN [     ] ↶    Colors      [■]↶ [■]↶ [■]↶ Use defaults
    #
    # ↶ only appears when a field differs from the existing page, and
    # restores the page's value (see update_change_markers()).
    #
    # Columns: label, field, ↶, gap, label, field, ↶. Field number i is in
    # row i // 2, and starts in column 0 or 4
    options_card = make_card(options_frame, padding=14)
    options_card.grid(row=0, column=0, sticky="ew", padx=px(4), pady=px(4))
    options_frame.columnconfigure(0, weight=1)
    options_card.columnconfigure((1, 5), weight=1, uniform="fields")
    options_card.columnconfigure(3, minsize=px(20))

    # Undo buttons (↶): option name -> (button, tooltip)
    change_markers = {}

    def add_change_marker(option, parent, row, column):
        """
        Add an undo button (↶) for a page option, hidden until the option
        differs from the page; it restores the page's value

        The button always stays in place, with the same size, and is only
        emptied and disabled when hidden, so that nothing moves when it
        appears.
        """
        button = ttk.Button(parent, text="", width=2, style="Link.TButton",
                            command=lambda: restore_from_page(option))
        button.grid(row=row, column=column, sticky="w", padx=(px(2), 0))
        button.state(["disabled"])
        change_markers[option] = (button, Tooltip(button, text="",
                                                  waittime=50))

    def restore_from_page(option):
        """Set a page option back to the value of the existing page (↶)"""
        if option in existing_page["options"]:
            gui_vars[option].set(existing_page["options"][option])

    def option_label(text, row, column, help_text):
        """Add a label with a tooltip to the page options grid"""
        label = ttk.Label(options_card, text=text, style="CardText.TLabel")
        label.grid(row=row, column=column, sticky="w", padx=(0, px(12)),
                   pady=px(4))
        Tooltip(label, text=help_text, waittime=50)

    def option_cell(i):
        """Row and first column of field number i in the grid"""
        return i // 2, (i % 2) * 4

    for i, (var_name, label_text) in enumerate(PAGE_TEXTS):
        row, column = option_cell(i)
        option_label(label_text, row, column, HELP_STRINGS[var_name])

        var = tk.StringVar(value=DEFAULTS[var_name])
        gui_vars[var_name] = var

        entry = ttk.Entry(
            options_card,
            textvariable=var,
            width=20
        )
        entry.grid(row=row, column=column + 1, sticky="ew", pady=px(4))
        # Unfocus on Enter key
        entry.bind("<Return>", unfocus_entry)

        add_change_marker(var_name, options_card, row, column + 2)

    # COLORS: one row of clickable swatches

    color_vars = [var_name for var_name, _ in PAGE_COLORS]

    def pick_color(event, var):
        """Open the color picker for a swatch"""
        color = colorchooser.askcolor(color=var.get())[1]
        if color:
            # The swatch is updated by the trace on the variable
            var.set(color)

    def reset_colors():
        for k in color_vars:
            gui_vars[k].set(DEFAULTS[k])

    # The colors take the grid cell after the texts
    colors_row, colors_column = option_cell(len(PAGE_TEXTS))
    option_label("Colors", colors_row, colors_column,
                 "Colors of the TrACE page. Hover over a color for details, "
                 "and click it to change it.")

    swatches_frame = tk.Frame(options_card, bg=CARD_BG)
    swatches_frame.grid(row=colors_row, column=colors_column + 1, sticky="w")

    for i, (var_name, color_label) in enumerate(PAGE_COLORS):
        color_var = tk.StringVar(value=DEFAULTS[var_name])
        gui_vars[var_name] = color_var

        swatch = tk.Label(
            swatches_frame,
            bg=color_var.get(),
            width=3,
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            cursor="hand2"
        )
        swatch.grid(row=0, column=2 * i)
        add_change_marker(var_name, swatches_frame, 0, 2 * i + 1)
        tip = Tooltip(swatch, text="", waittime=50)

        def update_swatch(*args, v=color_var, s=swatch, t=tip,
                          name=color_label, help_text=HELP_STRINGS[var_name]):
            s.configure(bg=v.get())
            t.text = f"{name}: {v.get()}\n{help_text}\n\nClick to change"

        color_var.trace_add("write", update_swatch)
        update_swatch()

        swatch.bind(
            "<Button-1>",
            lambda event, v=color_var: pick_color(event, v)
        )

    reset_button = ttk.Button(
        swatches_frame,
        text="Use defaults",
        style="Card.TButton",
        command=reset_colors,
    )
    reset_button.grid(row=0, column=2 * len(PAGE_COLORS), padx=(px(4), 0))
    Tooltip(reset_button, text="Go back to the default colors", waittime=50)

    def update_reset_button(*args):
        # Only enabled when some color differs from its default
        changed = any(gui_vars[k].get().lower() != DEFAULTS[k].lower()
                      for k in color_vars)
        reset_button.state(["!disabled"] if changed else ["disabled"])

    for var_name in color_vars:
        gui_vars[var_name].trace_add("write", update_reset_button)
    update_reset_button()

    # ------------------------------------------------------------------
    # Bottom bar: output folder and the Run button
    # ------------------------------------------------------------------

    # A white bar with a thin line above it; the right edge lines up with
    # the cards
    footer = tk.Frame(root, bg=CARD_BG)
    # Packed before the body, so that the body shrinks first when the
    # window gets smaller
    footer.pack(fill="x", side="bottom", before=body)
    tk.Frame(footer, height=1, bg=CARD_BORDER).pack(fill="x")

    button_frame = ttk.Frame(footer, style="Card.TFrame",
                             padding=(px(20), px(12), px(20), px(12)))
    button_frame.pack(fill="x")

    # Output folder
    var, command, widget = add_path_var(*OUTPUT_FOLDER, FOLDER, True, "bar")
    widget["path_color"] = TEXT_COLOR

    # A small caption above the path, and everything else on the line of
    # the path: folder icon, path, Change button, hint and Run button
    widget["icon"] = tk.Canvas(button_frame, width=px(20), height=px(20),
                               bg=CARD_BG, highlightthickness=0)
    widget["icon"].grid(row=1, column=0, padx=(0, px(8)))
    widget["icon_size"] = 20

    caption = ttk.Label(button_frame, text="SAVE TO", style="Caption.TLabel")
    caption.grid(row=0, column=1, sticky="w")
    # The tooltip also says that the files are remembered from the last
    # run (see load_output_folder())
    caption_tip = Tooltip(caption, text=HELP_STRINGS[OUTPUT_FOLDER[0]],
                          waittime=50)

    widget["path"] = ttk.Label(button_frame, style="CardText.TLabel")
    widget["path"].grid(row=1, column=1, sticky="w")
    widget["path_tip"] = Tooltip(widget["path"], text="", waittime=50)

    add_choose_buttons(button_frame, var, command, widget, row=1, column=2,
                       removable=False)
    widget["choose"].grid(padx=(px(16), 0))

    # Run button, with a hint about what's missing
    run_controls["hint"] = ttk.Label(button_frame, style="Card.TLabel",
                                     wraplength=px(300), justify="right")
    run_controls["hint"].grid(row=1, column=5, sticky="e", padx=px(12))

    run_controls["button"] = ttk.Button(
        button_frame,
        text="Run",
        style="Accent.TButton",
        width=10,
        command=lambda v=gui_vars: on_run(v)
    )
    run_controls["button"].grid(row=1, column=6, sticky="e")

    def load_output_folder(*args):
        """
        Fill in the fields from the previous run in the output folder, and
        note which info sections (help, licence, logos) the existing page
        has

        The page options come from the existing page, and the files from
        the settings of the last successful run (see
        processing.read_previous_settings()). The info sections of the page
        are kept unless a file is chosen or ✕ is clicked.
        """
        output_dir = gui_vars[OUTPUT_FOLDER[0]].get().strip() or "."
        settings, origins = read_previous_settings(output_dir)
        for option, value in settings.items():
            if option in gui_vars and value is not None:
                gui_vars[option].set(value)

        info_sections = read_TrACE_info_sections(get_TrACE_file(output_dir))
        for var_name, _, _ in OPTIONAL_FILES:
            # A section removed in the last run ("") stays removed
            path_widgets[var_name]["keep"] = (var_name in info_sections and
                                              settings.get(var_name) != "")

        # Mention in the tooltip of SAVE TO that the files are remembered
        # (the page options come from the page, which needs no explanation)
        tip = HELP_STRINGS[OUTPUT_FOLDER[0]]
        if LAST_RUN_FILE in origins.values():
            tip += (f"\n\nThe files are remembered from the last successful "
                    f"run in this folder, in {LAST_RUN_FILE}, next to the "
                    "TrACE folder (it is not part of the TrACE folder).")
        caption_tip.text = tip

        # The page options of the existing page, to show ↶ next to fields
        # that differ from them
        read_existing_page()

        refresh_paths()

    def read_existing_page():
        """Read the page options of the existing page in the output folder"""
        output_dir = gui_vars[OUTPUT_FOLDER[0]].get().strip() or "."
        existing_page["options"] = read_TrACE_options(
            get_TrACE_file(output_dir))
        update_change_markers()

    gui_vars[OUTPUT_FOLDER[0]].trace_add("write", load_output_folder)
    load_output_folder()

    # Changing a page option shows or hides its ↶
    for option, _ in PAGE_TEXTS + PAGE_COLORS:
        gui_vars[option].trace_add("write", update_change_markers)

    button_frame.columnconfigure(5, weight=1)

    refresh_paths()

    # Fit the window to its contents, but not taller than the screen (with
    # some room for the taskbar and the title bar), and center it
    root.update_idletasks()
    width = max(px(900), main_frame.winfo_reqwidth() + px(20))
    height = (header_frame.winfo_reqheight() + main_frame.winfo_reqheight() +
              footer.winfo_reqheight())
    height = min(height, root.winfo_screenheight() - px(100))
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2 - px(30))
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(width, min(height, px(450)))

    root.mainloop()