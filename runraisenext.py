#!/usr/bin/env python2.7
"""A script for launching apps and switching windows.

TODO: Package it up, make it pip installable and with a default config file

"""
import sys
import argparse
import subprocess
import json
import os

import wmctrl


def run(command):
    """Run the given shell command as a subprocess."""
    subprocess.call(command, shell=True)


def run_window_spec_command(window_spec, run_function):
    """Run the command from the given window spec, if it has one.

    :param window_spec: the window spec whose command to run
    :type window_spec: dict

    :param run_function: the function to call to run the command
    :type run_function: callable

    """
    command = window_spec.get('command')
    if command:
        run_function(command)


def focus_window(window):
    """Focus the given window.

    :param window: the window to focus
    :type window: wmctrl.Window

    """
    window.focus()


def get_window_spec_from_file(alias, file_):
    """Get the requested window spec from the config file.

    :rtype: dictionary

    """
    specs = json.loads(open(file_, 'r').read())
    lowercased_specs = {}
    for key in specs:
        assert key.lower() not in lowercased_specs
        lowercased_specs[key.lower()] = specs[key]
    spec = lowercased_specs[alias.lower()]
    return spec


def loop(matching_windows, current_window, focus_window_function):
    """Focus the next window after current_window in matching_windows.

    If current_window is the last window in matching_windows, focus the first
    window in matching_windows.

    :param matching_windows: the list of windows matching the requested
        window spec
    :type matching_windows: list of wmctrl.Window objects

    :param current_window: the currently focused window, must be one of the
        windows from matching_windows
    :type current_window: wmctrl.Window

    :param focus_window_function: the function to call to focus a window
    :type focus_window_function: callable

    """
    assert current_window in matching_windows
    assert len(matching_windows) > 1

    # Find the next window after current_window in matching_windows
    # and focus it, looping back to the start of matching_windows if necessary.
    index = matching_windows.index(current_window) + 1
    if index >= len(matching_windows):
        index = 0
    window_to_focus = matching_windows[index]
    assert window_to_focus != current_window
    focus_window_function(window_to_focus)


def matches(window, window_spec):
    """Return True if the given window matches the given window spec.

    False otherwise.

    A window spec is a dict containing items that will be matched against
    the window object's attributes, for example:

        {'window_id': '0x02a00001',
         'desktop': '0',
         'pid': '4346',
         'wm_class': '.Firefox',
         'machine': 'mistakenot',
         'title': 'The Mock Class - Mock 1.0.1 documentation - Firefox'}

    A window object matches a spec if it has an attribute matching each of
    the items in the spec.

    A spec doesn't have to contain all of the attributes. For example
    {'wm_class': '.Firefox'} will match all windows with a wm_class
    attribute matching ".Firefox".

    Attribute matching is done by looking for substrings. For example a
    wm_class of ".Firefox" will match a window with a wm_class of
    "Navigator.Firefox".

    Window specs can also contain a "command" key (the command to be run to
    launch the app if it doesn't have any open windows) - this key will be
    ignored and the window will match the spec as long as all the other keys
    match.

    """
    for key in window_spec.keys():
        if key == 'command':
            continue
        if window_spec[key].lower() not in getattr(window, key, '').lower():
            return False
    return True


def runraisenext(window_spec, run_function, open_windows, focused_window,
                 focus_window_function, loop_function):
    """Either run the app, raise the app, or go to the app's next window.

    Depending on whether the app has any windows open and whether the app is
    currently focused.

    :param window_spec: the window spec to match against open windows
    :type window_spec: dict

    :param run_function: the function to use to run window spec commands
    :type run_function: callable taking one argument: the window spec

    :param open_windows: the list of open windows
    :type open_windows: list of Window objects

    :param focused_window: the currently focused window, should be one of the
        Window objects from open_windows
    :type focused_window: Window

    :param focus_window_function: the function to call to focus a window
    :type focus_window_function: callable taking one argument: a Window object
        representing the window to be focused

    :param loop_function: the function to call to loop (focus the next matching
        window)
    :type loop_function: callable

    """
    # If no window spec options were given, just run the command
    # (if there is one).
    if ('id' not in window_spec and
            'desktop' not in window_spec and
            'pid' not in window_spec and
            'wm_class' not in window_spec and
            'machine' not in window_spec and
            'title' not in window_spec):
        run_window_spec_command(window_spec, run_function)
        return

    # If there are no open windows, just run the command (if there is one).
    if not open_windows:
        run_window_spec_command(window_spec, run_function)
        return

    matching_windows = [window for window in open_windows
                        if matches(window, window_spec)]

    if not matching_windows:
        # The requested app is not open, launch it.
        run_window_spec_command(window_spec, run_function)
        return

    if focused_window not in matching_windows:
        # The app is open but is not focused, focus it.
        focus_window_function(matching_windows[0])
    elif len(matching_windows) == 1:
        # The app has one window open and it's already focused, do nothing.
        pass
    else:
        # The app has multiple windows open, and one of them is already
        # focused, focus the next matching window.
        loop_function(matching_windows, focused_window, focus_window_function)


class ConfigFileError(Exception):
    pass


def choose_config_file(config_file_arg):
    """Return the config file to use based on the command-line argument.

    Returns the absolute path to the file, expanding ~ and relative paths.

    If no config file is specified on the command-line, falls back on
    ~/.runraisenext.json. If that doesn't exist, falls back on the
    runraisenext.json file that ships with the package.

    :param config_file_arg: the config file that the user gave as a command
        line argument, or None
    :type config_file_arg: unicode or None

    :raises ConfigFileError: if the chosen config file doesn't exist or isn't
        a file

    """
    if config_file_arg is None:
        path = os.path.abspath(os.path.expanduser("~/.runraisenext.json"))
        if os.path.isfile(path):
            return path
        else:
            config_file = os.path.abspath("runraisenext.json")
    else:
        config_file = os.path.abspath(os.path.expanduser(config_file_arg))

    if not os.path.isfile(config_file):
        raise ConfigFileError(
            "Config file {c} doesn't exist or isn't a file".format(
                c=config_file))

    return config_file


def parse_command_line_arguments(args):
    """Parse the command-line arguments and return the requested window spec."""

    parser = argparse.ArgumentParser(
        description="a script for launching apps and switching windows",
        add_help=True)

    window_spec_args = parser.add_argument_group("window spec")
    window_spec_args.add_argument(
        '-i', '--id', dest="window_id",
        help="the window ID to look for, e.g. 0x0180000b")
    window_spec_args.add_argument(
        '-d', '--desktop', help="the desktop to look for windows on, e.g. 1")
    window_spec_args.add_argument(
        '-p', '--pid', help="the pid to look for, e.g. 3384")
    window_spec_args.add_argument(
        '-w', '--wm_class',
        help="the WM_CLASS to look for, e.g. Navigator.Firefox")
    window_spec_args.add_argument(
        '-m', '--machine', help="the client machine name to look for")
    window_spec_args.add_argument(
        '-t', '--title',
        help='the window title to look for, e.g. "wmctrl - A command line '
        'tool to interact with an EWMH/NetWM compatible X Window Manager. - '
        'Mozilla Firefox"')

    parser.add_argument(
        '-c', '--command',
        help="the command to run to launch the app, if no matching windows "
        "are found, e.g. firefox")

    parser.add_argument(
        'alias', nargs='?',
        help="the alias of a window spec from the config file to use for "
        "matching windows")

    parser.add_argument(
        "-f", "--file", help="Use a custom config file path", default=None,
        dest="config_file")

    args = parser.parse_args(args)

    try:
        config_file = choose_config_file(args.config_file)
    except ConfigFileError as err:
        parser.exit(status=1, message=err.message)

    if args.window_id is not None:
        if (args.desktop or args.pid or args.wm_class or args.machine
                or args.title):
            parser.exit(status=1,
                        message="A window ID uniquely identifies a window, "
                        "it doesn't make sense to give the -i, --id argument "
                        "at the same time as any other window spec arguments")

    # Form the window spec dict.
    if args.alias:
        window_spec = get_window_spec_from_file(args.alias, config_file)
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

    return window_spec


def main(args):
    window_spec = parse_command_line_arguments(args)
    return runraisenext(window_spec, run, wmctrl.windows(),
                        wmctrl.focused_window(), focus_window, loop)


if __name__ == "__main__":
    main(sys.argv[1:])
