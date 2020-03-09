import string
import sys
import re
from typing import Union, Callable, Tuple

from exceptions import ScannerInitException, ScannerTokenException
source_address = 'src.txt'
literal_source_address = 'literal_source.txt'
keyword_table_address = 'keyword_table.txt'
symbol_source_address = 'symbol_file.txt'
delimiter = '---'


# TODO cant detect -- or - because of the delimiter
# TODO have to color the '"' in the strings manually
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


class Scanner:

    def __init__(self):
        self.source_text = None
        self._errors = {}
        self.cursor = 0
        self.character = None
        self.literal_switcher = self.read_switch(literal_source_address)
        self.symbol_switcher = self.read_switch(symbol_source_address)
        self.keyword_table = self.read_switch(keyword_table_address)
        self.read_source()
        self.get_ch()

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
                return FLOAT_NUMBER
            # i.e 5e+2 or 5e-2
            is_scientific, scientific_number = self.check_for_scientific(number)
            if is_scientific:
                number = scientific_number
                return SCIENTIFIC_NOTATION
            return DOUBLE_NUMBER
        else:
            if self.character == 'L':
                # long integer
                self.get_ch()
                return LONG_INTEGER
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
                    return HEXADECIMAL_NUMBER
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
                    return SCIENTIFIC_NOTATION
                return DECIMAL_NUMBER

    def get_id_token(self, *args):
        id_string = "" + args[0]
        self.get_ch()
        while re.match('[0-9]', self.character) or re.match('[a-zA-z]', self.character):
            id_string += self.character
            self.get_ch()
        return self.find_keyword(id_string)

    def get_one_line_comment_token(self, *args):
        self.get_ch()
        comment_string = ""
        while self.character != '\n':
            comment_string += self.character
            self.get_ch()
        self.get_ch()
        return ONE_LINE_COMMENT_TOKEN

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
        return MULTI_LINE_COMMENT_TOKEN

    def get_string_token(self, *args):
        string_data = ""
        self.get_ch()
        while self.character != '"':
            string_data += self.character
            self.get_ch()
        self.get_ch()
        return self.find_keyword("string")

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

    def check_symbol_file(self) -> Union[None, int]:
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
                self.get_ch()
                return self.symbol_switcher[key]
        return None

    def get_next_token(self):
        while self.character in [' ', '\n']:
            self.get_ch()
        symbol_token = self.check_symbol_file()
        if symbol_token is not None:
            return symbol_token
        literal_token = self.get_token_func(self.character, self.literal_switcher)(self.character)
        return literal_token

    def get_ch(self) -> str:
        if self.cursor >= len(self.source_text):
            return
        self.character = self.source_text[self.cursor]
        self.cursor += 1

    def find_keyword(self, id_string):
        return self.keyword_table.get(id_string, ID_NUMBER)

    def tokenize(self):
        while self.cursor < len(self.source_text):
            # print("info : source - " + str(len(self.source_text)) + "  cursor: " + str(self.cursor) + "  char : " +
            #       self.source_text[self.cursor])
            print(self.get_next_token())


scanner = Scanner()
scanner.tokenize()
