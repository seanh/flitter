A script for launching apps and switching windows.

Requires wmctrl: <http://tomas.styblo.name/wmctrl/>  
On Ubuntu:

    $ sudo apt-get install wmctrl


Usage
-----

For example, to go to Firefox do:

    runraisenext.py firefox

This will:

* launch Firefox, if Firefox is not already open
* focus the Firefox window, if Firefox is already open but not focused
* focus the next Firefox window, if there are multiple Firefox windows
  open and one of them is already focused.

Bind this command to a keyboard shortcut, e.g. F2, and you can always press F2
to get to Firefox, whether Firefox is running or not. If there are multiple
Firefox windows, just keep hitting F2 until you get to the one you want.
It will even restore minimized windows and switch between desktops, if you have
Firefox windows open on different desktops.

If you bind different commands to different keys, e.g.:

    F1: runraisenext.py terminal
    F2: runraisenext.py firefox
    F3: runraisenext.py gvim

then you can use F1, F2, and F3 to switch between Terminal, Firefox and gVim
as you work.

The arguments that you can give on the command line (terminal, firefox, gvim,
etc.) must be defined in a `~/.flitter.json` file. For example:

    {
        "Terminal": {
            "wm_class": ".Gnome-terminal",
            "command": "gnome-terminal"
        },
        "Firefox": {
            "wm_class": ".Firefox",
            "command": "firefox"
        },
        "gVim": {
            "wm_class": ".Gvim",
            "command": "gvim"
        }
    }

Each of these JSON objects is a **window specification**, telling
`runraisenext.py` how to identify which windows belong to the given app.
The Firefox spec above tells `runraisenext.py` to focus or cycle through any
windows whose WM_CLASS contains the string ".Firefox", or to run the command
`firefox` if there are no matching windows.

A window spec can take up to 6 attributes to match windows against:

`window_id`
  The unique ID of an open window, e.g. 0x0180000b

`desktop`
  The desktop that the window is on, e.g. 1

`pid`
  The process ID of the window, e.g. 3384

`wm_class`
  The WM_CLASS of the window, e.g. Navigator.Firefox

`machine`
  The client machine that the window belongs to

`title`
  The window title

If you want to add your own window specs to the `~/.flitter.json` file,
use the `wmctrl -lxp` command to see what attributes to match against.
Usually the second half of the WM_CLASS (the part after the dot, e.g.
".Firefox" in "Navigator.Firefox") will match all windows belonging to a given
app.

Any of the properties of a window spec can also be given as command-line
arguments. For example, instead of:

    runraisenext.py firefox

you can do:

    runraisenext.py --wm_class .Firefox --command firefox

Any options given on the command line will override those from the config
file. See `runraisenext.py -h` for a full list of command-line options.

If multiple window attributes are given `runraisenext.py` will match against
all of them at once. For example, to go to the Nautilus file browser window for
the Foobar folder, do:

    runraisenext.py --wm_class .Nautilus --title Foobar

To cycle through all open windows without matching windows, do:

    runraisenext.py --all
