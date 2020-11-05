#!/usr/bin/python3
"""
Program asks first email address, show letters sent from this email, catched with sendmail,
then you choose letter of your interest and  get all sendmail actions with this letter.
"""  # Program has cli interface.

import re
import os
import math
import platform
import collections.abc
import subprocess
from io import TextIOWrapper
import argparse
import datetime

import curses
import curses.ascii
import curses.textpad

WARN_COLOR = 98
ERROR_COLOR = 99
PROG_BG_COLOR = 111
ON_CURSOR_COLOR = 100
DEFAULT_PATH_TO_SENDMAIL_LOG = './message.log'  # '/var/log/messages.log'     # TODO: REPLACE


def conf_args_parser() -> argparse.Namespace:
    """
    Function config program cli interface.

    Returns
    -------
    :return: argparse.Namespace
        Namespace of program arguments
    """
    default_path_to_sendmail_log = DEFAULT_PATH_TO_SENDMAIL_LOG
    meta_info = "DEFAULT PATH TO SENDMAIL LOGS{1}\t{0}{1}".format(default_path_to_sendmail_log,
                                                                  os.linesep)
    # define and conf parser
    parser = argparse.ArgumentParser(description=__doc__, prog='gather_send_mail_log',
                                     epilog=meta_info, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--path_to_log', '-P', default=default_path_to_sendmail_log, dest="path_to_log", nargs='?',
                        help='change default path to sendmail logs', action='store')
    return parser.parse_args()


def universal_grep(file: (TextIOWrapper, str), patterns: (str, list), as_list=False) -> (list, str):
    """
    Function imitate linux grep, and returns list of lines from :file: that matches :pattern:

    Parameters
    This is a ops wrong word.
    This is a ops wrong word.
    ----------
    :param file: TextIOWrapper(opened file) or str
        File object or string where to search for :pattern:
    :param patterns: str, list
        Pattern is one or patterns separated by newline characters for grep to search for in :file:
    :param as_list: bool
        If is True, return list of strings that matches :pattern:, instead of gathering them in one str obj.

    Returns
    -------
    :return: list or str
        List of strings row or gathered in str obj, each line of which matches :pattern:
    """

    assert isinstance(file, (TextIOWrapper, str)), ValueError(
        ":file: param must be str or link to opened file.")
    assert isinstance(patterns, (str, list, tuple, set)), ValueError(":pattern: must be string.")

    if isinstance(file, TextIOWrapper):
        # it`s unnecessary to load all file in memory, it`s enough to be able to iter by lines
        iterable_obj = file

    else:
        # split str object by liens, to be able to iter though it similar as though file
        iterable_obj = re.split("\r?\n", file)

    result = []
    # if list of patterns
    if not isinstance(patterns, str):
        for line in iterable_obj:
            if re.findall(patterns[0], line):
                result.append(re.sub("\r?\n", "", line.strip(" ")))
        if len(patterns) > 1:
            for pattern in patterns[1:]:
                result = (line for line in result if re.findall(pattern, line))
    # it the only pattern
    else:
        for line in iterable_obj:
            if re.findall(patterns, line):
                result.append(re.sub("\r?\n", "", line.strip(" ")))

    if not as_list:
        # gathering list of strings to one string
        result = os.linesep.join(result)

    if isinstance(file, TextIOWrapper):
        # Change the stream position to the start of stream
        file.seek(0, 0)

    return result


def linux_zgrep(file, patterns: (list, str), as_list=False):
    """
    Function use linux zgrep, and returns list of lines from :file:(even if :file: is compessed) that matches :pattern:

    Parameters
    ----------
    :param file: str
        path to file or text in which to search for :pattern:
    :param patterns: str, list
        Pattern is one or patterns separated by newline characters for grep to search for in :file:
    :param as_list: bool
        If is True, return list of strings that matches :pattern:, instead of gathering them in one str obj.

    Returns
    -------
    :return: list or str
        List of strings row or gathered in str obj, each line of which matches :pattern:
        """
    if isinstance(patterns, (list, tuple, set)):
        pattern = "".join(("(?=.*{})".format(i) for i in patterns))
    else:
        pattern = "(?=.*{})".format(patterns)

    out = subprocess.Popen(["zgrep", "-s", "-P", pattern, file],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL)
    std = [i.decode("utf-8") for i in out.communicate() if i]
    res = ''.join(std)
    if as_list:
        res = res.split('\n')

    return res


def linux_if_file_exist(file_path: str):
    """Function gives information if file at :file_path: exist."""
    out = subprocess.Popen(["file", file_path],
                           stdout=subprocess.PIPE)
    std = "".join([i.decode("utf-8") for i in out.communicate() if i])
    returncode = 1

    if "(No such file or directory)" in std:
        returncode = 0
    return returncode


def universal_if_file_exist(file_path: str):
    """Function gives information if file at :file_path: exist."""
    out = os.path.isfile(file_path)
    return out


class Button:
    """Class of buttons on screen to work better with curses functions."""

    def __init__(self, text, coordinates, color=0, key=None, bg_color=0, is_keyboard_reachable=False,
                 button_action=None):
        self.text = text
        self.coordinates = coordinates
        self.color = self.__init_color(color, bg_color)
        self.key = key
        self.is_keyboard_reachable = is_keyboard_reachable
        self.__button_action = button_action

    def __init_color(self, color, bg_color):
        """Method init color pare."""
        if color != 0 and curses.has_colors():
            curses.init_pair(color, color, bg_color)
        return color

    def print_on(self, screen, is_bold=False):
        """
        Method print given text on given coordinates, with given colors.

        Parameters
        ----------
        :param screen: _CursesWindow
            Screen on which to print. By default self.stdscr.
        """
        if is_bold:
            screen.attron(curses.color_pair(ON_CURSOR_COLOR))  # is on cursor
        elif self.color != 0:
            screen.attron(curses.color_pair(self.color))
        try:
            screen.addstr(*self.coordinates, self.text)
        except curses.error:
            pass

        if is_bold:
            screen.attroff(curses.color_pair(ON_CURSOR_COLOR))  # is on cursor
        elif self.color != 0:
            screen.attroff(curses.color_pair(self.color))

    def is_pressed(self, character_pressed=None):
        """Method check whether button was pressed, or clicked by mouse, if so, returns True."""
        return character_pressed and self.key == character_pressed

    def act(self, *args, **kwargs):
        """Method define what button do when pressed."""
        if self.__button_action:
            self.__button_action(*args, **kwargs)


class Warnings:
    """Class of warnings messages on screen to work better with curses functions."""

    def __init__(self, text, coordinates, is_err=False, win_width=40, to_center=True, to_do_frame=True):
        """
        :param to_center: Define if to locate message window on :coordinates: by it`s center
        """
        self.text = text
        if to_center:
            self.coordinates = [coordinates[0] - 2, coordinates[1] - win_width // 2]  # to center text
            self.__indent = 4  # indent one line up and down of text
            win_width += 2
        else:
            self.text = " " + self.text
            self.coordinates = coordinates
            self.__indent = 2

        if not to_do_frame:
            self.__indent -= 2
            self.coordinates[0] += 2

        self.is_err = is_err
        self.__to_center = to_center
        self.__to_do_frame = to_do_frame
        self.win_width = win_width
        self.screen_to_del = None
        self.screen_to_del_on = None

    def __create_screen(self, win_width):
        if not self.__to_do_frame:
            win_height = math.ceil(len(self.text) / win_width)
        else:
            win_height = math.ceil(len(self.text) / win_width) + self.__indent
        _window = curses.newwin(win_height, win_width, *self.coordinates)
        # create border
        if self.__to_do_frame:
            _window.box()

        if self.is_err:
            _window.bkgd(' ', curses.color_pair(ERROR_COLOR) | curses.A_BOLD)

        else:
            _window.bkgd(' ', curses.color_pair(WARN_COLOR) | curses.A_BOLD)

        window = _window.subwin(win_height, win_width, *self.coordinates)
        return window

    def show(self, screen, leave_on_screen=False):
        """
        Method print given text on given coordinates, in appropriate frame up to any button would be pressed.
        If :leave on screen:, does not hide message, until hide method would me called.
        """
        __screen = self.__create_screen(self.win_width)

        if self.is_err and self.__to_do_frame:
            title = " Error "
            __screen.addstr(0, self.win_width // 2 - len(title) // 2, title)
            __screen.attron(curses.color_pair(ERROR_COLOR))
        else:
            __screen.attron(curses.color_pair(WARN_COLOR))

        text = self.text
        if not self.__to_do_frame:
            line = 0
            x_start = 0
        elif self.__to_center:
            line = 2
            x_start = 1
        else:
            line = 1
            x_start = 1

        while text:
            if len(text) > self.win_width - self.__indent:
                pr_text = text[:self.win_width - self.__indent]

                if self.__to_center:  # to locate on center of a screen
                    __screen.addstr(line, self.win_width // 2 - len(pr_text) // 2, pr_text)
                else:
                    __screen.addstr(line, x_start, pr_text)

                text = text[self.win_width - self.__indent:]
                line += 1
            else:

                if self.__to_center:  # to locate on center of a screen
                    __screen.addstr(line, self.win_width // 2 - len(text) // 2, text)
                else:
                    __screen.addstr(line, x_start, text)

                text = ''

        if self.is_err:
            __screen.attroff(curses.color_pair(ERROR_COLOR))
        else:
            __screen.attroff(curses.color_pair(WARN_COLOR))

        __screen.refresh()

        if not leave_on_screen:
            # wait for any button is pressed
            ch = __screen.getch()

            # cleaning entered window
            del __screen
            screen.touchwin()
            screen.refresh()
            # return pressed ch
            return ch
        else:
            # save windows to clear them later
            self.screen_to_del = __screen
            self.screen_to_del_on = screen

    def hide(self):
        """Method clear warning from screen."""
        # cleaning entered window
        if self.screen_to_del and self.screen_to_del_on:
            del self.screen_to_del
            self.screen_to_del_on.touchwin()
            self.screen_to_del_on.refresh()

            self.screen_to_del = None
            self.screen_to_del_on = None


class MovingOrganizer:
    """Class organize simple cursor moving """

    def __init__(self, screen, print_with_indent=False, field_actions=None):
        self.is_active = False
        self._queue = []  # Buttons
        self._pointer = 0
        self.__screen = screen
        self.__wind_height, self.__wind_width = self.__screen.getmaxyx()

        self.first_visible = 0
        self.last_visible = 0

        self.__indent = 0
        self.__print_with_indent = int(print_with_indent)
        self.__field_actions = field_actions

    @property
    def __active_queue(self):
        return self._queue[self.first_visible: self.last_visible]

    @property
    def active_element(self):
        """Method returns active button object."""
        if self.__active_queue:
            return self.__active_queue[self._pointer]

    def refill_elements(self, elements: collections.abc.Iterable):
        """Method change current queue elements to given, and reset pointer."""
        self._pointer = 0
        self.__clear_queue()
        self.__add_elements(elements)

        self.first_visible = 0
        self.last_visible = 0

        if self.__indent != 0:
            self.last_visible = self.__wind_height // self.__indent

    def __add_elements(self, list_):
        """Method add button objects to queue."""
        line_num = 0
        if list_:
            self.__indent = max(map(lambda x: math.ceil(len(x) / self.__wind_width) + self.__print_with_indent, list_))

        for field in list_:
            self._queue.append(Button(text=field, coordinates=[line_num, 0],
                                      is_keyboard_reachable=True, button_action=self.__field_actions))

            if line_num < self.__wind_height - (self.__indent - 1):
                line_num += self.__indent  # plus num of lines in field

    def __clear_queue(self):
        """Method clear queue"""
        self._queue = []

    def move_up(self):
        """Method change active button to one, up in queue."""
        # to do scrolling
        if (self.first_visible > 0) and (self._pointer == 0):

            for button in self.__active_queue:
                button.coordinates[0] = button.coordinates[0] + self.__indent

            self.first_visible -= 1
            self.last_visible -= 1

            self.draw_on_screen()

        elif self._pointer > 0:
            self.__active_queue[self._pointer].print_on(self.__screen, is_bold=False)
            self._pointer -= 1
            self.__active_queue[self._pointer].print_on(self.__screen, is_bold=True)

            self.__screen.refresh()
        else:
            return 1  # err sign

    def move_down(self):
        """Method change active button to one, down in queue."""
        # to do scrolling
        if (self.last_visible < len(self._queue) - 1) and \
                (self._pointer == len(self.__active_queue) - 1):
            self.first_visible += 1
            self.last_visible += 1

            for button in self.__active_queue:
                button.coordinates[0] = button.coordinates[0] - self.__indent

            self.draw_on_screen()

        elif self._pointer < len(self.__active_queue) - 1:
            self.__active_queue[self._pointer].print_on(self.__screen, is_bold=False)
            self._pointer += 1
            self.__active_queue[self._pointer].print_on(self.__screen, is_bold=True)

            self.__screen.refresh()
        else:
            return 1  # err sign

    def draw_on_screen(self):
        """Method draw menu on screen."""
        self.__screen.clear()
        self.__screen.bkgd(' ', curses.color_pair(PROG_BG_COLOR))
        for num, button in enumerate(self.__active_queue):
            is_bold = False
            if num == self._pointer:
                is_bold = True
            button.print_on(self.__screen, is_bold=is_bold)
        self.__screen.refresh()

    def highlight(self, un_do=False):
        if self.active_element:
            self.active_element.print_on(self.__screen, is_bold=(not un_do))
        self.__screen.refresh()


class CliGraphInterface:
    """
    Program asks first email address, show letters sent from this email, caught with sendmail,
    then you choose letter of your interest and  get all sendmail actions with this letter.
    """

    def __init__(self):
        self.parser_arg = conf_args_parser()  # all arguments from cli execution
        self.path_to_log = self.parser_arg.path_to_log
        if platform.platform().startswith("Linux"):
            self.__grep = linux_zgrep
            self.__file_checker = linux_if_file_exist
        else:
            self.__grep = universal_grep
            self.__file_checker = universal_if_file_exist
        self.__continue_entering = ''
        self.email_to_search = ''
        self.date_to_search = ""
        self.__num_of_ids = 0
        self.__active_id_num = 0
        self.max_email_length = 33
        self.first_table_width = 18
        self.patterns_to_search_for = {}  # type - pattern

        self.stdscr = curses.initscr()  # initialize curses screen

        self.wind_height, self.wind_width = self.stdscr.getmaxyx()

        self.check_minimum_term_size()

        # hide cursor
        curses.curs_set(0)

        # init color pairs
        curses.start_color()
        self.background_color = curses.COLOR_BLUE
        curses.init_pair(111, curses.COLOR_WHITE, self.background_color)  # program bg color
        curses.init_pair(99, curses.COLOR_WHITE, curses.COLOR_RED)  # error messages
        curses.init_pair(98, curses.COLOR_BLUE, curses.COLOR_WHITE)  # warn messages
        curses.init_pair(100, curses.COLOR_BLACK, curses.COLOR_CYAN)  # is on cursor

        # set bg color
        self.stdscr.bkgd(' ', curses.color_pair(111) | curses.A_BOLD)

        # make two tables working to
        self.__left_window = curses.newwin(self.wind_height - 6, self.first_table_width - 3, 3, 2)
        self.left_window = self.__left_window.subwin(3, 2)
        self.__left_window.bkgd(" ", curses.color_pair(PROG_BG_COLOR) | curses.A_BOLD)

        self.__right_window = curses.newwin(self.wind_height - 6, self.wind_width - self.first_table_width - 3,
                                            3, self.first_table_width + 1)
        self.right_window = self.__right_window.subwin(3, self.first_table_width + 2)
        self.__right_window.bkgd(" ", curses.color_pair(PROG_BG_COLOR) | curses.A_BOLD)

        # make moving organizers for right and left tables
        self.left_table = MovingOrganizer(screen=self.left_window, field_actions=self.read_logs)
        self.right_table = MovingOrganizer(screen=self.right_window)

        self.active_table = self.left_table
        self.active_table.is_active = True

        curses.noecho()  # turn off auto echoing of keypress on to screen
        curses.cbreak()  # enter break mode where pressing Enter key
        self.stdscr.keypad(True)  # enable special Key values such as curses.KEY_LEFT etc

        # buttons to appear on screen
        self.buttons = []

        # get log location button
        log_button = Button(text="Log file: ".format(self.path_to_log),
                            coordinates=[self.wind_height - 3, 2])
        self.buttons.append(log_button)
        self.len_of_log_loc_intro = len(log_button.text) + 2

        # add email location button
        email_button = Button(text="Email: ",
                              coordinates=[1, 2])
        self.buttons.append(email_button)
        self.len_of_email_intro = len(email_button.text) + 2  # 2 -len of indent

        # add date location button
        date_button = Button(text="Date: ",
                             coordinates=[1, self.len_of_email_intro + self.max_email_length + 2])
        self.buttons.append(date_button)
        self.len_of_date_intro = len(date_button.text) + 2  # 2 -len of indent

        # init F__ buttons
        f_buttons = [Button(text="[ F2 Email ]", key=curses.KEY_F2, coordinates=[],
                            button_action=self.change_email),
                     Button(text="[ F3 Date ]", key=curses.KEY_F3, coordinates=[],
                            button_action=self.change_date_to_search),
                     Button(text="[ F4 Reread ]", key=curses.KEY_F4, coordinates=[],
                            button_action=self.read_logs),
                     Button(text="[ F9 Select log file ]", key=curses.KEY_F9, coordinates=[],
                            button_action=self.change_log_loc),
                     Button(text="[ F10 Exit ]", key=curses.KEY_F10,
                            coordinates=[], button_action=self.shut_down)]

        # get F__ buttons location
        button_x_pos = 2
        button_y_pos = self.wind_height - 2
        for button in f_buttons:
            button.coordinates = [button_y_pos, button_x_pos]
            button_x_pos += len(button.text) + 2
            if button_x_pos // self.wind_width:
                button_y_pos -= 1
                button_x_pos = 1

        # add f_buttons to other
        self.buttons += f_buttons

    @property
    def __sys_path_to_log(self):
        """Needs to differ windows and linux path."""
        return self.path_to_log + ("$#universal_grep_path" * (not platform.platform().startswith("Linux")))

    def check_minimum_term_size(self):
        """Method check and shut down program if term size is too small."""
        # check minimum term size
        if self.wind_height < 11 or self.wind_width < 50:
            self.shut_down(1, message="Too small terminal window to work in program.")

    def change_email(self, possible_to_cancel=True, exact_mail=None):
        """Method create window to enter new e-mail to search for."""
        to_save = True  # define whether to save entrance of textbox
        to_shut_down = False  # define whether to close program just after text box finishing

        if exact_mail:
            mail = exact_mail
            self.email_to_search = mail
            to_save = False

        else:
            def validator(ch):
                """Function change some entered characters to another."""
                if ch == curses.ascii.ESC:
                    nonlocal possible_to_cancel  # it`s bad practice, but i have nothing to do
                    if possible_to_cancel:
                        ch = curses.ascii.BEL  # Enter
                        nonlocal to_save
                        to_save = False
                if ch == curses.KEY_F10:
                    nonlocal to_shut_down
                    to_shut_down = True
                    ch = curses.ascii.BEL  # Enter
                if ch == curses.KEY_RESIZE:
                    self.resize_terminal(continue_entering="email")
                    win.bkgd(' ', curses.color_pair(0) | curses.A_BOLD)
                return ch

            mail = ""
            # create window
            while not mail:
                win = curses.newwin(1, self.max_email_length, 1, self.len_of_email_intro)  # 9 - len of email intro
                sub = win.subwin(1, self.len_of_email_intro)
                curses.curs_set(1)
                curses.cbreak()
                win.keypad(True)

                # create text pad to write in
                tb = curses.textpad.Textbox(sub)
                win.refresh()
                tb.edit(validate=validator)

                if to_shut_down:
                    self.shut_down()

                # change existing e-mail address
                if to_save:
                    mail = tb.gather()[:-1]  # last ch is space
                else:
                    mail = self.email_to_search

                # cleaning entered window
                del win
            self.stdscr.touchwin()
            self.stdscr.refresh()
            curses.curs_set(0)

        # logs rereading
        if to_save:
            self.patterns_to_search_for.update({"email": mail})
            if self.read_logs():  # return err sign
                self.patterns_to_search_for.pop("email")
                mail = self.email_to_search  # return previous one
            else:
                self.email_to_search = mail
        self.draw_tables()
        # fill by first output
        button = self.active_table.active_element
        if button:
            button.act(button.text)

        fillers = "_" * (self.max_email_length - len(mail) - 1)

        # print email
        self.print_on_screen((1, self.len_of_email_intro), mail, curses.COLOR_CYAN)
        self.print_on_screen((1, self.len_of_email_intro + len(mail)), fillers)

        self.stdscr.refresh()

    def refresh_ids_ord_number(self):
        """Method redraw on screen exact highlighted id`s ordinary number."""
        if not self.__num_of_ids:
            return
        indent = 2
        ids_num = "{0:->{1}}-{2}".format(self.__active_id_num - 1, len((self.__num_of_ids + 1).__repr__()),
                                         self.__num_of_ids + 1)
        ids_num_cordinates = (2, self.first_table_width - len(ids_num) - indent)

        # to clean location
        self.print_on_screen((2, 4), "-"*(self.first_table_width - 4))

        self.print_on_screen(ids_num_cordinates, ids_num)

    def resize_terminal(self, continue_entering=None):
        """Method resize terminal and redraw all info onto it."""
        old_path_to_log = self.path_to_log
        old_mail = self.email_to_search
        old_date = self.date_to_search
        self.wind_height, self.wind_width = self.stdscr.getmaxyx()

        self.check_minimum_term_size()

        # make two tables working to
        old_left_table_text = [button.text for button in self.left_table._queue]
        old_right_table_text = [button.text for button in self.right_table._queue]
        if self.right_table.is_active:
            active_one = "right"
        else:
            active_one = "left"

        del self.__left_window, self.__right_window, self.left_table, \
            self.right_table, self.left_window, self.right_window

        self.__left_window = curses.newwin(self.wind_height - 7, self.first_table_width - 3, 3, 2)
        self.left_window = self.__left_window.subwin(3, 2)
        self.__left_window.bkgd(" ", curses.color_pair(PROG_BG_COLOR) | curses.A_BOLD)

        self.__right_window = curses.newwin(self.wind_height - 7, self.wind_width - self.first_table_width - 3,
                                            3, self.first_table_width + 1)
        self.right_window = self.__right_window.subwin(3, self.first_table_width + 2)
        self.__right_window.bkgd(" ", curses.color_pair(PROG_BG_COLOR) | curses.A_BOLD)

        # make moving organizers for right and left tables
        self.left_table = MovingOrganizer(screen=self.left_window, field_actions=self.read_logs)
        self.right_table = MovingOrganizer(screen=self.right_window, print_with_indent=True)

        self.left_table.refill_elements(old_left_table_text)
        self.right_table.refill_elements(old_right_table_text)

        if active_one == "left":
            self.active_table = self.left_table
        else:
            self.active_table = self.right_table

        # buttons to appear on screen
        self.buttons = []

        # get log location button
        log_button = Button(text="Log file: ".format(self.path_to_log),
                            coordinates=[self.wind_height - 3, 2])
        self.buttons.append(log_button)
        self.len_of_log_loc_intro = len(log_button.text) + 2

        # add email location button
        email_button = Button(text="Email: ",
                              coordinates=[1, 2])
        self.buttons.append(email_button)
        self.len_of_email_intro = len(email_button.text) + 2  # 2 -len of indent

        # add date location button
        date_button = Button(text="Date: ",
                             coordinates=[1, self.len_of_email_intro + self.max_email_length + 2])
        self.buttons.append(date_button)
        self.len_of_date_intro = len(date_button.text) + 2  # 2 -len of indent

        # init F__ buttons
        f_buttons = [Button(text="[ F2 Email ]", key=curses.KEY_F2, coordinates=[],
                            button_action=self.change_email),
                     Button(text="[ F3 Date ]", key=curses.KEY_F3, coordinates=[],
                            button_action=self.change_date_to_search),
                     Button(text="[ F4 Reread ]", key=curses.KEY_F4, coordinates=[],
                            button_action=self.read_logs),
                     Button(text="[ F9 Select log file ]", key=curses.KEY_F9, coordinates=[],
                            button_action=self.change_log_loc),
                     Button(text="[ F10 Exit ]", key=curses.KEY_F10,
                            coordinates=[], button_action=self.shut_down)]

        # get F__ buttons location
        button_x_pos = 2
        button_y_pos = self.wind_height - 2
        for button in f_buttons:
            button.coordinates = [button_y_pos, button_x_pos]
            button_x_pos += len(button.text) + 2
            if button_x_pos // self.wind_width:
                button_y_pos -= 1
                button_x_pos = 1

        # add f_buttons to other
        self.buttons += f_buttons

        # draw
        self.stdscr.clear()

        self.make_frame()
        self.draw_buttons()
        if not continue_entering == "file_path":
            self.change_log_loc(exact_file=old_path_to_log)
        if not continue_entering == "date":
            self.change_date_to_search(exact_date=old_date)
        if not continue_entering == "email":
            self.change_email(exact_mail=old_mail)

        self.right_table.draw_on_screen()
        self.left_table.draw_on_screen()
        self.draw_tables()

        # update screen
        # self.stdscr.refresh()

    def change_date_to_search(self, by_def=False, exact_date=None):
        """Method create window to enter new date to search for."""
        to_save = True  # define whether to save entrance of textbox
        to_shut_down = False  # define whether to close program just after text box finishing
        to_finish_entering = False  # # define whether to close program if esc was pressed

        line_width = 8
        date_entering_start_coordinates = \
            [1, self.max_email_length + self.len_of_date_intro + self.len_of_email_intro]

        if exact_date:
            date_to_search = exact_date
            self.date_to_search = date_to_search
            to_save = False

        elif by_def:
            to_save = False  # leave default one
            date_to_search = "__-__ "
            self.date_to_search = date_to_search

        else:
            def validator(ch):
                """Function change some entered characters to another."""
                if ch == curses.ascii.ESC:
                    ch = curses.ascii.BEL  # Enter
                    nonlocal to_save, to_finish_entering
                    to_save = False
                    to_finish_entering = True
                if ch == curses.KEY_F10:
                    nonlocal to_shut_down
                    to_shut_down = True
                    ch = curses.ascii.BEL  # Enter
                if ch == curses.KEY_BACKSPACE:
                    nonlocal indent
                    if (indent - 2) == win_.getmaxyx()[1]:  # last possible character
                        indent = indent - 1

                    # restore fillers
                    win_.addstr(0, indent - 3, "_")
                if ch == curses.KEY_RESIZE:
                    self.resize_terminal(continue_entering="date")
                    win_.bkgd(' ', curses.color_pair(0))
                    for pos in range(line_width - 1):
                        if pos in (3,):
                            win_.addstr(0, pos, "-")
                        elif pos in (2, 4):
                            pass
                    win_.refresh()

                return ch

            month_num_to_name = {'1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr', '5': 'May', '6': 'Jun',
                                 '7': 'Jul', '8': 'Aug', '9': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec', "__": "__",
                                 "**": "**"}
            date = {"day": "", "month": ""}

            # create window
            win_ = curses.newwin(1, line_width,
                                 *date_entering_start_coordinates)
            curses.curs_set(1)

            # set bg color
            # win_.bkgd(' ', curses.color_pair(111) | curses.A_BOLD)

            # add delimiters
            for pos in range(line_width - 1):
                if pos in (3,):
                    win_.addstr(0, pos, "-")
                elif pos in (2, 4):
                    pass
                else:
                    win_.addstr(0, pos, "_")

            # show help message
            help_ = Warnings("day - month",
                             (date_entering_start_coordinates[0] + 1, date_entering_start_coordinates[1] + 3),
                             win_width=len("day - month") + 2, to_do_frame=False, to_center=True)
            help__ = Warnings("[1-31] - [1-12]",
                              (date_entering_start_coordinates[0] + 2, date_entering_start_coordinates[1] + 3),
                              win_width=len("[1-31] - [1-12]") + 2, to_do_frame=False, to_center=True)

            help_.show(self.stdscr, leave_on_screen=True)
            help__.show(self.stdscr, leave_on_screen=True)
            # create and fill text boxes
            indent = 0
            for type_, len_ in {"day": 2, "month": 2}.items():
                len_ += 1

                sub = win_.subwin(1, len_, date_entering_start_coordinates[0],
                                  date_entering_start_coordinates[1] + indent)

                indent += len_ + 2

                curses.cbreak()
                win_.keypad(True)

                # create text pad to write in
                tb = curses.textpad.Textbox(sub)
                win_.refresh()
                tb.edit(validate=validator)

                if to_finish_entering:
                    break

                if to_shut_down:
                    self.shut_down()

                # add to date dict
                date.update({type_: tb.gather().rstrip(" ")})

            # cleaning entered window
            del win_
            self.stdscr.touchwin()
            self.stdscr.refresh()
            curses.curs_set(0)

            # redraw id and log messages tables
            self.draw_tables()

            # change date some way
            if date["month"] not in ["__", "**"]:
                date["month"] = date["month"].lstrip("0").strip("_").strip(" ")
            if date["month"] == '':
                date["month"] = "__"

            if date["day"] not in ["__", "**"]:
                date["day"] = date["day"].lstrip("0").strip("_").strip(" ")
            if date["day"] == '':
                date["day"] = "__"

            # check input
            if not date["month"] in month_num_to_name.keys():
                err = Warnings("Wrong month number `{}`".format(date["month"]),
                               (self.wind_height // 2, self.wind_width // 2), is_err=True)
                err.show(self.stdscr)
                to_save = False

            elif not date["day"] in list(str(i) for i in range(1, 32)) + ["__", "**"]:
                err = Warnings("Wrong day number `{}`".format(date["day"]),
                               (self.wind_height // 2, self.wind_width // 2), is_err=True)
                err.show(self.stdscr)
                to_save = False

            # change existing date
            if to_save:
                date_to_search = "{} {}".format(month_num_to_name[date["month"]], date["day"])

                # change to today date if only right fillers where specified
                if set(date_to_search) - {"*", " "} == set():
                    data = datetime.date.today()
                    date_to_search = "%s %02d" % (month_num_to_name[str(data.month)], data.day)
                # fill by first output
                button = self.active_table.active_element
                if button:
                    button.act(button.text)

        # logs rereading
        if to_save:
            # fillers for not to specified date
            if set(date_to_search) - {"_", "-", " "} == set():
                # in case if date wasn't added yet
                date_to_search = "__-__ "
                if "date" in self.patterns_to_search_for.keys():
                    self.patterns_to_search_for.pop("date")
            else:
                self.patterns_to_search_for.update({"date": date_to_search})

            # set today data and reading logs
            self.print_on_screen(date_entering_start_coordinates, date_to_search, curses.COLOR_CYAN)
            if not (by_def and self.read_logs()):  # return 1 if err happens
                self.date_to_search = date_to_search

            # fill by first output
            button = self.active_table.active_element
            if button:
                button.act(button.text)

        else:
            # redraw existing id and log messages tables
            self.draw_tables()

        # print date
        self.print_on_screen(date_entering_start_coordinates, self.date_to_search, curses.COLOR_CYAN)

        self.stdscr.refresh()

    def change_log_loc(self, by_def=False, exact_file=None):
        """Method create window to enter log file location to search where."""

        to_save = True  # define whether to save entrance of textbox
        to_shut_down = False  # define whether to close program just after text box finishing
        err_to_show = None  # if something goes wrong
        line_width = 50
        log_entering_start_coordinates = [self.wind_height - 3, self.len_of_log_loc_intro]

        if exact_file:
            path_to_log = exact_file
            self.path_to_log = path_to_log
            to_save = False

        elif by_def:
            path_to_log = self.path_to_log
            to_save = True

        else:
            def validator(ch):
                """Function change some entered characters to another."""
                if ch == curses.KEY_RESIZE:
                    self.resize_terminal(continue_entering="file_path")
                    ch = curses.ascii.ESC

                if ch == curses.ascii.ESC:
                    ch = curses.ascii.BEL  # Enter
                    nonlocal to_save
                    to_save = False

                if ch == curses.KEY_F10:
                    nonlocal to_shut_down
                    to_shut_down = True
                    ch = curses.ascii.BEL  # Enter

                return ch

            # create window
            win = curses.newwin(1, line_width,
                                *log_entering_start_coordinates)
            sub = win.subwin(*log_entering_start_coordinates)

            # set bg color
            # win.bkgd('-', curses.color_pair(111) | curses.A_BOLD)

            curses.cbreak()
            curses.curs_set(1)
            win.keypad(True)

            # create text pad to write in
            tb = curses.textpad.Textbox(sub)
            win.refresh()
            tb.edit(validate=validator)

            if to_shut_down:
                self.shut_down()

            # change existing e-mail address
            if to_save:
                path_to_log = tb.gather()[:-1]  # last ch is space
            else:
                path_to_log = self.path_to_log

            # cleaning entered window
            del win
            self.stdscr.touchwin()
            self.stdscr.refresh()
            curses.curs_set(0)

        fillers = " " + "-" * (line_width - len(path_to_log) - 1)

        if to_save:
            if self.__file_checker(path_to_log):

                # change existing e-mail address and logs rereading
                old_path = self.path_to_log
                self.path_to_log = path_to_log
                if not by_def and self.read_logs():  # return err sign
                    self.path_to_log = old_path

                    err_to_show = Warnings("File `{}` is not a log file.".format(path_to_log),
                                           (self.wind_height // 2, self.wind_width // 2), is_err=True)

                # fill by first output
                button = self.active_table.active_element
                if button:
                    button.act(button.text)

            # if file does not exist
            else:
                err_to_show = Warnings("File `{}` does not exist.".format(path_to_log),
                                       (self.wind_height // 2, self.wind_width // 2), is_err=True)

        # print log location
        self.print_on_screen(log_entering_start_coordinates, self.path_to_log, curses.COLOR_CYAN)
        log_entering_start_coordinates[1] += len(self.path_to_log)  # move cursor just after log
        self.print_on_screen(log_entering_start_coordinates, fillers)

        # redraw existing id and log messages tables
        self.draw_tables()

        # show err if some occurs
        if err_to_show:
            err_to_show.show(self.stdscr)
            # redraw tables
            self.draw_tables()

        self.stdscr.refresh()

    def make_frame(self):
        """Method set right program frame."""
        # frame
        self.stdscr.border('|', '|', '-', '-', '/', '\\', '\\', '/')

        # horizontal lines
        for coordinates in [(self.wind_height - 3, 0), (2, 0)]:
            self.print_on_screen(coordinates, "+{}+".format("-" * (self.wind_width - 2)))

        # vertical line
        for row in (self.first_table_width,):
            self.print_on_screen((2, row), "+")
            for line in range(3, self.wind_height - 3):
                self.print_on_screen((line, row), "|")
            self.print_on_screen((line + 1, row), "+")

        # add lables
        for lable_name, coordinates in {"ID": (2, 2), "LOG": (2, self.first_table_width + 2)}.items():
            self.print_on_screen(coordinates, lable_name)

        # update screen
        self.stdscr.refresh()

    def conf_args_parser(self) -> argparse.Namespace:
        """
        Function config program cli interface.

        Returns
        -------
        :return: argparse.Namespace
            Namespace of program arguments
        """
        default_path_to_sendmail_log = './message.log'
        exit_status = "{}".format(os.linesep).join(["\t{}: {}".format(status, description)
                                                    for status, description in
                                                    {1: "Wrong path to sendmail logs was given",
                                                     2: "Wrong e-mail address to search for",
                                                     3: "Wrong unique id for given e-mail"}.items()])
        meta_info = "DEFAULT PATH TO SENDMAIL LOGS{1}\t{0}{1}\nEXIT STATUS{1}{2}".format(default_path_to_sendmail_log,
                                                                                         os.linesep, exit_status)
        # define and conf parser
        parser = argparse.ArgumentParser(description=self.__doc__, prog='gather_send_mail_log',
                                         epilog=meta_info, formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--version', action='version', version='%(prog)s 1.0')
        parser.add_argument('--path_to_log', '-P', default=default_path_to_sendmail_log, dest="path_to_log", nargs='?',
                            help='change default path to sendmail logs', action='store')

        return parser.parse_args()

    def shut_down(self, state=0, message='', with_confirm=False):
        """Method set all terminal settings back to normal and close window."""
        if with_confirm:
            conf = Warnings("Do you want to close application? Press ESC ones more to exit.",
                            (self.wind_height // 2, self.wind_width // 2),
                            win_width=len("Do you want to close application? ") + 2)
            exit_ch = conf.show(self.stdscr)

            if exit_ch != curses.ascii.ESC:
                # redraw tables
                self.draw_tables()
                return

        curses.nocbreak()
        curses.curs_set(1)
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        if message:
            print(message)
        exit(state)

    def print_on_screen(self, coordinates, text, color_num=0, screen=None, bg_color=None):
        """
        Method print given text on given coordinates, with given colors.

        Parameters
        ----------
        :param coordinates: iterable(tuple)
            (y, x) Coordinates where text starts.
        :param text: str
            Text to print
        :param color_num: int
            Number of color pare, inited in advance.
        :param screen: _CursesWindow
            Screen on which to print. By default self.stdscr.
        :param bg_color: int
            Background color of text. If None - self.background_color is used.
        """
        if screen is None:
            screen = self.stdscr
        if bg_color is None:
            bg_color = self.background_color

        if color_num != 0 and curses.has_colors():  # different color
            curses.init_pair(color_num, color_num, bg_color)
            screen.attron(curses.color_pair(color_num))

        try:
            screen.addstr(*coordinates, text)
        except curses.error:
            pass

        if color_num != 0 and curses.has_colors():  # different color
            screen.attroff(curses.color_pair(color_num))

        screen.refresh()

    def draw_buttons(self):
        """Function draw buttons on :self.stdscr:."""
        # add buttons
        for button in self.buttons:
            button.print_on(self.stdscr)
        # update screen
        self.stdscr.refresh()

    def draw_tables(self):
        """Method show id and text tables."""
        self.right_window.refresh()
        self.left_window.refresh()

    def read_logs(self, id_=None):
        """Method read logs and give messages sorted by date, by id and mail."""
        grep, file = self.__grep, self.__sys_path_to_log
        # for windows grep
        if file.endswith("$#universal_grep_path"):
            file = open(self.path_to_log)

        # if only by one id
        if id_:
            text = grep(file, [id_], as_list=True)
        else:
            all_ids = list(
                set(re.findall(r": (\w+):", grep(file, list(self.patterns_to_search_for.values()) + ['msgid=']))))
            if not all_ids:  # empty id list
                err_to_show = Warnings("No information was found.", (self.wind_height // 2, self.wind_width // 2),
                                       is_err=True)
                err_to_show.show(self.stdscr)
                self.left_table.draw_on_screen()
                self.right_table.draw_on_screen()
                return 1  # err sign

            text = grep(file, list(self.patterns_to_search_for.values()) + all_ids[:1], as_list=True)
            self.__num_of_ids = len(all_ids) - 1
            self.__active_id_num = 0

        # for windows grep
        if isinstance(file, TextIOWrapper):
            file.close()

        if not id_:
            self.left_table.refill_elements(all_ids)
            self.left_table.draw_on_screen()

        self.right_table.refill_elements(text)
        self.right_table.draw_on_screen()
        self.right_table.highlight(un_do=True)

        self.refresh_ids_ord_number()

    def run(self):
        """Blocking method, handle program in working state."""
        try:
            # init starting program settings
            self.make_frame()
            self.draw_buttons()
            self.change_log_loc(by_def=True)
            self.change_date_to_search(by_def=True)
            self.change_email(possible_to_cancel=False)

            # update screen
            self.draw_tables()
            # main loop
            while True:
                ch = self.stdscr.getch()
                for button in self.buttons:

                    if button.is_pressed(character_pressed=ch):
                        button.act()

                if ch == curses.ascii.ESC:
                    self.shut_down(with_confirm=True)

                if ch == curses.KEY_RESIZE:
                    self.resize_terminal()

                if ch == curses.KEY_UP:
                    not_moved = self.active_table.move_up()
                    if not not_moved:
                        self.__active_id_num += 1
                        button = self.active_table.active_element
                        if button:
                            button.act(button.text)

                if ch == curses.KEY_DOWN:
                    not_moved = self.active_table.move_down()
                    if not not_moved:
                        self.__active_id_num -= 1
                        button = self.active_table.active_element

                        if button:
                            button.act(button.text)

                if ch == 9:  # TAB
                    self.active_table.is_active = False

                    if self.active_table == self.left_table:
                        self.active_table = self.right_table
                        self.active_table.highlight()
                    else:
                        self.active_table.highlight(un_do=True)
                        self.active_table = self.left_table

                    self.active_table.is_active = True

        except (KeyboardInterrupt,):
            self.shut_down(1)


def main():
    program = CliGraphInterface()
    program.run()


if __name__ == '__main__':
    main()
