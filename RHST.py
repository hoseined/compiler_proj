import functools


def calltracker(func):
    @functools.wraps(func)
    def wrapper(*args):
        wrapper.has_been_called = True
        return func(*args)

    wrapper.has_been_called = False
    return wrapper


NULL_VALUE = "#"


class RHST:
    grammar_address = 'raw_grammar.txt'

    def __init__(self):
        self.grammar_dict = self.read_raw_grammar()
        print("grammar : ", self.grammar_dict)
        self.nullable_dict = {}
        self.fill_nullable_dict()
        print("is_nullable : ", self.nullable_dict)
        self.first_dict = self.compute_first_dict()
        print("first : ", self.first_dict)
        self.follow_dict = self.compute_follow_dict()
        print("follow : ", self.follow_dict)

    @calltracker
    def read_raw_grammar(self) -> dict:
        with open(self.grammar_address, 'r') as file:
            data = file.readlines()
        result = {}
        for line in data:
            split = line.split(':')
            predicate = split[0].strip()
            subject = split[1].strip()
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
                if symbol in subject:
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
                        result.add(term)
                        break
                    else:
                        is_nullable = self.nullable_dict[term]
                        if not is_nullable:
                            result.update(self.first_dict[term])
                        else:
                            result.update(self.follow(term))
        return result


RHST()

# A : A B
# B : C D
# C : #
# D : C mamad asghar
