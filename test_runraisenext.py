"""Tests for runraisenext.py."""

import mock

import runraisenext
import wmctrl


def test_window_matches_when_matching():
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
    window = wmctrl.Window('window_id', 'desktop', 'pid', 'Navigator.Firefox',
                           'machine', 'title')

    for spec in specs:
        assert runraisenext.matches(window, spec)


def test_window_matches_when_not_matching():
    """matches() should return False when given a non-matching window spec."""

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
    window = wmctrl.Window('window_id', 'desktop', 'pid', 'Navigator.Firefox',
                           'machine', 'title')

    for spec in specs:
        assert not runraisenext.matches(window, spec)


def test_window_matches_with_command():
    """matches() should ignore "command" keys in window spec dicts.

    Window objects don't have a .command attribute, but a window spec dict with
    a "command" key should still match as long as its other keys match.

    """
    spec = dict(window_id='window_id', desktop='desktop', pid='pid',
                wm_class='.Firefox', machine='machine', title='title',
                command='firefox')
    window = wmctrl.Window('window_id', 'desktop', 'pid', 'Navigator.Firefox',
                           'machine', 'title')
    assert runraisenext.matches(window, spec)


def test_window_matches_is_case_insensitive():
    """matched() should match against window spec items case-insensitively."""
    spec = dict(window_id='WINDOW_ID', desktop='DESKTOP', pid='PID',
                wm_class='.FIREFOX', machine='MACHINE', title='TITLE',
                command='firefox')
    window = wmctrl.Window('window_id', 'desktop', 'pid', 'Navigator.Firefox',
                           'machine', 'title')
    assert runraisenext.matches(window, spec)


def test_with_command_only():
    """runraisenext -c firefox should run the firefox` command.

    If just a command is given and no window spec or alias, it should just run
    that command.

    """
    run_function = mock.MagicMock()
    focused_window = wmctrl.Window('2', '0', 'pid', 'Navigator.Thunderbird',
                                   'mistakenot', 'My Thunderbird Window')
    windows = [
        wmctrl.Window('1', '0', 'pid', 'Navigator.Firefox', 'mistakenot',
                      'My Firefox Window'),
        focused_window,
        wmctrl.Window('1', '0', 'pid', 'Terminal.Terminal', 'mistakenot',
                      'My Terminal Window'),
    ]
    focus_window_function = mock.MagicMock()

    runraisenext.runraisenext({'command': 'firefox'}, run_function, windows,
                              focused_window, focus_window_function)

    run_function.assert_called_once_with('firefox')
    assert not focus_window_function.called


def test_with_no_open_windows():
    """runraisenext firefox should run `firefox` if there are no open windows.

    If there are no open windows it should just run the command associated with
    the given window spec.

    """
    run_function = mock.MagicMock()
    focus_window_function = mock.MagicMock()

    runraisenext.runraisenext({'command': 'firefox'}, run_function, [], None,
                              focus_window_function)

    run_function.assert_called_once_with('firefox')
    assert not focus_window_function.called


def test_with_no_matching_windows():
    """runraisenext firefox should run `firefox` if there are no firefox windows
    open.

    If there are no open windows that match the given window spec, it should
    run the window spec's command.

    """
    window_spec = {"command": "firefox", "wm_class": ".Firefox"}
    run_function = mock.MagicMock()
    focused_window = wmctrl.Window('2', '0', 'pid', 'Navigator.Thunderbird',
                                   'mistakenot', 'My Thunderbird Window')
    windows = [
        wmctrl.Window('1', '0', 'pid', 'Navigator.Gvim', 'mistakenot',
                      'My GVim Window'),
        focused_window,
        wmctrl.Window('1', '0', 'pid', 'Terminal.Terminal', 'mistakenot',
                      'My Terminal Window'),
    ]
    focus_window_function = mock.MagicMock()

    runraisenext.runraisenext(window_spec, run_function, windows,
                              focused_window, focus_window_function)

    run_function.assert_called_once_with('firefox')
    assert not focus_window_function.called


def test_raise():
    """If there's a Firefox window open but it's not focused, runraisenext
    firefox should focus the Firefox window."""
    window_spec = {"command": "firefox", "wm_class": ".Firefox"}
    run_function = mock.MagicMock()
    focused_window = wmctrl.Window('2', '0', 'pid', 'Navigator.Thunderbird',
                                   'mistakenot', 'My Thunderbird Window')
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
    assert focus_window_function.called_once_with(firefox_window)


def test_already_raised():
    """If there's one Firefox window open and it's already focused,
    runraisenext firefox should do nothing."""
    window_spec = {"command": "firefox", "wm_class": ".Firefox"}
    run_function = mock.MagicMock()
    firefox_window = wmctrl.Window('2', '0', 'pid', 'Navigator.Firefox',
                                   'mistakenot', 'My Firefox Window')
    windows = [
        firefox_window,
        wmctrl.Window('2', '0', 'pid', 'Navigator.Thunderbird', 'mistakenot',
                      'My Thunderbird Window'),
        wmctrl.Window('1', '0', 'pid', 'Terminal.Terminal', 'mistakenot',
                      'My Terminal Window'),
    ]
    focus_window_function = mock.MagicMock()

    runraisenext.runraisenext(window_spec, run_function, windows,
                              firefox_window, focus_window_function)

    assert not run_function.called
    assert not focus_window_function.called


def test_main_calls_loop():
    """If there are multiple Firefox windows open and one of them is focused,
    runraisenext firefox should focus the next Firefox windows.

    Repeated calls should loop through all the Firefox windows, going back to
    the first one after the last one.

    """
    window_spec = {"command": "firefox", "wm_class": ".Firefox"}
    run_function = mock.MagicMock()
    firefox_window_1 = wmctrl.Window('2', '0', 'pid', 'Navigator.Firefox',
                                     'mistakenot', 'My Firefox Window')
    firefox_window_2 = wmctrl.Window('3', '0', 'pid', 'Navigator.Firefox',
                                     'mistakenot', 'My Other Firefox Window')
    windows = [
        firefox_window_1,
        firefox_window_2,
        wmctrl.Window('4', '0', 'pid', 'Navigator.Thunderbird', 'mistakenot',
                      'My Thunderbird Window'),
        wmctrl.Window('5', '0', 'pid', 'Terminal.Terminal', 'mistakenot',
                      'My Terminal Window'),
    ]
    focus_window_function = mock.MagicMock()

    runraisenext.runraisenext(window_spec, run_function, windows,
                              firefox_window_1, focus_window_function)

    assert not run_function.called
    assert focus_window_function.called_once_with(firefox_window_2)


def test_most_recently_raised_first():
    """When raising an app, the app's most recently focused window should be
    focused first."""
    raise NotImplementedError


# TODO: Tests for all the command-line options.
