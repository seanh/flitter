"""Tests for runraisenext.py."""

import mock

import runraisenext


@mock.patch('runraisenext.run_command')
@mock.patch('runraisenext.get_open_windows_from_wmctrl')
def test_launching_apps(get_open_windows_function, run_command_function):
    """runraisenext <app> should launch the app if it isn't running.

    If there are no windows that match the given window spec, it should run
    the window spec's command.

    """
    def get_open_windows():
        """Mock _get_open_windows_from_wmctrl() function.

        Returns mock wmctrl -lxp output.

        """
        return (
            '0x03e0000c  0 4464   gnome-terminal.Gnome-terminal  mistakenot '
            'tmux  /home/vagrant\n'
            '0x042000b3  0 4904   Mail.Thunderbird      mistakenot Inbox - '
            'Unified Folders - Mozilla Thunderbird\n')
    get_open_windows_function.side_effect = get_open_windows

    # Test it with a few different apps from the config file, for good measure.
    apps = [
        {'name': 'firefox', 'command': 'firefox'},
        {'name': 'skype', 'command': 'skype'},
        {'name': 'gvim', 'command': 'gvim'},
    ]
    for app in apps:
        runraisenext.main([app['name'], '-f', 'runraisenext.json'])
        run_command_function.assert_called_once_with(app['command'])
        run_command_function.reset_mock()


@mock.patch('runraisenext.focus_window_with_wmctrl')
@mock.patch('runraisenext.get_open_windows_from_wmctrl')
@mock.patch('runraisenext.get_current_window_from_wmctrl')
def test_focusing_apps(get_current_window_function, get_open_windows_function,
                       focus_window_function):
    """runraisenext <app> should focus the app if it's running but not focused.

    If there is one window that matches the given window spec and that window
    is not focused, it should focus that window.

    """
    def get_open_windows():
        """Mock _get_open_windows_from_wmctrl() function.

        Returns mock wmctrl -lxp output.

        """
        # FIXME: This isn't perfect: non-ASCII characters have been removed
        # from the mock output.
        return (
            '0x02c000b3  0 4346   Navigator.Firefox     mistakenot The Mock '
            'Class - Mock 1.0.1 documentation - Vimperator\n'
            '0x03e0000c  0 4464   gnome-terminal.Gnome-terminal  mistakenot '
            'tmux  /home/vagrant\n'
            '0x05600003  0 12022  gvim.Gvim             mistakenot '
            'test_runraisenext.py (~/Projects/runraisenext) - GVIM1\n'
            '0x0580002b  0 15150  skype.Skype           mistakenot foobar - '
            'Skype\n')
    get_open_windows_function.side_effect = get_open_windows

    def _get_current_window():
        """Mock _get_current_window_from_wmctrl() function.

        Returns mock wmctrl -a :ACTIVE: -v output.

        """
        # Returns the window ID for firefox from the mock open windows above.
        return ('envir_utf8: 1\n'
                'Using window: 0x02c000b3\n')
    get_current_window_function.side_effect = _get_current_window

    # Since Firefox is the open window, runraisenext skype or gvim should
    # raise Skype or gVim.
    runraisenext.main(['skype', '-f', 'runraisenext.json'])
    focus_window_function.assert_called_once_with('0x0580002b')
    focus_window_function.reset_mock()

    runraisenext.main(['gvim', '-f', 'runraisenext.json'])
    focus_window_function.assert_called_once_with('0x05600003')
    focus_window_function.reset_mock()


@mock.patch('runraisenext.run_command')
@mock.patch('runraisenext.focus_window_with_wmctrl')
@mock.patch('runraisenext.get_open_windows_from_wmctrl')
@mock.patch('runraisenext.get_current_window_from_wmctrl')
def test_app_focused(get_current_window_function, get_open_windows_function,
                     focus_window_function, run_command_function):
    """It should do nothing if the app's only window is already focused.

    If there is one window that matches the given window spec and that window
    is already focused, it should do nothing.

    """
    def get_open_windows():
        """Mock _get_open_windows_from_wmctrl() function.

        Returns mock wmctrl -lxp output.

        """
        # FIXME: This isn't perfect: non-ASCII characters have been removed
        # from the mock output.
        return (
            '0x02c000b3  0 4346   Navigator.Firefox     mistakenot The Mock '
            'Class - Mock 1.0.1 documentation - Vimperator\n'
            '0x03e0000c  0 4464   gnome-terminal.Gnome-terminal  mistakenot '
            'tmux  /home/vagrant\n'
            '0x05600003  0 12022  gvim.Gvim             mistakenot '
            'test_runraisenext.py (~/Projects/runraisenext) - GVIM1\n'
            '0x0580002b  0 15150  skype.Skype           mistakenot foobar - '
            'Skype\n')
    get_open_windows_function.side_effect = get_open_windows

    def _get_current_window():
        """Mock _get_current_window_from_wmctrl() function.

        Returns mock wmctrl -a :ACTIVE: -v output.

        """
        # Returns the window ID for firefox from the mock open windows above.
        return ('envir_utf8: 1\n'
                'Using window: 0x02c000b3\n')
    get_current_window_function.side_effect = _get_current_window

    # Since Firefox is the open window, runraisenext sfirefox should do
    # nothing.
    runraisenext.main(['firefox', '-f', 'runraisenext.json'])
    focus_window_function.assert_not_called()
    run_command_function.assert_not_called()


@mock.patch('runraisenext.run_command')
@mock.patch('runraisenext.focus_window_with_wmctrl')
@mock.patch('runraisenext.get_open_windows_from_wmctrl')
@mock.patch('runraisenext.get_current_window_from_wmctrl')
def test_looping(get_current_window_function, get_open_windows_function,
                 focus_window_function, run_command_function):
    """runraisenext <app> should loop through all of the app's windows.

    If there is more than one window that matches the given window spec,
    and one of the matching windows is the currently focused window,
    then it should loop through each of the matching windows.

    """
    def get_open_windows():
        """Mock _get_open_windows_from_wmctrl() function.

        Returns mock wmctrl -lxp output.

        """
        # FIXME: This isn't perfect: non-ASCII characters have been removed
        # from the mock output.
        # This returns three Gnome Terminal windows, and some other windows.
        return (
            '0x02c000b3  0 4346   Navigator.Firefox     mistakenot The Mock '
            'Class - Mock 1.0.1 documentation - Vimperator\n'
            '0x03e0000c  0 4464   gnome-terminal.Gnome-terminal  mistakenot '
            'tmux  /home/vagrant\n'
            '0x042000b3  0 4904   Mail.Thunderbird      mistakenot Inbox - '
            'Unified Folders - Mozilla Thunderbird\n'
            '0x03e005d4  0 4464   gnome-terminal.Gnome-terminal  mistakenot '
            'fish  /home/seanh/Projects/runraisenext\n'
            '0x03e03281  0 4464   gnome-terminal.Gnome-terminal  mistakenot '
            'wmctrl  /home/seanh/Vagrant/ckan\n')
    get_open_windows_function.side_effect = get_open_windows

    # Make the first Gnome Terminal window the currently focused one.
    get_current_window_function.return_value = ('envir_utf8: 1\n'
                                                'Using window: 0x03e0000c\n')

    # Since there are 3 Gnome Terminal windows, and the first Gnome Terminal
    # window is the currently focused window, runraisenext terminal should
    # focus the second Gnome Terminal window.
    runraisenext.main(['terminal', '-f', 'runraisenext.json'])
    focus_window_function.assert_called_once_with('0x03e005d4')
    focus_window_function.reset_mock()
    run_command_function.assert_not_called()

    # Make the second Gnome Terminal window the currently focused one.
    get_current_window_function.return_value = ('envir_utf8: 1\n'
                                                'Using window: 0x03e005d4\n')

    # Now runraisenext terminal should focus the third Gnome Terminal window.
    runraisenext.main(['terminal', '-f', 'runraisenext.json'])
    focus_window_function.assert_called_once_with('0x03e03281')
    focus_window_function.reset_mock()
    run_command_function.assert_not_called()

    # Make the third Gnome Terminal window the currently focused one.
    get_current_window_function.return_value = ('envir_utf8: 1\n'
                                                'Using window: 0x03e03281\n')

    # Now runraisenext terminal should focus the first Gnome Terminal window.
    runraisenext.main(['terminal', '-f', 'runraisenext.json'])
    focus_window_function.assert_called_once_with('0x03e0000c')
    run_command_function.assert_not_called()


def test_get_open_windows():
    """Test the parsing of wmctrl -lxp's window list.

    Test for correct parsing of a real window list from wmctrl -lxp, including
    junk windows from Unity, the Nautilus desktop window, Conky,
    non-ASCII characters in window titles, and WM_CLASS's with spaces in them.

    """
    window_list = open('example_wmctrl_window_list.txt', 'r').read()
    windows = runraisenext.get_open_windows(window_list)
    assert len(windows) == 17
