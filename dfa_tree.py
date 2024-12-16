import graphviz
import pandas as pd
import matplotlib.pyplot as plt

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
    def numbering_nodes(root, last_num):
        if root.left and root.right:
            last_num = Node.numbering_nodes(root.right, last_num)
            return Node.numbering_nodes(root.left, last_num) 
        if root.left:
            return Node.numbering_nodes(root.left, last_num)

        root.firstpos = {last_num}
        root.lastpos = {last_num}
        return last_num - 1

    def __repr__(self) -> str:
        return str({
            'value': self.value,
            'nullable': self.nullable,
            'firstpos': self.firstpos,
            'lastpos': self.lastpos,
            'left': self.left,
            'right': self.right,
        })

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


def followpos(node, followpos_table):
    if node.value == '.':
        for i in node.left.lastpos:
            followpos_table[i].update(node.right.firstpos)
    elif node.value in '*+':
        for i in node.lastpos:
            followpos_table[i].update(node.firstpos)

def build_syntax_tree(regex):
    regex = parse_ending(regex)
    regex = parse_concats(regex)
    regex = decompose_plus(regex)
    _last_num = last_num(regex)
    root = parse_regex(regex)
    Node.numbering_nodes(root, _last_num)
    root.compute_nullable_firstpos_lastpos()
    return root

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

def visualize_dfa(dfa):
    dot = graphviz.Digraph()
    for state in dfa:
        dot.node(state)
        for symbol, next_state in dfa[state].items():
            dot.edge(state, next_state, label=symbol)
    dot.render('dfa', format='png')

def plot_graphs_and_tables(dfa):
    df = pd.DataFrame(dfa).fillna('')
    print(df)
    df.plot(kind='bar')
    plt.show()

# Example usage
# regex = 'ab'
# regex = 'a*b'
# regex = 'a*b*'
# regex = 'a|b|c'
# regex = 'a|b+'
# regex = 'ab|c+|(ab|cd)+'
regex = 'a*((b)+|a)+'
# regex = 'a*((bc)+|(c|d)*|aa)+'
syntax_tree = build_syntax_tree(regex)
print(syntax_tree)
exit()
followpos_table = build_followpos_table(syntax_tree)
nfa = {}  # Convert syntax tree to NFA
dfa = nfa_to_dfa(nfa)
visualize_dfa(dfa)
plot_graphs_and_tables(dfa)


# To calculate FollowPos, you need to traverse the syntax tree and apply the following rules:

# Concatenation (A B): If a position i is in LastPos(A), then all positions in FirstPos(B) are in FollowPos(i).

# Kleene Star (A)*: If a position i is in LastPos(A), then all positions in FirstPos(A) are in FollowPos(i).