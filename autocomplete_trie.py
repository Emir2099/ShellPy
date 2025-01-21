import queue

class TrieNode:
    def __init__(self, letter, word, is_word=False):
        self.word = word
        self.is_word = is_word
        self.letter = letter
        self.next_nodes = {}

def compile_trie(commands):
    start_trie = TrieNode("", "")
    for command in commands:
        curr_trie_node = start_trie
        for ch in command:
            if ch in curr_trie_node.next_nodes:
                curr_trie_node = curr_trie_node.next_nodes[ch]
            else:
                next_trie_node = TrieNode(ch, curr_trie_node.word + ch)
                curr_trie_node.next_nodes[ch] = next_trie_node
                curr_trie_node = next_trie_node
        curr_trie_node.is_word = True
    return start_trie

class Suffix:
    def __init__(self, suffix, has_words):
        self.word = suffix
        self.has_words = has_words

def autocomplete(prefix, trie_node):
    prefix = "".join([ch for ch in prefix if ord(ch) > 33])
    curr_trienode = trie_node
    for ch in prefix:
        if ch in curr_trienode.next_nodes:
            curr_trienode = curr_trienode.next_nodes[ch]
        else:
            return []
    q = queue.Queue()
    q.put(curr_trienode)
    nodes = []
    while q.qsize() > 0:
        curr_node = q.get()
        if curr_node.is_word:
            nodes.append(curr_node)
        for k, val in curr_node.next_nodes.items():
            q.put(val)
    return [
        Suffix(node.word[len(prefix):], len(node.next_nodes) > 0) for node in nodes
    ]

def longest_common_prefix(strings):
    if not strings:
        return ""
    min_len = min(len(s) for s in strings)
    for i in range(min_len):
        char_set = set(s[i] for s in strings)
        if len(char_set) > 1:
            return strings[0][:i]
    return strings[0][:min_len]