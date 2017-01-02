import ewmh


EWMH = ewmh.EWMH()


class Window(object):

    def __init__(self, ewmh_window):
        try:
            self.desktop = EWMH.getWmDesktop(ewmh_window)
        except TypeError:
            # getWmDesktop() raises TypeError for some windows.
            # This appears to be a bug in the ewmh Python lib.
            self.desktop = None
        self.window_id = ewmh_window.id
        self.pid = EWMH.getWmPid(ewmh_window)
        self.wm_class = '.'.join(ewmh_window.get_wm_class())
        self.machine = ewmh_window.get_wm_client_machine()
        self.title = EWMH.getWmName(ewmh_window)

        for attr in ('wm_class', 'machine', 'title'):
            # Annoyingly getWmName() seems to alway return unicode strings
            # _unless_ the window name contains non-ASCII characters then it
            # returns a byte string (which will cause our code, which expects
            # to be working with unicode strings, to crash later on).
            value = getattr(self, attr)
            if hasattr(value, 'decode'):
                setattr(self, attr, value.decode())

    def __eq__(self, other):
        if not hasattr(other, "window_id"):
            return False
        return self.window_id == other.window_id

    def __str__(self):
        return '{window_id} {wm_class} {title}'.format(
                window_id=self.window_id, wm_class=self.wm_class,
                title=self.title)

    def focus(self):
        """Focus (activate) this window."""
        EWMH.setActiveWindow(self.ewmh_window)
        EWMH.display.flush()

    @property
    def ewmh_window(self):
        """Return the underlying ewmh.Window object for this window."""
        # Because we don't save the actual ewmh.Window object against self we
        # have to find it again here.
        for ewmh_window in EWMH.getClientList():
            if ewmh_window.id == self.window_id:
                return ewmh_window
        assert False, "Tried to focus a window that doesn't exist (anymore)"

    @property
    def minimized(self):
        return 323 in EWMH.getWmState(self.ewmh_window)

    @staticmethod
    def window(window_id):
        """Return a Window object for the open window with the given window_id.

        Returns None if there's no open window with the given window_id
        (maybe the window has been closed).

        """
        for w in Window.windows():
            if w.window_id == window_id:
                return w

    @staticmethod
    def windows():
        """Return a list of Window objects for all currently open windows."""
        windows_ = []
        for ewmh_window in EWMH.getClientList():
            windows_.append(Window(ewmh_window))
        return windows_

    @staticmethod
    def focused_window():
        """Return the currently focused window."""
        active_window = EWMH.getActiveWindow()
        if active_window is None:
            return None
        else:
            return Window(active_window)
