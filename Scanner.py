import sys
import re
import dominate
from dominate.tags import *
from typing import Union, Callable, Tuple, Optional

from exceptions import ScannerInitException, ScannerTokenException

source_address = 'src.txt'
literal_source_address = 'literal_source.txt'
keyword_table_address = 'keyword_table.txt'
symbol_source_address = 'symbol_file.txt'
color_table_address = 'color_table.txt'
style_table_address = 'style_table.txt'
delimiter = '---'

# TODO cant detect -- or - because of the delimiter
# TODO have to color the '"' in the strings manually
# TODO no scientific notation html
# Token Numbers here start at 500
DECIMAL_NUMBER = 500
HEXADECIMAL_NUMBER = 501
DOUBLE_NUMBER = 505
SCIENTIFIC_NOTATION = 503
LONG_INTEGER = 504
FLOAT_NUMBER = 502
ID_NUMBER = 507
ONE_LINE_COMMENT_TOKEN = 506
MULTI_LINE_COMMENT_TOKEN = 508


class Token:
    def __init__(self, symbol, scanner_num, mem_address=None):
        self.symbol = symbol
        self.scanner_num = scanner_num
        self.mem_address = mem_address


class Scanner:

    def __init__(self):
        self.source_text = None
        self._errors = {}
        self.cursor = 0
        self.character = None
        self.literal_switcher = self.read_switch(literal_source_address)
        self.symbol_switcher = self.read_switch(symbol_source_address)
        self.keyword_table = self.read_switch(keyword_table_address)
        self.color_table = self.read_switch(color_table_address)
        self.style_table = self.read_switch(style_table_address)
        self.read_source()
        self.get_ch()
        self.dom = dominate.document(title="Colored Code")
        self.p = p()
        self.paragraph_list = []

    def read_switch(self, address) -> dict:
        result = {}
        with open(address, 'r') as literal_source:
            lines = literal_source.readlines()
            for line in lines:
                parts = line.split(delimiter)
                result[parts[0]] = parts[1].strip()
        return result

    def get_token_func(self, k, switcher) -> Union[None, Callable]:
        # if self.character == '/':
        #     self.get_ch()
        #     if self.character == '/':
        #         k = '//'
        #     elif self.character == '*':
        #         k = '/*'
        #     else:
        #         self._errors.update({'token function error': 'no pattern with format /[number][letter] exists'})
        #         raise ScannerTokenException(self._errors)
        # TODO check this later ( if error can be issued in the symbol checking part
        for key in switcher.keys():
            if re.match(key, k):
                try:
                    return getattr(self, 'get_' + switcher[key] + '_token')
                except AttributeError:
                    self._errors.update({
                        'token function attribute error':
                            'function or symbol with token name "{}" doesnt exist'.format(switcher[key])})
                    raise ScannerTokenException(self._errors)
        self._errors.update({'token function error': 'no token or symbol starting with {} exists'.format(k)})
        raise ScannerTokenException(self._errors)

    def check_for_scientific(self, number) -> Tuple[bool, int]:
        if self.character == 'e':
            self.get_ch()
            if self.character == '+' or self.character == '-':
                if self.character == '+':
                    plus = True
                else:
                    plus = False
                self.get_ch()
                power = 0
                while re.match('[0-9]', self.character):
                    power = 10 * power + int(self.character)
                    self.get_ch()
                if not plus:
                    power = -power
                number = number * pow(10, power)
                return True, number
        else:
            return False, 0

    def add_html_text(self, content, keyword):
        content = str(content)
        color = self.color_table.get(keyword)
        text_style = self.style_table.get(keyword, None)
        if text_style is None:
            self.p.add_raw_string('<font color="{}">{}</font>'.format(color, content))
        else:
            self.p.add_raw_string('<{}><font color="{}">{}</font></{}>'.format(text_style, color, content, text_style))

    def get_number_token(self, *args):
        self.character = args[0]
        number = 0
        while re.match('[0-9]', self.character):
            number = number * 10 + int(self.character)
            self.get_ch()
        if re.match('\.', self.character):
            # real number
            self.get_ch()
            if not re.match('[0-9]', self.character):
                self._errors.update({
                    'token function error': {'character after dot in a number not allowed.'
                                             '\npattern: {}'.format(str(number) + '.' + self.character)}})
                raise ScannerTokenException(self._errors)
            counter = 1
            while re.match('[0-9]', self.character):
                number += int(self.character) * pow(10, -counter)
                self.get_ch()
                counter += 1
            if self.character == 'F':
                # float number
                self.get_ch()
                self.add_html_text(str(number) + "F", "Real")
                return FLOAT_NUMBER, number
            # i.e 5e+2 or 5e-2
            is_scientific, scientific_number = self.check_for_scientific(number)
            if is_scientific:
                number = scientific_number
                return SCIENTIFIC_NOTATION, number
            self.add_html_text(number, "Real")
            return DOUBLE_NUMBER, number
        else:
            if self.character == 'L':
                # long integer
                self.get_ch()
                self.add_html_text(str(number), "Integer")
                return LONG_INTEGER, number
            elif self.character == 'x':
                if number == 0:
                    # hexadecimal number
                    self.get_ch()
                    counter = 0
                    hex_string = ""
                    while re.match('[0-9]', self.character) or re.match('[ABCDEF]', self.character):
                        hex_string += self.character
                        self.get_ch()
                        counter += 1
                    number = int(hex_string, 16)
                    self.add_html_text("0x" + hex_string, "Other")
                    return HEXADECIMAL_NUMBER, number
                else:
                    # wrong format i.e 0298x..
                    self._errors.update({
                        'token function error': 'the given pattern is wrong : {}x\n try 0x[number]'.format(number)})
                    raise ScannerTokenException(self._errors)
            else:
                # decimal integer
                # i.e 55e-2
                is_scientific, scientific_number = self.check_for_scientific(number)
                if is_scientific:
                    number = scientific_number
                    return SCIENTIFIC_NOTATION, number
                self.add_html_text(str(number), "Integer")
                return DECIMAL_NUMBER, number

    def get_id_token(self, *args):
        id_string = "" + args[0]
        self.get_ch()
        while re.match('[0-9]', self.character) or re.match('[a-zA-z]', self.character):
            id_string += self.character
            self.get_ch()
        token = self.find_keyword(id_string)
        if token == ID_NUMBER:
            self.add_html_text(id_string, "Identifiers")
        else:
            self.add_html_text(id_string, "Reserved Key Words")
        return token, id_string

    def get_one_line_comment_token(self, *args):
        self.get_ch()
        comment_string = ""
        while self.character != '\n':
            comment_string += self.character
            self.get_ch()
        self.get_ch()
        self.add_html_text("// " + comment_string, "Comments")
        self.paragraph_list.append(self.p)
        self.p = p()
        return ONE_LINE_COMMENT_TOKEN, comment_string

    def get_multi_line_comment_token(self, *args):
        self.get_ch()
        comment_string = ""
        while True:
            comment_string += self.character
            self.get_ch()
            if self.character == '*':
                self.get_ch()
                if self.character == '/':
                    # end of comment
                    break
                else:
                    continue
        self.get_ch()
        self.add_html_text("/*", "Other")
        self.add_html_text(comment_string, "Comments")
        self.add_html_text("*/", "Other")
        return MULTI_LINE_COMMENT_TOKEN, comment_string

    def get_string_token(self, *args):
        string_data = ""
        self.get_ch()
        self.add_html_text('"', "Other")
        while self.character != '"':
            if self.character == '\\':
                self.get_ch()
                self.add_html_text(string_data, "Strings")
                self.add_html_text("\\" + self.character, "Special")
                string_data = ""
                self.get_ch()
                continue
            string_data += self.character
            self.get_ch()
        self.get_ch()
        self.add_html_text(string_data, "Strings")
        self.add_html_text('"', "Other")
        return self.find_keyword("string"), string_data

    def read_source(self) -> bool:
        try:
            with open(source_address, 'r') as source_file:
                self.source_text = source_file.read()
        except FileNotFoundError:
            self._errors.update({'source_read_error': sys.exc_info()})
            raise ScannerInitException(self._errors)
        return True

    def check_two_char_symbols(self, first_char, second_char):
        if self.character == first_char:
            self.get_ch()
            if self.character == second_char:
                self.character = (first_char + second_char)
            else:
                self.character = first_char
                self.cursor -= 1

    def check_symbol_file(self) -> Tuple[Union[None, int], Optional[str]]:
        self.check_two_char_symbols('=', '=')
        self.check_two_char_symbols('!', '=')
        self.check_two_char_symbols('<', '=')
        self.check_two_char_symbols('>', '=')
        self.check_two_char_symbols('>', '=')
        self.check_two_char_symbols('+', '+')
        self.check_two_char_symbols('+', '=')
        self.check_two_char_symbols('-', '=')
        self.check_two_char_symbols('/', '=')
        self.check_two_char_symbols('/', '*')
        self.check_two_char_symbols('/', '/')
        for key in self.symbol_switcher.keys():
            if key == self.character:
                original_char = self.character
                self.get_ch()
                return self.symbol_switcher[key], original_char
        return None, ""

    def get_next_token(self):
        while self.character in [' ', '\n']:
            if self.character == ' ':
                self.p.add_raw_string(self.character)
            if self.character == '\n':
                self.paragraph_list.append(self.p)
                self.p = p()
            self.get_ch()
        symbol_token, original_char = self.check_symbol_file()
        if symbol_token is not None:
            self.add_html_text(original_char, "Other")
            return Token(scanner_num=symbol_token, symbol=original_char)
        literal_token, value = self.get_token_func(self.character, self.literal_switcher)(self.character)
        return Token(scanner_num=literal_token, symbol=value)

    def get_ch(self) -> None:
        if self.cursor >= len(self.source_text):
            return
        self.character = self.source_text[self.cursor]
        self.cursor += 1

    def find_keyword(self, id_string):
        return self.keyword_table.get(id_string, ID_NUMBER)

    def tokenize(self):
        counter = 0
        while self.cursor < len(self.source_text):
            # print("info : source - " + str(len(self.source_text)) + "  cursor: " + str(self.cursor) + "  char : " +
            #       self.source_text[self.cursor])
            # print(self.get_next_token())
            counter += 1
        # print("token count: " + str(counter))
        with open('result.html', 'w') as result:
            with self.dom:
                with div(id='main') as div_main:
                    # add last paragraph
                    self.paragraph_list.append(self.p)
                    for paragraph in self.paragraph_list:
                        div_main.add(paragraph)
                result.write(str(html(body(div_main))))