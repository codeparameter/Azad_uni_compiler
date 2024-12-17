import json
from graphviz import Digraph


def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError

def single_set(s):
    return next(iter(s))

def update_set_in_dict(_dict, key, value):
    if key in _dict:
        _dict[key].update(value)
    else:
        _dict[key] = value.copy()

class Node:
    def __init__(self, value):
        self.value = value
        self.nullable = False
        self.firstpos = set()
        self.lastpos = set()
        self.left = None
        self.right = None

    def compute_nullable_firstpos_lastpos(self):
        if self.value == '*':
            if not self.left.firstpos or not self.left.lastpos:
                self.left.compute_nullable_firstpos_lastpos()
                
            self.nullable = True
            self.firstpos = self.left.firstpos
            self.lastpos = self.left.lastpos

        elif self.value == '|':
            if not self.right.firstpos or not self.right.lastpos:
                self.right.compute_nullable_firstpos_lastpos()
            if not self.left.firstpos or not self.left.lastpos:
                self.left.compute_nullable_firstpos_lastpos()
            
            self.nullable = self.left.nullable or self.right.nullable
            self.firstpos = self.left.firstpos | self.right.firstpos
            self.lastpos = self.left.lastpos | self.right.lastpos

        elif self.value == '.':
            if not self.right.firstpos or not self.right.lastpos:
                self.right.compute_nullable_firstpos_lastpos()
            if not self.left.firstpos or not self.left.lastpos:
                self.left.compute_nullable_firstpos_lastpos()            
            
            self.nullable = self.left.nullable and self.right.nullable
            self.firstpos = self.left.firstpos if not self.left.nullable else self.left.firstpos | self.right.firstpos
            self.lastpos = self.right.lastpos if not self.right.nullable else self.left.lastpos | self.right.lastpos

    @staticmethod
    def numbering_nodes(root, last_num, locs=dict()):
        if root.left and root.right:
            last_num, locs = Node.numbering_nodes(root.right, last_num, locs)
            return Node.numbering_nodes(root.left, last_num, locs) 
        if root.left:
            return Node.numbering_nodes(root.left, last_num, locs)

        root.firstpos = {last_num}
        root.lastpos = {last_num}
        update_set_in_dict(locs, root.value, {last_num})
        return last_num - 1, locs

    def __str__(self) -> str:
        return f'{self.firstpos} {self.value} { "V" if self.nullable else "F"} {self.lastpos}'
        # return str({
        #     'value': self.value,
        #     'nullable': self.nullable,
        #     'firstpos': self.firstpos,
        #     'lastpos': self.lastpos,
        #     # 'left': self.left,
        #     # 'right': self.right,
        # })

class State:

    def __init__(self, name, value, _symbols, _start=False, _final=False) -> None:
        self.name = name
        self.value = value
        self.map = {s: None for s in _symbols}
        self.start = _start
        self.final = _final

    def __eq__(self, __o: object) -> bool:
        return self.value == __o.value

    def __ne__(self, __o: object) -> bool:
        return self.value != __o.value

    def to_dict(self):
        return {
            'name': self.name,
            'value': self.value,
            'start': self.start,
            'final': self.final,
            'map': {k: v.name if v else v for k, v in self.map.items()},
        }

    def __str__(self) -> str:
        return f'{"->" if self.start else ""}{"*" if self.final else ""}{self.name}'
        # return str(self.to_dict())

    @staticmethod
    def transition_table(states):
        return [state.to_dict() for state in states]

def symbols(regex):
    res = set()
    for char in regex:
        if char not in '()|.*+':
            res.add(char)
    return res

def parse_ending(regex):
    return regex.replace('#', '') + '#'

def parse_concats(regex):
    new_reg = ''
    last_ch = ''
    for char in regex:
        if last_ch and last_ch not in '(|.' and \
            char not in ')|.*+':
            new_reg += '.'
        new_reg += char
        last_ch = char
    return new_reg

def decompose_plus(regex):
    new_reg = ''
    cache = ''
    parenthesis_openings = []

    for i, char in enumerate(regex):

        if char == '(':
            parenthesis_openings.append(i)

        elif char == ')':
            assert parenthesis_openings, 'There is no opening for ")"'

            if len(parenthesis_openings) == 1:
                _from = parenthesis_openings[0]
                _to = i

                assert _from - _to < 1, "Parenthesis must include characters"
                cache = '(' + decompose_plus(regex[_from + 1:_to]) + ')'
                new_reg += cache

            parenthesis_openings.pop()

        elif not parenthesis_openings:
            if char == '+':
                new_reg += '.' + cache + '*'
            else:
                cache = char
                new_reg += cache

    assert not parenthesis_openings, "some parenthesis didn't close"
        
    return new_reg


def recursive_parse_reg(regex):

    # checking single char

    if len(regex) == 1:
        assert regex[0] not in '()*|.', f'There is no character to operate with {regex[0]}'
        return Node(regex[0])

    new_reg = regex[::-1]
    parenthesis_closings = []

    # checking OR (|)

    for idx, char in enumerate(new_reg):
        i = len(new_reg) - 1 - idx 

        if char == '|' and not parenthesis_closings:
            node = Node('|')
            assert i > 0 and idx > 0, 'There is no character to continue with'
            node.right = recursive_parse_reg(regex[i + 1:])
            node.left = recursive_parse_reg(regex[:i])
            return node

        elif char == ')':
            parenthesis_closings.append(i)
        elif char == '(':
            parenthesis_closings.pop()

    # checking one phrase *

    if len(regex) >= 2 and regex[-1] == '*':
        if len(regex) == 2:
            assert regex[0] not in '()*|.', 'Must use a char before *'
            node = Node(value='*')
            node.left = Node(regex[0])
            return node

        elif regex[-2] == ')':
            new_reg2 = new_reg[1:]
            one_phrase = False
            parenthesis_closings = []
            parenthesis_opening = 0

            for idx, char in enumerate(new_reg2):
                i = len(new_reg2) - 1 - idx 

                if char == ')':
                    parenthesis_closings.append(i)
                    if one_phrase:
                        one_phrase = False
                        break
                elif char == '(':
                    if len(parenthesis_closings) == 1:
                        one_phrase = True
                        parenthesis_opening += i
                    parenthesis_closings.pop()
                else:
                    if one_phrase:
                        one_phrase = False
                        break
            
            if one_phrase:
                node = Node(value='*')
                node.left = recursive_parse_reg(regex[parenthesis_opening + 1: -2])
                return node

    # checking one phrase parenthesis
    
    if len(regex) >= 3 and regex[0] == '(' and regex[-1] == ')':
        one_phrase = False
        parenthesis_opening = []

        for idx, char in enumerate(regex):

            if char == '(':
                parenthesis_opening.append(i)
                if one_phrase:
                    one_phrase = False
                    break
            elif char == ')':
                if len(parenthesis_opening) == 1:
                    one_phrase = True
                parenthesis_opening.pop()
            else:
                if one_phrase:
                    one_phrase = False
                    break
        
        if one_phrase:
            return recursive_parse_reg(regex[1: -1])

    # checking concatenate

    parenthesis_closings = []

    for idx, char in enumerate(new_reg):
        i = len(new_reg) - 1 - idx 

        if char == '.' and not parenthesis_closings:
            node = Node('.')
            assert i > 0 and idx > 0, 'There is no character to continue with'
            node.right = recursive_parse_reg(regex[i + 1:])
            node.left = recursive_parse_reg(regex[:i])
            return node

        elif char == ')':
            parenthesis_closings.append(i)
        elif char == '(':
            parenthesis_closings.pop()
    
    raise ValueError(f'regex "{regex}" did not match any pattern')


def last_num(regex):
    loc = 0
    for char in regex:
        if char not in '()*|.':
            loc += 1
    return loc


def parse_regex(regex):
    root = Node(regex[-2])
    root.right = Node(value=regex[-1])
    root.left = recursive_parse_reg(regex[:-2])
    return root

def build_syntax_tree(regex):
    regex = parse_ending(regex)
    regex = parse_concats(regex)
    regex = decompose_plus(regex)
    print(regex)
    _last_num = last_num(regex)
    root = parse_regex(regex)
    _, locs = Node.numbering_nodes(root, _last_num)
    root.compute_nullable_firstpos_lastpos()
    return root, locs

def followpos(node, followpos_table):
    if node.value == '.':
        for i in node.left.lastpos:
            update_set_in_dict(followpos_table, i, node.right.firstpos)
    elif node.value == '*':
        for i in node.lastpos:
            update_set_in_dict(followpos_table, i, node.firstpos)


def build_followpos_table(root):
    followpos_table = {node: set() for node in root.firstpos | root.lastpos}
    nodes = [root]
    while nodes:
        node = nodes.pop()
        if node.left:
            nodes.append(node.left)
        if node.right:
            nodes.append(node.right)
        followpos(node, followpos_table)
    return followpos_table


def plot_tree(node, graph=None):
    if graph is None:
        graph = Digraph()
        graph.node(str(node), str(node))
    
    if node.left:
        graph.node(str(node.left), str(node.left))
        graph.edge(str(node), str(node.left))
        plot_tree(node.left, graph)
    
    if node.right:
        graph.node(str(node.right), str(node.right))
        graph.edge(str(node), str(node.right))
        plot_tree(node.right, graph)

    return graph

def plot_dfa(states, graph=None):
    for state in states:
        if graph is None:
            graph = Digraph()
            graph.node(str(state), str(state))

        for symb, s in state.map.items():
            if s:
                graph.node(str(s), str(s))
                graph.edge(str(state), str(s), symb)

    return graph


def build_dfa(regex):
    _symbols = symbols(regex)
    root, locs = build_syntax_tree(regex)
    final_loc = single_set(root.lastpos)

    graph = plot_tree(root)
    graph.render('tree', format='png', view=True)

    followpos_table = build_followpos_table(root)

    print()
    print('FollowPos Table')
    print(json.dumps(followpos_table, indent=2, default=set_default))

    states = [State(name='S0', value=root.firstpos, 
                    _symbols=_symbols,
                    _start=True,
                    _final=final_loc in root.firstpos)]
    resolved_states = 0

    while resolved_states != len(states):
        state = states[resolved_states]
        for symbol in _symbols:
            new_set = set()
            for loc in locs[symbol]:
                if loc in state.value:
                    new_set.update(followpos_table[loc])

            if not new_set:
                continue

            new_state = State(name=f'S{len(states)}', 
                            value=new_set, 
                            _symbols=_symbols, 
                            _final=final_loc in new_set)
            old_state_i = 0
            should_append = True
            for i, s in enumerate(states):
                if new_state == s:
                    old_state_i += i
                    should_append = not should_append
                    break
            
            if should_append:
                states.append(new_state)
                state.map[symbol] = new_state
            else:
                state.map[symbol] = states[old_state_i]

        resolved_states += 1

    print()
    print('Transition Table')
    print(json.dumps(State.transition_table(states), indent=2, default=set_default))

    graph = plot_dfa(states)
    graph.render('dfa', format='png', view=True)

    return states

# Example usage
# regex = 'ab'
# regex = 'a*b'
# regex = 'a*b*'
# regex = 'a|b|c'
# regex = 'a|b+'
# regex = 'ab|c+|(ab|cd)+'
# regex = 'a*((b)+|a)+'
# regex = '(a*|b+)'
regex = 'a*((bc)+|(c|d)*|aa)+'

states = build_dfa(regex)