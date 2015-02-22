"""Tests for runraisenext.py."""

import mock

import flitter.runraisenext as runraisenext
import flitter.wmctrl as wmctrl


class TestRunRaiseNext(object):

    """Tests for the runraisenext() function."""

    def setUp(self):
        """Patch the _dump() and _load() functions.

        runraisenext() dumps a list of open windows in most-recently-used order
        to ~/.flitter.pickle, and loads it again each time.

        We patch the _dump() and _load() functions to mock out this filesystem
        access in the tests, replacing them with functions that just save
        the dumped/loaded object in a self.dumped_object attribute of the test
        class.

        This lets use reset self.dumped_object after each test method,
        avoiding any inter-dependence between test methods.

        """
        self.dumped_object = None

        self.dump_patcher = mock.patch('flitter.runraisenext._dump')
        mock_dump_function = self.dump_patcher.start()

        def dump_(obj, path):
            self.dumped_object = obj

        mock_dump_function.side_effect = dump_

        self.load_patcher = mock.patch('flitter.runraisenext._load')
        mock_load_function = self.load_patcher.start()

        def load_(path):
            if self.dumped_object is None:
                # We're assuming that runraisenext() never actually tries to
                # dump the value None, and simulating what happens when the
                # ~/.flitter.pickle file doesn't exist.
                raise IOError
            else:
                return self.dumped_object

        mock_load_function.side_effect = load_

    def tearDown(self):
        self.dump_patcher.stop()
        self.load_patcher.stop()
        self.dumped_object = None

    def test_window_matches_when_matching(self):
        """matches() should return True when given a matching window spec."""
        specs = [
            dict(window_id="window_id"),
            dict(desktop="desktop"),
            dict(pid="pid"),
            dict(wm_class="Firefox"),
            dict(wm_class=".Firefox"),
            dict(wm_class="Navigator"),
            dict(wm_class="Navigator.Firefox"),
            dict(machine="machine"),
            dict(title="title"),
            dict(window_id='window_id', desktop='desktop', pid='pid',
                 wm_class='.Firefox', machine='machine', title='title'),
            ]
        window = wmctrl.Window('window_id', 'desktop', 'pid',
                               'Navigator.Firefox', 'machine', 'title')

        for spec in specs:
            assert runraisenext.matches(window, spec)

    def test_window_matches_when_not_matching(self):
        """matches() should return False when given a non-matching spec."""
        specs = [
            dict(window_id="different_window_id"),
            dict(desktop="different_desktop"),
            dict(pid="different_pid"),
            dict(wm_class="Chrome"),
            dict(wm_class=".Chrome"),
            dict(machine="different_machine"),
            dict(title="different_title"),
            dict(window_id='different_window_id', desktop='different_desktop',
                 pid='different_pid', wm_class='.Chrome',
                 machine='different_machine', title='different_title'),
            dict(window_id='window_id', desktop='desktop', pid='pid',
                 wm_class='.Chrome', machine='machine', title='title'),
            dict(window_id='different_window_id', desktop='desktop', pid='pid',
                 wm_class='.Firefox', machine='machine', title='title'),
            ]
        window = wmctrl.Window('window_id', 'desktop', 'pid',
                               'Navigator.Firefox', 'machine', 'title')

        for spec in specs:
            assert not runraisenext.matches(window, spec)

    def test_window_matches_with_command(self):
        """matches() should ignore "command" keys in window spec dicts.

        Window objects don't have a .command attribute, but a window spec dict
        with a "command" key should still match as long as its other keys
        match.

        """
        spec = dict(window_id='window_id', desktop='desktop', pid='pid',
                    wm_class='.Firefox', machine='machine', title='title',
                    command='firefox')
        window = wmctrl.Window('window_id', 'desktop', 'pid',
                               'Navigator.Firefox', 'machine', 'title')
        assert runraisenext.matches(window, spec)

    def test_window_matches_is_case_insensitive(self):
        """matches() should be case-insensitive."""
        spec = dict(window_id='WINDOW_ID', desktop='DESKTOP', pid='PID',
                    wm_class='.FIREFOX', machine='MACHINE', title='TITLE',
                    command='firefox')
        window = wmctrl.Window('window_id', 'desktop', 'pid',
                               'Navigator.Firefox', 'machine', 'title')
        assert runraisenext.matches(window, spec)

    def test_with_command_only(self):
        """`flitter -c firefox` should run the `firefox` command.

        If just a command is given and no window spec or alias, it should just
        run that command.

        """
        run_function = mock.MagicMock()
        focused_window = wmctrl.Window('2', '0', 'pid',
                                       'Navigator.Thunderbird', 'mistakenot',
                                       'My Thunderbird Window')
        windows = [
            wmctrl.Window('1', '0', 'pid', 'Navigator.Firefox', 'mistakenot',
                          'My Firefox Window'),
            focused_window,
            wmctrl.Window('2', '0', 'pid', 'Terminal.Terminal', 'mistakenot',
                          'My Terminal Window'),
        ]
        focus_window_function = mock.MagicMock()

        runraisenext.runraisenext({'command': 'firefox'}, run_function,
                                  windows, focused_window,
                                  focus_window_function)

        run_function.assert_called_once_with('firefox')
        assert not focus_window_function.called

    def test_with_no_open_windows(self):
        """`flitter firefox` should run `firefox` if no open windows.

        If there are no open windows it should just run the command associated
        with the given window spec.

        """
        run_function = mock.MagicMock()
        focus_window_function = mock.MagicMock()

        runraisenext.runraisenext({'command': 'firefox'}, run_function, [],
                                  None, focus_window_function)

        run_function.assert_called_once_with('firefox')
        assert not focus_window_function.called

    def test_with_no_matching_windows(self):
        """`flitter firefox` should run `firefox` if no firefox windows.

        If there are no open windows that match the given window spec, it
        should run the window spec's command.

        """
        window_spec = {"command": "firefox", "wm_class": ".Firefox"}
        run_function = mock.MagicMock()
        focused_window = wmctrl.Window('2', '0', 'pid',
                                       'Navigator.Thunderbird', 'mistakenot',
                                       'My Thunderbird Window')
        windows = [
            wmctrl.Window('1', '0', 'pid', 'Navigator.Gvim', 'mistakenot',
                          'My GVim Window'),
            focused_window,
            wmctrl.Window('2', '0', 'pid', 'Terminal.Terminal', 'mistakenot',
                          'My Terminal Window'),
        ]
        focus_window_function = mock.MagicMock()

        runraisenext.runraisenext(window_spec, run_function, windows,
                                  focused_window, focus_window_function)

        run_function.assert_called_once_with('firefox')
        assert not focus_window_function.called

    def test_raise(self):
        """If there's a Firefox window open but it's not focused,
        `flitter firefox` should focus the Firefox window.

        """
        window_spec = {"command": "firefox", "wm_class": ".Firefox"}
        run_function = mock.MagicMock()
        focused_window = wmctrl.Window('1', '0', 'pid',
                                       'Navigator.Thunderbird', 'mistakenot',
                                       'My Thunderbird Window')
        firefox_window = wmctrl.Window('2', '0', 'pid', 'Navigator.Firefox',
                                       'mistakenot', 'My Firefox Window')
        windows = [
            firefox_window,
            focused_window,
            wmctrl.Window('1', '0', 'pid', 'Terminal.Terminal', 'mistakenot',
                          'My Terminal Window'),
        ]
        focus_window_function = mock.MagicMock()

        runraisenext.runraisenext(window_spec, run_function, windows,
                                  focused_window, focus_window_function)

        assert not run_function.called
        focus_window_function.assert_called_once_with(firefox_window)

    def test_already_raised(self):
        """If there's one Firefox window open and it's already focused,
        `flitter firefox` should do nothing.

        """
        window_spec = {"command": "firefox", "wm_class": ".Firefox"}
        run_function = mock.MagicMock()
        firefox_window = wmctrl.Window('2', '0', 'pid', 'Navigator.Firefox',
                                       'mistakenot', 'My Firefox Window')
        windows = [
            firefox_window,
            wmctrl.Window('2', '0', 'pid', 'Navigator.Thunderbird',
                          'mistakenot', 'My Thunderbird Window'),
            wmctrl.Window('1', '0', 'pid', 'Terminal.Terminal', 'mistakenot',
                          'My Terminal Window'),
        ]
        focus_window_function = mock.MagicMock()

        runraisenext.runraisenext(window_spec, run_function, windows,
                                  firefox_window, focus_window_function)

        assert not run_function.called
        assert not focus_window_function.called

    def test_looping(self):
        """If there are multiple Firefox windows open and one of them is
        focused, `flitter firefox` should focus the next Firefox windows.

        Repeated calls should loop through all the Firefox windows, going back
        to the first one after the last one.

        """
        window_spec = {"command": "firefox", "wm_class": ".Firefox"}
        run_function = mock.MagicMock()
        firefox_window_1 = wmctrl.Window('2', '0', 'pid', 'Navigator.Firefox',
                                         'mistakenot', 'My Firefox Window')
        firefox_window_2 = wmctrl.Window('3', '0', 'pid', 'Navigator.Firefox',
                                         'mistakenot',
                                         'My Other Firefox Window')
        windows = [
            firefox_window_1,
            firefox_window_2,
            wmctrl.Window('4', '0', 'pid', 'Navigator.Thunderbird',
                          'mistakenot', 'My Thunderbird Window'),
            wmctrl.Window('5', '0', 'pid', 'Terminal.Terminal', 'mistakenot',
                          'My Terminal Window'),
        ]
        focus_window_function = mock.MagicMock()

        runraisenext.runraisenext(window_spec, run_function, windows,
                                  firefox_window_1, focus_window_function)

        assert not run_function.called
        focus_window_function.assert_called_once_with(firefox_window_2)

    def test_most_recently_raised_first(self):
        """Test looping through windows of apps in most-recently-used order."""
        # We'll have two Thunderbird, 1 Firefox and 3 Terminal windows.
        thunderbird_1 = wmctrl.Window(
            "1", "0", "pid", "Navigator.Thunderbird", "mistakenot",
            "Thunderbird Window 1")
        thunderbird_2 = wmctrl.Window(
            "2", "0", "pid", "Navigator.Thunderbird", "mistakenot",
            "Thunderbird Window 2")
        firefox = wmctrl.Window(
            "3", "0", "pid", "Navigator.Firefox", "mistakenot",
            "Firefox Window")
        terminal_1 = wmctrl.Window(
            "4", "0", "pid", "Terminal.Terminal", "mistakenot",
            "Terminal Window 1")
        terminal_2 = wmctrl.Window(
            "5", "0", "pid", "Terminal.Terminal", "mistakenot",
            "Terminal Window 2")
        terminal_3 = wmctrl.Window(
            "6", "0", "pid", "Terminal.Terminal", "mistakenot",
            "Terminal Window 3")
        windows = [thunderbird_1, thunderbird_2, firefox, terminal_1,
                   terminal_2, terminal_3]

        def request_window(wm_class, focused_window, expected_window):
            run_function = mock.MagicMock()
            focus_window_function = mock.MagicMock()
            runraisenext.runraisenext(
                window_spec={"wm_class": wm_class},
                run_function=run_function, open_windows=windows,
                focused_window=focused_window,
                focus_window_function=focus_window_function)
            assert not run_function.called
            focus_window_function.assert_called_once_with(expected_window)
            return expected_window

        focused_window = firefox
        focused_window = request_window(".Terminal", focused_window,
                                        terminal_1)
        focused_window = request_window(".Terminal", focused_window,
                                        terminal_2)
        focused_window = request_window(".Terminal", focused_window,
                                        terminal_3)
        focused_window = request_window(".Thunderbird", focused_window,
                                        thunderbird_1)
        focused_window = request_window(".Thunderbird", focused_window,
                                        thunderbird_2)
        focused_window = request_window(".Terminal", focused_window,
                                        terminal_3)
        focused_window = request_window(".Terminal", focused_window,
                                        terminal_2)
        focused_window = request_window(".Terminal", focused_window,
                                        terminal_1)
        focused_window = request_window(".Terminal", focused_window,
                                        terminal_3)
        focused_window = request_window(".Terminal", focused_window,
                                        terminal_2)
        focused_window = request_window(".Thunderbird", focused_window,
                                        thunderbird_2)
        focused_window = request_window(".Thunderbird", focused_window,
                                        thunderbird_1)

    def test_go_to_other_window(self):
        """Test moving from a known to an "other" window with --others."""
        known_window_1 = wmctrl.Window(
            "1", "0", "pid", "Navigator.Thunderbird", "mistakenot",
            "Thunderbird")
        known_window_2 = wmctrl.Window(
            "2", "0", "pid", "Navigator.Firefox", "mistakenot", "Firefox")
        other_window = wmctrl.Window(
            "3", "0", "pid",
            "org.gnome.Weather.Application.Org.gnome.Weather.Application",
            "mistakenot", "Weather")
        known_window_3 = wmctrl.Window(
            "4", "0", "pid", "Terminal.Terminal", "mistakenot", "Terminal")

        window_specs = [
            dict(wm_class=".Thunderbird"),
            dict(wm_class=".Firefox"),
            dict(wm_class=".Terminal"),
        ]

        run_function = mock.MagicMock()
        focus_window_function = mock.MagicMock()

        runraisenext.runraisenext(
            window_spec={},
            run_function=run_function,
            open_windows=[known_window_1, known_window_2, other_window,
                          known_window_3],
            focused_window=known_window_1,
            focus_window_function=focus_window_function,
            others=True,
            window_specs=window_specs)

        assert not run_function.called
        focus_window_function.assert_called_once_with(other_window)

    def test_loop_through_other_windows(self):
        """Test looping through "other" windows by calling --others repeatedly.

        """
        known_window_1 = wmctrl.Window(
            "1", "0", "pid", "Navigator.Thunderbird", "mistakenot",
            "Thunderbird")
        known_window_2 = wmctrl.Window(
            "2", "0", "pid", "Navigator.Firefox", "mistakenot", "Firefox")
        other_window_1 = wmctrl.Window(
            "3", "0", "pid",
            "org.gnome.Weather.Application.Org.gnome.Weather.Application",
            "mistakenot", "Weather")
        known_window_3 = wmctrl.Window(
            "4", "0", "pid", "Terminal.Terminal", "mistakenot", "Terminal")
        other_window_2 = wmctrl.Window(
            "5", "0", "pid", "baobab.Baobab", "mistakenot",
            "Disk Usage Analyzer")
        other_window_3 = wmctrl.Window(
            "6", "0", "pid", "gnome-clocks.Gnome-clocks", "mistakenot",
            "Clocks")
        windows = [known_window_1, known_window_2, other_window_1,
                   known_window_3, other_window_2, other_window_3]

        window_specs = [
            dict(wm_class=".Thunderbird"),
            dict(wm_class=".Firefox"),
            dict(wm_class=".Terminal"),
        ]

        run_function = mock.MagicMock()

        def request_other(focused_window, expected_window):
            """Do `flitter --others`.

            And assert that the expected_window was raised.

            """
            focus_window_function = mock.MagicMock()
            runraisenext.runraisenext(
                window_spec={},
                run_function=run_function,
                open_windows=windows,
                focused_window=focused_window,
                focus_window_function=focus_window_function,
                others=True,
                window_specs=window_specs)
            assert not run_function.called
            focus_window_function.assert_called_once_with(expected_window)
            return expected_window

        # First move from a known window to the first other window.
        focused_window = request_other(known_window_1, other_window_1)
        # Now loop through the other windows.
        focused_window = request_other(focused_window, other_window_2)
        focused_window = request_other(focused_window, other_window_3)
        focused_window = request_other(focused_window, other_window_1)

    def test_ignore_windows(self):
        """flitter -o should skip ignored windows."""
        ignored_window_1 = wmctrl.Window(
            "1", "0", "pid", "desktop_window.Nautilus", "mistakenot",
            "Desktop")
        ignored_window_2 = wmctrl.Window(
            "2", "0", "pid", "Conky.Conky", "mistakenot",
            "Conky (mistakenot)")
        known_window = wmctrl.Window(
            "3", "0", "pid", "Navigator.Thunderbird", "mistakenot",
            "Thunderbird")
        other_window_1 = wmctrl.Window(
            "4", "0", "pid",
            "org.gnome.Weather.Application.Org.gnome.Weather.Application",
            "mistakenot", "Weather")
        other_window_2 = wmctrl.Window(
            "5", "0", "pid", "baobab.Baobab", "mistakenot",
            "Disk Usage Analyzer")
        other_window_3 = wmctrl.Window(
            "6", "0", "pid", "gnome-clocks.Gnome-clocks", "mistakenot",
            "Clocks")
        windows = [ignored_window_1, ignored_window_2, known_window,
                   other_window_1, other_window_2, other_window_3]
        window_specs = [dict(wm_class=".Thunderbird")]
        ignore = [
            dict(wm_class="desktop_window.Nautilus"),
            dict(wm_class="Conky.Conky")
        ]
        run_function = mock.MagicMock()

        def request_other(focused_window, expected_window):
            """Do `flitter --others`.

            And assert that the expected_window was raised.

            """
            focus_window_function = mock.MagicMock()
            runraisenext.runraisenext(
                window_spec={},
                run_function=run_function,
                open_windows=windows,
                focused_window=focused_window,
                focus_window_function=focus_window_function,
                others=True, ignore=ignore,
                window_specs=window_specs)
            assert not run_function.called
            focus_window_function.assert_called_once_with(expected_window)
            return expected_window

        # First move from a known window to the first other window.
        focused_window = request_other(known_window, other_window_1)
        # Now loop through the other windows.
        focused_window = request_other(focused_window, other_window_2)
        focused_window = request_other(focused_window, other_window_3)
        focused_window = request_other(focused_window, other_window_1)

    # TODO: Tests for all the command-line options.
