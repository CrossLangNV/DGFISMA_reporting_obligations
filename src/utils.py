#helper class
class SeekableIterator:
    def __init__(self, iterator):
        self.iterator = iterator
        self.current = None
        self.reuse = False

    def __iter__(self):
        return self
    
    def __next__(self):
        return self.next()

    def next(self):
        if self.reuse:
            self.reuse = False
        else:
            self.current = None
            self.current = next(self.iterator)
        return self.current

    def rewind(self):
        self.reuse = True

#helper functions
import inspect
import re
from src.keywords_nouns_verbs import ALL_ARG2_KEYWORDS


def looks_like_arg0(text: str):
    return looks_like_arg2(text, False) or text.lower() in 'they|it'.split('|')    

def looks_like_arg2(text:str,allow_them=True):
    text_start = text[0:35]
    if re.search(r'(?<!of the )(?<!of an )(?<!of a )\b(' + ALL_ARG2_KEYWORDS + r')\b(?! ?\'s)', text_start, re.I):
        return True
    if re.match(r'^([^ ]+ |at least )?(to |for )?(us|him|her|the others?)\b', text_start, re.I):
        return True
    if allow_them and re.match(r'^([^ ]+ |at least )?(to |for )?(them)\b', text_start, re.I):
        return True
    return False
 
def match_class_in_list(span, list): 
    return span.getAttribute('class') in list

def match_class(span, reg): 
    return re.search(reg, span.getAttribute('class'))

def update_class(arg, new_class):
    arg_class = arg.getAttribute('class')
    if arg_class != new_class:
        #print(">"+new_class+":" + arg.toxml())
        arg.setAttribute('class', new_class)
        last_frame = inspect.getouterframes(inspect.currentframe())[1]
        last_frame_str = last_frame.filename + ':' + str(last_frame.lineno)
        #arg.setAttribute('data-update-stack', last_frame_str)
        #print(">"+last_frame_str)

def text_of(element):
    return str(element.firstChild.data)
