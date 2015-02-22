#!/usr/bin/env python2.7
"""A script for launching apps and switching windows."""
import sys
import argparse
import subprocess
import json
import os
import pickle

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


def get_all_window_specs_from_file(file_):
    """Return a list of all the window specs from the given config file."""
    specs = json.loads(
        open(os.path.abspath(os.path.expanduser(file_)), 'r').read())["specs"]
    lowercased_specs = {}
    for key in specs:
        assert key.lower() not in lowercased_specs
        lowercased_specs[key.lower()] = specs[key]
    return lowercased_specs


def get_window_spec_from_file(alias, file_):
    """Get the requested window spec from the config file.

    :rtype: dictionary

    """
    specs = get_all_window_specs_from_file(file_)
    spec = specs[alias.lower()]
    return spec


def get_ignore_from_file(file_):
    """Return the list of window specs to ignore from the given config file."""
    return json.loads(
        open(os.path.abspath(os.path.expanduser(file_)), 'r').read())[
            "ignore"]


def _load(path):
    """Helper function to load an object from persistent storage.

    This is a wrapper for pickle.load(), we wrap it to make it easy for tests
    to patch it and mock out the filesystem.

    """
    with open(path, "r") as file_:
        return pickle.load(file_)


def _dump(obj, path):
    """Helper function to persist an object.

    This is a wrapper for pickle.dump(), we wrap it to make it easy for tests
    to patch it and mock out the filesystem.

    """
    with open(path, "w") as file_:
        pickle.dump(obj, file_)


def pickle_path():
    """Return the path to the file we use to track windows in mru order."""
    return os.path.abspath(os.path.expanduser("~/.flitter.pickle"))


def sorted_most_recently_used(current_window_list):
    """Return the given list of open windows in most-recently-used order.

    :param current_window_list: the list of currently open windows,
        in any order
    :type current_window_list: list of Window objects

    :returns: the given list of currently opened windows, sorted into
        most-recently-used-first order
    :rtype: list of Window objects

    """
    try:
        pickled_window_list = _load(pickle_path())
    except (IOError, EOFError):
        pickled_window_list = []

    # Remove windows that have been closed since the last time we ran.
    pickled_window_list = [
        w for w in pickled_window_list if w in current_window_list]

    # Add windows that have been opened since the last time we ran to the front
    # of the list.
    new_windows = []
    for window in current_window_list:
        if window not in pickled_window_list:
            new_windows.append(window)
    pickled_window_list = new_windows + pickled_window_list

    return pickled_window_list


def update_pickled_window_list(open_windows, newly_focused_window):
    """Move the newly focused window to the top of the cached list of windows.

    We keep a cached list of windows in most-recently-used order so that
    when switching to a new app we can switch to the app's most recently used
    windows first.

    Each time after focusing a window we call this function to update the
    cached list on disk for the next time we run.

    """
    assert newly_focused_window in open_windows
    open_windows.remove(newly_focused_window)
    assert newly_focused_window not in open_windows, (
        "There shouldn't be more than one instance of the same window in "
        "the list of open windows")
    open_windows.insert(0, newly_focused_window)
    _dump(open_windows, pickle_path())


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


def matches_any(window, specs):
    """Return True if the given window matches any of the given specs."""
    for spec in specs:
        if matches(window, spec):
            return True
    return False


def _unvisited_windows(matching_windows, open_windows):
    """Return the list of matching windows that we haven't looped through yet.

    When we're looping through the windows of an app there's a continuous
    sequence of the app's windows at the top of the list of all open windows
    (which is sorted in most-recently-focused order). These are the windows
    from the app that we've already looped through.

    This function returns the app's windows that aren't part of this list:
    the ones we haven't looped through yet.

    May return an empty list.

    """
    visited_windows = []
    for window in open_windows:
        if window in matching_windows:
            visited_windows.append(window)
        else:
            break
    return [w for w in matching_windows if w not in visited_windows]


def _get_other_windows(windows, specs):
    """Return the windows that don't match any of the specs.

    Return the list of Window objects from windows that don't match any of the
    window spec dicts in specs. These are called the "other" windows.

    """
    return [w for w in windows if not matches_any(w, specs)]


def runraisenext(window_spec, run_function, open_windows, focused_window,
                 focus_window_function, others=False, window_specs=None,
                 ignore=None):
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

    :param others: If ``True`` go to the next "other" window ("other" windows
        are windows that don't match any of the given window specs) instead of
        looking for the next window that matches a particular window spec.
        The ``window_spec`` and ``run_function`` arguments aren't used if
        ``others`` is ``True``.

    :param window_specs: A list of all the window specs from the user's config
        file. This is only needed if ``others=True`` is given.
    :type window_specs: list of dicts

    :param ignore: A list of window specs matching windows that should be
        ignored and never focused. This is used to skip things like desktop
        windows, taskbars, etc.
    :type ignore: list of dicts

    """
    def _focus_window(window):
        """Call focus_window_function() on the given window.

        Also moves the newly-focused window to the top of the
        most-recently-used-windows list, which we want to do whenever we
        focus a window.

        """
        focus_window_function(window)
        update_pickled_window_list(open_windows, window)

    if not ignore:
        ignore = []

    open_windows = sorted_most_recently_used(open_windows)

    # If no window spec options were given, just run the command
    # (if there is one).
    if (not others and
            'id' not in window_spec and
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

    if others:
        matching_windows = _get_other_windows(open_windows, window_specs)
    else:
        matching_windows = [window for window in open_windows
                            if matches(window, window_spec)]

    matching_windows = [w for w in matching_windows
                        if not matches_any(w, ignore)]

    if not matching_windows:
        # The requested app is not open, launch it.
        run_window_spec_command(window_spec, run_function)
    elif focused_window not in matching_windows:
        # The requested app isn't focused. Focus its most recently used window.
        _focus_window(matching_windows[0])
    elif len(matching_windows) == 1 and focused_window in matching_windows:
        # The app has one window open and it's already focused, do nothing.
        pass
    else:
        # The app has more than one window open, and one of the app's windows
        # is focused. Loop to the app's next window.
        assert focused_window in matching_windows and len(matching_windows) > 1
        unvisited = _unvisited_windows(matching_windows, open_windows)
        if unvisited:
            assert focused_window != unvisited[0], (
                "We shouldn't be trying to switch to the window that's "
                "already focused")
            _focus_window(unvisited[0])
        else:
            assert focused_window != matching_windows[-1], (
                "We shouldn't be trying to switch to the window that's "
                "already focused")
            _focus_window(matching_windows[-1])


class ConfigFileError(Exception):
    pass


def _config_file_path(args):
    """Return the absolute path to the config file to use.

    This first uses the config file given with the -f/--f command-line
    argument (which defaults to ~/.flitter.json if not given).
    If that file doesn't exist it falls back on the default flitter.json file
    that ships with Flitter in the same directory as this Python module.
    Failing that it crashes.

    """
    path = os.path.abspath(os.path.expanduser(args.file))
    if os.path.isfile(path):
        return path

    default_path = os.path.join(
        os.path.split(sys.modules[__name__].__file__)[0], "flitter.json")
    if os.path.isfile(default_path):
        return default_path

    raise ConfigFileError(
        "Couldn't find either the config file {file} or the default config "
        "file {default_file}".format(file=path, default_file=default_path))


def parse_command_line_arguments(args):
    """Parse the command-line arguments."""
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
        "-f", "--file", help="use a custom config file path",
        default="~/.flitter.json")

    parser.add_argument(
        "-o", "--others",
        help="raise \"other\" windows (windows that don't match any window "
             "spec in the config file), instead of windows matching a "
             "particular window spec",
        action="store_true")

    args = parser.parse_args(args)

    if args.window_id is not None:
        if (args.desktop or args.pid or args.wm_class or args.machine or
                args.title):
            parser.exit(status=1,
                        message="A window ID uniquely identifies a window, "
                        "it doesn't make sense to give the -i, --id argument "
                        "at the same time as any other window spec arguments")

    if args.others:
        if (args.command or args.window_id or args.desktop or args.pid or
                args.wm_class or args.machine or args.title):
            parser.exit(
                "The -o/--others argument can't be used at the same time as "
                "-c/--command, -i/--id, -d/--desktop, -p/--pid,-w/--wm_class, "
                "-m/--machine or -t/--title")

    try:
        config_file_path = _config_file_path(args)
    except ConfigFileError as err:
        parser.exit(err.message)

    # Form the window spec dict.
    if args.alias:
        window_spec = get_window_spec_from_file(args.alias, config_file_path)
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

    ignore = get_ignore_from_file(config_file_path)
    all_window_specs = get_all_window_specs_from_file(
        config_file_path).values()

    return window_spec, all_window_specs, ignore, args.others


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    window_spec, all_window_specs, ignore, others = (
        parse_command_line_arguments(args))
    return runraisenext(window_spec, run, wmctrl.windows(),
                        wmctrl.focused_window(), focus_window,
                        others=others, ignore=ignore,
                        window_specs=all_window_specs)
