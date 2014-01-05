#!/usr/bin/env python2
"""A script for launching apps and switching windows.

FIXME: Something is going wrong when there are no open windows on the current
       desktop.

"""
import argparse
import subprocess
import json
import os


class Window:
    """A simple class to represent an open window.

    """
    def __init__(self, line):
        """

        :param line: a line representing a window from the output of
                     wmctrl -lxp
        :type line: string

        """
        self.line = line
        parts = line.split(None, 5)
        assert len(parts) in (5,6)
        self.window_id = parts[0]
        self.desktop = parts[1]
        self.pid = parts[2]
        self.wm_class = parts[3]
        self.machine = parts[4]
        if len(parts) == 6:
            self.title = parts[5].strip()
        else:
            self.title = ''

    def __eq__(self, other):

        if not hasattr(other, "window_id"):
            return False

        return self.window_id == other.window_id

    def __repr__(self):
        return self.line

    def matches(self, spec):
        """Return True if this window matches the given window spec,
        False otherwise.

        :param spec: a window spec dictionary containing 0 or more of the keys:
                     "window_id", "desktop", "pid", "wm_class", "machine",
                     "title", all of the values should be strings
        :type spec: dictionary

        """
        for key in spec.keys():
            if key == 'command':
                continue
            if spec[key].lower() not in getattr(self, key, '').lower():
                return False
        return True

    def focus(self):
        """Focus this window.

        """
        # Focus this window.
        subprocess.call(["wmctrl", "-i", "-a", self.window_id])


def run_command(window_spec):
    """Run the shell command from the given window_sped as a subprocess."""
    command = window_spec.get("command")
    if command:
        subprocess.call(command, shell=True)


def get_open_windows():
    """Return a list of Window objects for all currently open windows.

    """
    output = subprocess.check_output(["wmctrl", "-lxp"])

    # FIXME: We assume utf8 here, which is probably bad.
    lines = [line.decode("utf8") for line in output.split("\n")]

    windows = []
    for line in lines:
        if not line:
            continue
        windows.append(Window(line))

    # Remove Nautilus's desktop window.
    # TODO: Make this a configurable list of excludes.
    windows = [window for window in windows
               if not window.matches({"wm_class": "desktop_window.Nautilus"})]

    return windows


def get_matching_windows(open_windows, window_spec):
    """Return the list of windows from open_windows that match window_spec.

    """
    matching_windows = [window for window in open_windows
                        if window.matches(window_spec)]
    return matching_windows


def get_current_window(open_windows):
    """Return the currently focused window.

    :rtype: Window object

    """
    # wmctrl doesn't provide a good way to get the currently focused window,
    # but this works.
    output = subprocess.check_output(["wmctrl", "-a", ":ACTIVE:", "-v"],
                                     stderr=subprocess.STDOUT)

    # FIXME: We assume utf8 here, which is probably bad.
    lines = [line.decode("utf8") for line in output.split("\n")]

    assert len(lines) == 3
    window_id = lines[1].split()[-1]
    matching_windows = [window for window in open_windows
                        if window.window_id == window_id]
    assert len(matching_windows) == 1
    current_window = matching_windows[0]
    return current_window


def loop(matching_windows, current_window):

    assert current_window in matching_windows
    assert len(matching_windows) > 1

    # Find the next window after current_window in matching_windows
    # and focus it, looping back to the start of matching_windows if necessary.
    index = matching_windows.index(current_window) + 1
    if index >= len(matching_windows):
        index = 0
    window_to_focus = matching_windows[index]
    assert window_to_focus != current_window
    window_to_focus.focus()


def get_window_spec_from_file(alias):
    """Get the requested window spec from the ~/.runraisenext.json file.

    :rtype: dictionary

    """
    specs = json.loads(
            open(
                os.path.abspath(
                    os.path.expanduser("~/.runraisenext.json")),
                'r').read()
            )
    lowercased_specs = {}
    for key in specs:
        assert key.lower() not in lowercased_specs
        lowercased_specs[key.lower()] = specs[key]
    spec = lowercased_specs[alias.lower()]
    return spec


def main():
    """Parse the command-line arguments and kick off the necessary actions.

    """
    parser = argparse.ArgumentParser(
        description="a script for launching apps and switching windows",
        add_help=True)

    window_spec_args = parser.add_argument_group("window spec")
    window_spec_args.add_argument('-i', '--id', dest="window_id",
        help="the window ID to look for, e.g. 0x0180000b")
    window_spec_args.add_argument('-d', '--desktop',
        help="the desktop to look for windows on, e.g. 1")
    window_spec_args.add_argument('-p', '--pid',
        help="the pid to look for, e.g. 3384")
    window_spec_args.add_argument('-w', '--wm_class',
        help="the WM_CLASS to look for, e.g. Navigator.Firefox")
    window_spec_args.add_argument('-m', '--machine',
        help="the client machine name to look for")
    window_spec_args.add_argument('-t', '--title',
        help='the window title to look for, e.g. "wmctrl - A command line tool to interact with an EWMH/NetWM compatible X Window Manager. - Mozilla Firefox"')

    parser.add_argument('-c', '--command',
        help="The command to run to launch the app, if no matching windows are found, e.g. firefox")

    parser.add_argument('alias', nargs='?',
        help="the alias of a window spec from the config file to use for"
             "matching windows")

    # TODO: More command-line options:
    # -a, --all
    # -c, --current
    # -f, --file (select a non-default config file)

    args = parser.parse_args()

    if args.window_id is not None:
        if (args.desktop or args.pid or args.wm_class or args.machine
            or args.title):
            parser.exit(status=1, message="A window ID uniquely identifies "
                                           "a window, it doesn't make sense "
                                           "to give the -i, --id argument at "
                                           "the same time as any other window "
                                           "spec arguments")

    # Form the window spec dict.
    if args.alias:
        window_spec = get_window_spec_from_file(args.alias)
    else:
        window_spec = {}
    if args.window_id is not None:
        window_spec['id'] = args.window_id
    if args.desktop is not None:
        window_spec['desktop'] = args.desktop
    if args.pid is not None:
        window_spec['pid'] = args.pid
    if args.wm_class is not None:
        window_spec['wm_class'] = args.wm_class
    if args.machine is not None:
        window_spec['machine'] = args.machine
    if args.title is not None:
        window_spec['title'] = args.title
    if args.command is not None:
        window_spec['command'] = args.command

    # If no window spec options were given, just run the command
    # (if there is one).
    if ('id' not in window_spec and
        'desktop' not in window_spec and
        'pid' not in window_spec and
        'wm_class' not in window_spec and
        'machine' not in window_spec and
        'title' not in window_spec):
        run_command(window_spec)
        return

    open_windows = get_open_windows()

    # If there are no open windows, just run the command (if there is one).
    if not open_windows:
        run_command(window_spec)
        return

    matching_windows = get_matching_windows(open_windows, window_spec)

    if not matching_windows:
        # The requested app is not open, launch it.
        run_command(window_spec)
        return

    current_window = get_current_window(open_windows)

    if current_window not in matching_windows:
        # The app is open but is not focused, focus it.
        matching_windows[0].focus()
    elif len(matching_windows) == 1:
        # The app has one window open and it's already focused, do nothing.
        pass
    else:
        # The app has multiple windows open, and one of them is already
        # focused, focus the next matching window.
        loop(matching_windows, current_window)


if __name__ == "__main__":
    main()
