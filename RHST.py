import functools
import pandas as pd
import numpy as np

def calltracker(func):
    @functools.wraps(func)
    def wrapper(*args):
        wrapper.has_been_called = True
        return func(*args)

    wrapper.has_been_called = False
    return wrapper


NULL_VALUE = "#"
PREDICT_ADD_FOLLOW = 'PREDICT ADD FOLLOW'


class RHST:
    grammar_address = 'raw_grammar.txt'

    def __init__(self):
        self.prod_number = {}
        self.grammar_dict = self.read_raw_grammar()
        print("grammar : ", self.grammar_dict)
        self.nullable_dict = {}
        self.fill_nullable_dict()
        print("is_nullable : ", self.nullable_dict)
        self.first_dict = self.compute_first_dict()
        print("first : ", self.first_dict)
        self.follow_dict = self.compute_follow_dict()
        print("follow : ", self.follow_dict)
        self.predict_dict = self.compute_predict_dict()
        print("predict : ", self.predict_dict)
        self.parse_table = self.generate_parse_table()
        print("\n", self.parse_table)

    @calltracker
    def read_raw_grammar(self) -> dict:
        with open(self.grammar_address, 'r') as file:
            data = file.readlines()
        result = {}
        for index, line in enumerate(data):
            split = line.split(':')
            predicate = split[0].strip()
            subject = split[1].strip()
            if predicate not in self.prod_number.keys():
                self.prod_number.update({predicate: [[subject, index]]})
            else:
                self.prod_number[predicate].append([subject, index])
            if predicate not in result.keys():
                result[predicate] = [subject]
            else:
                result[predicate].append(subject)
        return result

    @calltracker
    def fill_nullable_dict(self) -> None:
        if not self.read_raw_grammar.has_been_called:
            raise Exception("you need to call read_grammar before this function")
        for k in self.grammar_dict.keys():
            self.nullable_dict[k] = self.is_nullable(self.grammar_dict[k], [k])

    def is_nullable(self, subject_list, predicate_list: list) -> bool:
        for subject in subject_list:
            parts = subject.split(" ")
            part_length = 0
            for part in parts:
                is_terminal = part[0].isupper()
                if is_terminal:
                    if part in predicate_list:
                        part_length += 1
                        continue
                    is_nullable = self.nullable_dict.get(part, None)
                    if is_nullable is None:
                        next_level_predicate_list = predicate_list.copy()
                        next_level_predicate_list.append(part)
                        is_nullable = self.is_nullable(self.grammar_dict[part], next_level_predicate_list)
                    if is_nullable:
                        self.nullable_dict[part] = True
                        part_length += 1
                else:
                    if part == NULL_VALUE:
                        part_length += 1
            if part_length == len(parts):
                return True
        return False

    @calltracker
    def compute_first_dict(self) -> dict:
        if not self.fill_nullable_dict.has_been_called:
            raise Exception("you need to call fill_nullable_dict before this function")
        result = {}
        for k in self.grammar_dict.keys():
            result[k] = self.first(self.grammar_dict[k], k)
        return result

    def first(self, subject_list, predicate) -> set:
        result = set([])
        for subject in subject_list:
            parts = subject.split(" ")
            for part in parts:
                if part == predicate:
                    continue
                is_terminal = part[0].isupper()
                if not is_terminal:
                    result.add(part)
                    break
                else:
                    is_nullable = self.nullable_dict[part]
                    if not is_nullable:
                        for item in self.first(self.grammar_dict[part], part):
                            result.add(item)
                        break
                    else:
                        for item in self.first(self.grammar_dict[part], part):
                            result.add(item)
        return result

    @calltracker
    def compute_follow_dict(self) -> dict:
        if not self.compute_first_dict.has_been_called:
            raise Exception("you need to call compute_first_dict before this function")
        result = {}
        for k in self.grammar_dict.keys():
            result[k] = self.follow(k)
        return result

    def follow(self, symbol) -> set:
        follow_symbols = []
        for k2 in self.grammar_dict.keys():
            for subject in self.grammar_dict[k2]:
                if symbol in subject.split(' '):
                    follow_symbols.append({k2: subject.split(symbol)[1].strip()})
        result = set([])
        for item in follow_symbols:
            for k, v in item.items():
                if k == symbol and v == '':
                    continue
                if v == '':
                    result.update(self.follow(k))
                terms = v.split(' ')
                for term in terms:
                    is_terminal = term.isupper()
                    if not is_terminal:
                        if term != '':
                            result.add(term)
                        break
                    else:
                        is_nullable = self.nullable_dict[term]
                        if not is_nullable:
                            result.update(self.first_dict[term])
                        else:
                            result.update(self.first_dict[term])
                            result.update(self.follow(term))
        if symbol == 'S':
            result.add('$')
        if '#' in result:
            result.remove('#')
        return result

    def compute_predict_dict(self):
        if not self.compute_follow_dict.has_been_called:
            raise Exception("you need to call compute_follow_dict before this function")
        result = {}
        for k in self.grammar_dict.keys():
            result[k] = self.predict(k)
        return result

    def get_prod_number(self, symbol, subject) -> int:
        prod_list = self.prod_number[symbol]
        for item in prod_list:
            if subject == item[0]:
                return item[1]

    def predict(self, symbol) -> list:
        predict_symbols = []
        for subject in self.grammar_dict[symbol]:
            symbol_list = []
            subject_symbols = subject.split(' ')
            first_symbol = subject_symbols[0]
            symbol_list.append(first_symbol)
            is_terminal = first_symbol.isupper()
            if is_terminal:
                if self.nullable_dict[first_symbol]:
                    index = 1
                    while index < len(subject_symbols):
                        current_symbol = subject_symbols[index]
                        if not current_symbol.isupper():
                            symbol_list.append(current_symbol)
                            break
                        else:
                            if not self.nullable_dict[current_symbol]:
                                symbol_list.append(subject_symbols[index])
                                break
                            else:
                                symbol_list.append(subject_symbols[index])
                                index += 1
                    if index == len(subject_symbols):
                        symbol_list.append(PREDICT_ADD_FOLLOW)
            predict_symbols.append([self.get_prod_number(symbol, subject), symbol_list])

        result = []
        for prod_pair in predict_symbols:
            symbol_list = prod_pair[1]
            for item in symbol_list:
                is_terminal = item[0].isupper()
                if is_terminal:
                    if item == PREDICT_ADD_FOLLOW:
                        result.append([prod_pair[0], self.follow_dict[symbol]])
                    else:
                        result.append([prod_pair[0], self.first_dict[item]])
                else:
                    if item == NULL_VALUE:
                        result.append([prod_pair[0], self.follow_dict[symbol]])
                    result.append([prod_pair[0], {item}])
        return result

    def get_parse_table_rows_and_columns(self):
        terminals = set()
        non_terminals = set()
        for k in self.grammar_dict.keys():
            terminals.add(k)
            for subject in self.grammar_dict[k]:
                for item in subject.split(' '):
                    if not item.isupper():
                        non_terminals.add(item)
        return terminals, non_terminals

    def generate_parse_table(self) -> pd.DataFrame:
        rows, columns = self.get_parse_table_rows_and_columns()
        df = pd.DataFrame(columns=columns, index=rows)
        for row_name in self.predict_dict.keys():
            for parse_list in self.predict_dict[row_name]:
                for column_name in parse_list[1]:
                    df[column_name][row_name] = parse_list[0]
        del df['#']
        df = df.replace(np.NAN, '-')
        return df


RHST()
