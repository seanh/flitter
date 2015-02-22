"""A Python wrapper library for the wmctrl program.

It only wraps the wmctrl features that Flitter needs, ignores the rest.

"""
import subprocess


def _run(command):
    """Run the given command as a subprocess.

    :param command: the command to run, for example "wmctrl -lxp"
    :type command: string

    """
    return subprocess.check_output(command.split(),
                                   stderr=subprocess.STDOUT).decode("utf-8")


def _parse_wmctrl_window_line(line):
    """Parse the given line of output from wmctrl -lxp and return its parts."""
    window_id, desktop, pid, rest = line.split(None, 3)
    wm_class, rest = rest.split('  ', 1)
    parts = rest.split(None, 1)
    assert len(parts) in (1, 2)
    machine = parts[0]
    if len(parts) == 2:
        title = parts[1]
    else:
        title = ''

    return dict(window_id=window_id, desktop=desktop, pid=pid,
                wm_class=wm_class, machine=machine, title=title)


class Window(object):

    """A window."""

    def __init__(self, window_id, desktop, pid, wm_class, machine, title=None):
        self.window_id = window_id
        self.desktop = desktop
        self.pid = pid
        self.wm_class = wm_class
        self.machine = machine
        if title is None:
            title = ''
        self.title = title

    def __repr__(self):
        return str(dict(
            window_id=self.window_id, desktop=self.desktop, pid=self.pid,
            wm_class=self.wm_class, machine=self.machine, title=self.title))

    def __eq__(self, other):
        """Return True if this window is the same as other.

        Return True if this Window object represents the same window as the
        given other Window object, False otherwise.

        """
        if not hasattr(other, "window_id"):
            return False

        return self.window_id == other.window_id

    def _focus(self, run_function):
        run_function("wmctrl -i -a " + self.window_id)

    def focus(self):
        """Focus this window."""
        self._focus(_run)


def _windows(wmctrl_output):
    windows_ = []
    for line in wmctrl_output.split("\n"):
        if not line:
            continue
        windows_.append(Window(**_parse_wmctrl_window_line(line)))

    return windows_


def windows():
    """Return a list of all the currently open windows.

    :rtype: list of Window objects

    """
    return _windows(wmctrl_output=_run("wmctrl -lxp"))


def _get_focused_window_from_wmctrl():
    """Return the currently focused window from wmctrl.

    Returns the unparsed string output of wmctrl output, which contains the ID
    of the current window as well as some other info.

    """
    # wmctrl doesn't provide a good way to get the currently focused window,
    # but this works.
    try:
        return _run("wmctrl -a :ACTIVE: -v")
    except subprocess.CalledProcessError:
        # This happens if there is no focused window (wmctrl exits with status
        # 1).
        return None


def _focused_window(output, windows_):
    if output is None:
        return None
    lines = [line for line in output.split("\n")]
    assert len(lines) == 3
    window_id = lines[1].split()[-1]
    matching_windows = [window for window in windows_
                        if window.window_id == window_id]
    assert len(matching_windows) == 1
    current_window = matching_windows[0]
    return current_window


def focused_window():
    """Return the currently focused window."""
    return _focused_window(_get_focused_window_from_wmctrl(), windows())
