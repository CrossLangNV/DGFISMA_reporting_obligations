#helper functions
import inspect
from keywords_nouns_verbs import ALL_ARG2_KEYWORDS


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
        arg.setAttribute('data-update-stack', last_frame_str)
        #print(">"+last_frame_str)

def text_of(element):
    return str(element.firstChild.data)


#some testing

from bs4 import BeautifulSoup, Comment, Doctype
import re

def clean_html(  html_file  ):
    
    '''
    Function will find all text in the html, convert to a plain text (String), and add it to a List
    
    :param html_file: String containing a html file in plain text.
    :return: List of Strings (sentences). 
    '''
    
    page_content=BeautifulSoup( html_file, "html.parser")
    
    
    #articles=[]
    #article=[]
    
    sentences=[]
    
    
    #remove the header:
    [x.extract() for x in page_content.findAll('head')]

    #remove the items of Doctype type:
    for item in page_content:
        if isinstance(item, Doctype):
            item.extract()

    #remove the comments
    com = page_content.findAll(text=lambda text:isinstance(text, Comment))
    [comment.extract() for comment in com]

    for node in page_content.findAll('p'):
        text = ''.join(node.findAll(text=True)) 
        text = text.strip() 
        text= text.replace( "\n", "" )
        text= text.replace( "\xa0" , " ")
               
        if text:  
            sentences.append( text )  
             
    return sentences