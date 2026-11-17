import tkinter as tk
import tkinter.font as tkFont
from tkinter import colorchooser, filedialog, ttk
from pathlib import Path
import re

from constants import HELP_STRINGS, DEFAULTS
from processing import do_processing

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


    def browse_file(entry_widget):
        """Select a file"""

        cur_entry = entry_widget.get()

        if (Path(cur_entry).is_file()):
            initial_dir = Path(cur_entry).parent
        else:
            initial_dir = Path.cwd()

        choice = filedialog.askopenfilename(title="Select File", 
                                            filetypes=[('CSV Files', 
                                                        '*.csv'),
                                                        ('All Files', 
                                                        '*.*')],
                                            initialdir=initial_dir)

        if choice:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, choice)

    def browse_folder(entry_widget):
        """Select a folder"""

        cur_entry = entry_widget.get()
        if (Path(cur_entry).is_dir()):
            initial_dir = Path(cur_entry)
        else:
            initial_dir = Path.cwd()


        choice = filedialog.askdirectory(title="Select Folder",
                                        initialdir=initial_dir
                                        )

        if choice:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, choice)

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
    root.geometry("950x640")
    root.minsize(950,640)

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
        text="1. Input Paths",
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
    
    path_vars = ["audio_dir", "elan_dir", "speakers_info_file",
                 "recordings_info_file", 
                 "help_file", "licence_file", "logos_file",
                 "output_dir"]
    path_labels = ["Audio folder", "Elan folder", 
                   "Speakers CSV file", "Recordings CSV file",
                   "Help file (optional)", "Licence file (optional)",
                   "Logos CSV file (optional)",
                   "Output folder"]
    path_tooltips = [
        HELP_STRINGS["audio_dir"],
        HELP_STRINGS["elan_dir"],
        HELP_STRINGS["speakers_info_file"],
        HELP_STRINGS["recordings_info_file"],
        HELP_STRINGS["help_file"],
        HELP_STRINGS["licence_file"],
        HELP_STRINGS["logos_file"],
        HELP_STRINGS["output_dir"]
        ]

    for i, var_name in enumerate(path_vars):

        label = ttk.Label(paths_frame, text=f"ⓘ {path_labels[i]}:") 
        label.grid(
            row=i, column=0, sticky="w", pady=5
        )
        Tooltip(label, text=path_tooltips[i], waittime=50)

        if (var_name == "output_dir"):
            var = tk.StringVar(value=DEFAULTS[var_name])
        else:
            var = tk.StringVar()
            
        gui_vars[var_name] = var

        entry = ttk.Entry(paths_frame, textvariable=var, width=50)
        entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
        # Unfocus on Enter key
        entry.bind("<Return>", unfocus_entry)

        if re.search("folder", path_labels[i]):
            ttk.Button(
                paths_frame,
                text="Browse...",
                style="Small.TButton",
                command=lambda e=entry: browse_folder(e)
            ).grid(row=i, column=2, ipady=0, pady=5)
        else:
            ttk.Button(
                paths_frame,
                text="Browse...",
                style="Small.TButton",
                command=lambda e=entry: browse_file(e)
            ).grid(row=i, column=2, ipady=0, pady=5)
        
    paths_frame.columnconfigure(1, weight=1)

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
        label = ttk.Label(titles_frame, text=f"ⓘ {text_labels[i]}:")
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
            text=f"ⓘ {color_labels[i]}:"
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

    checkbox_frame = ttk.Frame(outputs_frame, height=100)
    checkbox_frame.grid(row=0, column=0, sticky="w", pady=5)

    checkbox_vars = ["copy_audio", "generate_data", "generate_html"]
    checkbox_labels = ["Copy audio files", 
                        "Recreate data", 
                        "Recreate HTML file"]

    checkbox_tooltips = [
        ("If checked, audio files will be copied from the input audio folder to " +
        "TrACE audio folder. Uncheck if the audios already have been copied and " +
        "don't need to be updated."),

        ("If checked, data files will not be re-created. As data creation is " +
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

    ttk.Button(
        button_frame,
        text="Run",
        style="Custom.TButton",
        command=lambda v=gui_vars: on_run(v)
    ).pack(side="right")

    root.mainloop()