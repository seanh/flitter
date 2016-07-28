import ewmh


EWMH = ewmh.EWMH()


class Window(object):

    def __init__(self, ewmh_window):
        # FIXME: We don't save ewmh_window against self because ewmh_window
        # isn't pickleable, and we do pickle these Window objects.
        # We should fix this by having a to_pickleable() and from_pickleable()
        # methods.
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

    def __eq__(self, other):
        if not hasattr(other, "window_id"):
            return False
        return self.window_id == other.window_id

    def focus(self):
        """Focus (activate) this window."""
        # FIXME: Because we don't save the actual ewmh.Window object against
        # self (see FIXME above) we have to find it again here.
        for ewmh_window in EWMH.getClientList():
            if ewmh_window.id == self.window_id:
                EWMH.setActiveWindow(ewmh_window)
                EWMH.display.flush()
                return
        assert False, "Tried to focus a window that doesn't exist (anymore)"

    @classmethod
    def windows(cls):
        """Return a list of Window objects for all currently open windows."""
        windows_ = []
        for ewmh_window in EWMH.getClientList():
            windows_.append(Window(ewmh_window))
        return windows_

    @classmethod
    def focused_window(cls):
        """Return the currently focused window."""
        return Window(EWMH.getActiveWindow())
