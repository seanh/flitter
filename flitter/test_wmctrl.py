"""Tests for wmctrl.py."""

import mock

import flitter.wmctrl as wmctrl


def test_parse_wmctrl_window_line():
    """Test that _parse_wmctrl_window_line() returns the right result for a
    typical wmctrl -lxp output line.

    """
    expected_result = dict(
        window_id='0x042000b3',
        desktop='0',
        pid='4904',
        wm_class='Mail.Thunderbird',
        machine='mistakenot',
        title='Inbox - Unified Folders - Mozilla Thunderbird')
    assert wmctrl._parse_wmctrl_window_line(
        '0x042000b3  0 4904   Mail.Thunderbird      mistakenot Inbox - Unified '
        'Folders - Mozilla Thunderbird') == expected_result


def test_parse_wmctrl_window_line_with_spaces_in_wm_class():
    """Test that _parse_wmctrl_window_line() returns the right result when the
    wmctrl -lxp output line has a wm_class with spaces in it.

    The wmctrl -lxp output line items are separated by spaces, but the wm_class
    item may contain spaces so it's separated by double spaces on either side.

    """
    expected_result = dict(
        window_id='0x04400051',
        desktop='0',
        pid='5116',
        wm_class='Time Tracker.Hamster',
        machine='mistakenot',
        title='Time Tracker')
    assert wmctrl._parse_wmctrl_window_line(
        '0x04400051  0 5116   Time Tracker.Hamster  mistakenot '
        'Time Tracker') == expected_result


def test_window_eq_when_equal():
    """__eq__() should return True when given an equal other Window."""
    window_1 = wmctrl.Window('window_id', 'desktop', 'pid', 'wm_class',
                             'machine', 'title')
    window_2 = wmctrl.Window('window_id', 'desktop', 'pid', 'wm_class',
                             'machine', 'title')

    assert window_1 == window_2


def test_window_eq_when_not_equal():
    """__eq__() should return False when given an unequal other Window."""
    window_1 = wmctrl.Window('window_id', 'desktop', 'pid', 'wm_class',
                             'machine', 'title')
    window_2 = wmctrl.Window('window_id_2', 'desktop', 'pid_2', 'wm_class',
                             'machine', 'title')

    assert window_1 != window_2


def test_window_eq_when_not_a_window_object():
    """__eq__() should return False when given a non-Window object."""
    window = wmctrl.Window('window_id', 'desktop', 'pid', 'wm_class',
                           'machine', 'title')
    assert window != object()


def test_windows():
    """Test that _windows() returns the right windows.

    This includes windows with spaces in their WM_CLASS, with non-ASCII
    characters in their window title, etc. so that the wmctrl output parsing
    is tested.

    """
    window_list = open('example_wmctrl_window_list.txt', 'r').read()
    windows = wmctrl._windows(window_list)
    window_ids = [window.window_id for window in windows]
    expected_window_ids = [
        '0x02a00001', '0x03200002', '0x0280000a', '0x03200007', '0x03200011',
        '0x03200016', '0x0320001b', '0x0320001c', '0x02c000b3', '0x03e0000c',
        '0x04000155', '0x042000b3', '0x04400051', '0x04c00001', '0x05000012',
        '0x03e005d4', '0x0580002b', '0x05600003']

    assert window_ids == expected_window_ids


def test_focus():
    """Test that Window._focus() calls _run() as we expect it to."""
    window = wmctrl.Window('test_window_id', 'desktop', 'pid',
                           'Navigator.Firefox', 'machine', 'title')
    mock_run_function = mock.MagicMock()

    window._focus(mock_run_function)

    assert mock_run_function.called_once_with('wmctrl -i -a test_window_id')


def test_focused_window():
    """Test that _focused_window() returns the right Window."""
    # Example output from wmctrl -a :ACTIVE: -v
    wmctrl_output = '''envir_utf8: 1
Using window: 0x03e00008
'''
    matching_window = wmctrl.Window('0x03e00008', 'desktop', 'pid', 'wm_class',
                                    'machine')
    windows = [
        wmctrl.Window('window_id', 'desktop', 'pid', 'wm_class', 'machine'),
        matching_window,
        wmctrl.Window('second_window_id', 'desktop', 'pid', 'wm_class',
                      'machine'),
    ]
    assert wmctrl._focused_window(wmctrl_output, windows) == matching_window
