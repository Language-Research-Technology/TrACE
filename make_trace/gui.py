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
                    wraplength=None):

            self.waittime = waittime  # in miliseconds, originally 500
            # in pixels, originally 180; wide enough for a few short lines
            self.wraplength = wraplength or px(420)
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
    # Secondary text: the lightest grey with enough contrast for reading
    # (4.5:1, WCAG AA) on both the white cards and the grey background
    muted_color = "#687078"
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
    # Small grey uppercase captions, e.g. "SAVE TO"
    style.configure("Caption.TLabel", background=card_bg,
                    foreground=muted_color, font=(font_family, 8, "bold"))
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
    # Disabled buttons keep their shape, with lighter text and no hover
    style.map(
        "Card.TButton",
        foreground=[("disabled", "#adb5bd")],
        background=[("disabled", button_bg), ("active", button_hover)],
        lightcolor=[("disabled", button_bg), ("active", button_hover)],
        darkcolor=[("disabled", button_bg), ("active", button_hover)]
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
        foreground=accent_color
    ).grid(row=0, column=0, padx=(0, px(6)))
    ttk.Label(
        tip_frame,
        text="Hover over any name to see what it's for",
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

    body_canvas = tk.Canvas(body, bg=bg_color, highlightthickness=0,
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

    path_widgets = {}

    # Filled in when the Run button is created at the bottom
    run_controls = {}

    def refresh_paths(*args):
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

            if "icon" in widget:
                draw_icon(widget["icon"], widget["filetypes"],
                          icon_colors["set" if value else "empty"],
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
                # it goes into the tooltip, and only problems are coloured
                max_len = 18 if kind == "row" else 32
                shown_path = full_path
                if kind == "bar" and value:
                    shown_path = str(Path(full_path).joinpath("TrACE"))
                if not value:
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
                if value:
                    widget["remove"].grid()
                else:
                    widget["remove"].grid_remove()

        if "button" not in run_controls:
            return

        if missing:
            if len(missing) > 1:
                missing = [", ".join(missing[:-1]), missing[-1]]
            hint = f"To continue, choose the {' and '.join(missing)}."
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
                  "required": required, "path_color": muted_color}
        path_widgets[var_name] = widget
        return var, command, widget

    def add_choose_buttons(parent, var, command, widget, row, column,
                           removable=True):
        widget["choose"] = ttk.Button(parent, width=8, style="Card.TButton",
                                      command=command)
        widget["choose"].grid(row=row, column=column, padx=(px(8), 0))

        if removable:
            widget["remove"] = ttk.Button(parent, text="✕", width=2,
                                          style="Ghost.TButton",
                                          command=lambda v=var: v.set(""))
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
                                   bg=card_bg, highlightthickness=0)
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
                                   bg=card_bg, highlightthickness=0)
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

    for i, spec in enumerate([
        ("audio_dir", "Audio folder", None, True),
        ("elan_dir", "ELAN folder", None, True),
        ("speakers_info_file", "Speakers CSV file", csv_types, True),
        ("recordings_info_file", "Recordings CSV file", csv_types, True),
    ]):
        add_path_card(paths_frame, i // 2, i % 2, *spec)

    # Optional files, as smaller cards below
    add_path_row(paths_frame, 2, 0, "help_file", "Help file", md_types)
    add_path_row(paths_frame, 2, 1, "licence_file", "Licence file", md_types)
    add_path_row(paths_frame, 3, 0, "logos_file", "Logos CSV file",
                 csv_types)

    paths_frame.columnconfigure((0, 1), weight=1, uniform="cards")

    # ------------------------------------------------------------------
    # PAGE OPTIONS
    # ------------------------------------------------------------------

    # One card with a 2x2 grid of fields:
    #
    #   Browser tab title [      ]    Page header [      ]
    #   Notes tier in ELAN [     ]    Colors      [■] [■] [■] Reset
    #
    # Columns: label, field, gap, label, field
    options_card = make_card(options_frame, padding=14)
    options_card.grid(row=0, column=0, sticky="ew", padx=px(4), pady=px(4))
    options_frame.columnconfigure(0, weight=1)
    options_card.columnconfigure((1, 4), weight=1, uniform="fields")
    options_card.columnconfigure(2, minsize=px(28))

    def option_label(text, row, column, help_text):
        label = ttk.Label(options_card, text=text, style="CardText.TLabel")
        label.grid(row=row, column=column, sticky="w", padx=(0, px(12)),
                   pady=px(4))
        Tooltip(label, text=help_text, waittime=50)

    # (var name, label, row, column)
    text_fields = [
        ("title", "Browser tab title", 0, 0),
        ("header", "Page header", 0, 3),
        ("ann_note_tier", "Notes tier in ELAN", 1, 0),
    ]

    for var_name, label_text, row, column in text_fields:
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

    # COLORS: one row of clickable swatches

    colour_vars = ["primary_color", "ann_highlight_color", "filter_match_color"]
    color_labels = ["Interface color", "Current annotation color",
                    "Filter match color"]

    def pick_colour(event, var):
        colour = colorchooser.askcolor(color=var.get())[1]
        if colour:
            # The swatch is updated by the trace on the variable
            var.set(colour)

    def reset_colors():
        for k in colour_vars:
            gui_vars[k].set(DEFAULTS[k])

    option_label("Colors", 1, 3,
                 "Colors of the TrACE page. Hover over a color for details, "
                 "and click it to change it.")

    swatches_frame = tk.Frame(options_card, bg=card_bg)
    swatches_frame.grid(row=1, column=4, sticky="w")

    for i, var_name in enumerate(colour_vars):
        colour_var = tk.StringVar(value=DEFAULTS[var_name])
        gui_vars[var_name] = colour_var

        swatch = tk.Label(
            swatches_frame,
            bg=colour_var.get(),
            width=3,
            highlightthickness=1,
            highlightbackground=card_border,
            cursor="hand2"
        )
        swatch.grid(row=0, column=i, padx=(0, px(6)))
        tip = Tooltip(swatch, text="", waittime=50)

        def update_swatch(*args, v=colour_var, s=swatch, t=tip,
                          name=color_labels[i], help_text=HELP_STRINGS[var_name]):
            s.configure(bg=v.get())
            t.text = f"{name}: {v.get()}\n{help_text}\n\nClick to change"

        colour_var.trace_add("write", update_swatch)
        update_swatch()

        swatch.bind(
            "<Button-1>",
            lambda event, v=colour_var: pick_colour(event, v)
        )

    reset_button = ttk.Button(
        swatches_frame,
        text="Reset",
        style="Card.TButton",
        command=reset_colors,
    )
    reset_button.grid(row=0, column=3, padx=(px(4), 0))
    Tooltip(reset_button, text="Go back to the default colors", waittime=50)

    def update_reset_button(*args):
        # Only enabled when some color differs from its default
        changed = any(gui_vars[k].get().lower() != DEFAULTS[k].lower()
                      for k in colour_vars)
        reset_button.state(["!disabled"] if changed else ["disabled"])

    for var_name in colour_vars:
        gui_vars[var_name].trace_add("write", update_reset_button)
    update_reset_button()

    # ------------------------------------------------------------------
    # Bottom bar: output folder, output options and the Run button
    # ------------------------------------------------------------------

    # A white bar with a thin line above it; the right edge lines up with
    # the cards
    footer = tk.Frame(root, bg=card_bg)
    # Packed before the body, so that the body shrinks first when the
    # window gets smaller
    footer.pack(fill="x", side="bottom", before=body)
    tk.Frame(footer, height=1, bg=card_border).pack(fill="x")

    button_frame = ttk.Frame(footer, style="Card.TFrame",
                             padding=(px(20), px(12), px(20), px(12)))
    button_frame.pack(fill="x")

    # Output folder
    var, command, widget = add_path_var("output_dir", "Output folder", None,
                                        True, "bar")
    widget["path_color"] = text_color

    # A small caption above the path, and everything else on the line of
    # the path: folder icon, path, Change button, hint and Run button
    widget["icon"] = tk.Canvas(button_frame, width=px(20), height=px(20),
                               bg=card_bg, highlightthickness=0)
    widget["icon"].grid(row=1, column=0, padx=(0, px(8)))
    widget["icon_size"] = 20

    caption = ttk.Label(button_frame, text="SAVE TO", style="Caption.TLabel")
    caption.grid(row=0, column=1, sticky="w")
    Tooltip(caption, text=HELP_STRINGS["output_dir"], waittime=50)

    widget["path"] = ttk.Label(button_frame, style="CardText.TLabel")
    widget["path"].grid(row=1, column=1, sticky="w")
    widget["path_tip"] = Tooltip(widget["path"], text="", waittime=50)

    add_choose_buttons(button_frame, var, command, widget, row=1, column=2,
                       removable=False)
    widget["choose"].grid(padx=(px(16), 0))

    # Output options, in a small window of their own, since they are
    # rarely changed
    checkbox_specs = [
        ("copy_audio", "Copy audio files",
         "Copy the audio files into the TrACE folder. Turn off if they have "
         "already been copied and haven't changed."),
        ("generate_data", "Recreate data",
         "Recreate the transcripts and speaker data. This is fast, so it "
         "can usually stay on."),
        ("generate_html", "Recreate the TrACE page",
         "Create the TrACE page from scratch. Turn off if you edited the "
         "page by hand and want to keep your changes."),
    ]

    for var_name, _, _ in checkbox_specs:
        gui_vars[var_name] = tk.BooleanVar(value=True)

    def open_output_options():
        dialog = tk.Toplevel(root, bg=card_bg, padx=px(20), pady=px(16))
        dialog.title("Output options")
        dialog.transient(root)
        dialog.resizable(False, False)

        for i, (var_name, label_text, explanation) in enumerate(
                checkbox_specs):
            ttk.Checkbutton(
                dialog,
                text=label_text,
                variable=gui_vars[var_name],
                style="Card.TCheckbutton"
            ).grid(row=2 * i, column=0, sticky="w",
                   pady=(px(10) if i else 0, 0))

            # Indented to line up with the checkbox text
            ttk.Label(
                dialog,
                text=explanation,
                style="Card.TLabel",
                wraplength=px(340),
                justify="left"
            ).grid(row=2 * i + 1, column=0, sticky="w", padx=(px(26), 0))

        ttk.Button(
            dialog,
            text="Close",
            style="Card.TButton",
            command=dialog.destroy
        ).grid(row=2 * len(checkbox_specs), column=0, sticky="e",
               pady=(px(16), 0))

        dialog.bind("<Escape>", lambda event: dialog.destroy())

        # Show it in the middle of the main window
        dialog.update_idletasks()
        x = root.winfo_rootx() + (root.winfo_width() -
                                  dialog.winfo_reqwidth()) // 2
        y = root.winfo_rooty() + (root.winfo_height() -
                                  dialog.winfo_reqheight()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.grab_set()

    options_button = ttk.Button(button_frame, style="Card.TButton",
                                command=open_output_options)
    options_button.grid(row=1, column=4, padx=(px(8), 0))

    def update_options_button(*args):
        # Show when some steps are turned off, so it's not forgotten
        n_off = sum(not gui_vars[v].get() for v, _, _ in checkbox_specs)
        options_button.configure(
            text=f"Options ({n_off} off)…" if n_off else "Options…"
        )

    for var_name, _, _ in checkbox_specs:
        gui_vars[var_name].trace_add("write", update_options_button)
    update_options_button()

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