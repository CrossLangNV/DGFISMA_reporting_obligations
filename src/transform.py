from typing import Generator, Tuple, Set
import string
import re

from cassis import Cas

from spacy.lang.en import English 
from src.utils import SeekableIterator

class ListTransformer():
    
    def __init__( self, cas: Cas ):
        
        '''
        Add a list view to the cas.
        :param cas: Cas. Cas object (mutable object).
        '''
        self.cas=cas
        
    def add_list_view( self , OldSofaID: str, NewSofaID: str='ListView', \
                                      value_between_tagtype: str="com.crosslang.uimahtmltotext.uima.type.ValueBetweenTagType", \
                                      paragraph_type: str= "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Paragraph" ):
        
        '''
        The method will get all value_between_tagtype (text in between tags), detect all lists (enumeration),
        and use a set of hand-crafted rules (function handle_root_list called by function transform_lines) to transform these enumeration to 
        sentences using the function transform_lines.
        The transformed sentences are then added to the cas.
        :param OldSofaID: String. Name of the old sofa.
        :param NewSofaID: String. Name of the new sofa.
        :param value_between_tagtype: String. 
        :param paragraph_type: String.
        :return: None. 
        '''
        
        value_between_tagtype_generator=self.cas.get_view( OldSofaID ).select( value_between_tagtype )        
        
        seek_vbtt=SeekableIterator( iter(value_between_tagtype_generator) )
        
        lines, offsets=get_other_lines( self.cas , OldSofaID, seek_vbtt, 'root', paragraph_type=paragraph_type )

        flatten_offsets( offsets )
        
        lines, offsets =postprocess_nested_lines( lines, offsets  )

        assert len( lines ) == len( offsets )

        transformed_lines, transformed_lines_offsets=transform_lines( lines, offsets )
        
        assert len( transformed_lines ) == len( transformed_lines_offsets )
        
        lines_offsets=[]
        for line, offset in zip( transformed_lines, transformed_lines_offsets  ):
            lines_offsets.append(line + "|" + str( offset ))

        #add the transformed lines to the cas
        
        self.cas.create_view(NewSofaID)
        
        self.cas.get_view( NewSofaID).sofa_string = "\n".join( lines_offsets )
        

def get_other_lines( cas: Cas, SofaID: str , value_between_tagtype_seekable_generator: Generator, root_paragraph:str='root', \
                    paragraph_type: str= "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Paragraph", end=-1,   ) -> Tuple[list,list]: 
    
    '''
    Convert cas with paragraph annotations to a nested lists to be used for annotation of reporting obligations.
    Structure of the nested lists is as follows:
    ->p   new_root (i.e. start of enumeration, e.g. "...shall be allocated as follows:"  )
    ->p
    ->p
    [->p  new_root
    [->p  new_root
    ->p]]
    :param cas: Cas.
    :param SofaID.
    :param value_between_tagtype_seekable_generator. SeekableIterator object.
    :param root_paragraph. The current paragraph.
    :param paragraph_type: String.
    :param end: Int. End index of the paragraph.
    :return: List, List. Lines and offsets.
    '''

    lines=[]
    offsets=[]
    paragraphs_covering_tag=None
    new_root_paragraph=None
    
    for tag in value_between_tagtype_seekable_generator:
        
        #check if tag is a "p", and if it was not part of one of the already nested p's.
        if not tag.tagName == 'p':
            continue
                
        #check if p-tag is deepest child (i.e. old eurlex have nested p's)
        if not deepest_child( cas, SofaID, tag ):
            continue
        
        #if tag.end>end==>then tag no longer part of paragraph
        if end >0 and tag.end > end:
            value_between_tagtype_seekable_generator.rewind()
            return lines, offsets
                    
        paragraphs_covering_tag= ['root'] + list(cas.get_view( SofaID ).select_covering( paragraph_type, tag ))
    
        #If no enumeration detected yet, set root_paragraph to 'root'.
        if root_paragraph=='root': 
            index_root=0
        else:
            index_root=get_index_typesystem_elements_in_list( paragraphs_covering_tag[1:], root_paragraph.xmiID )+1
        
        #sanity check
        assert index_root >= 0

        #Start of new sublist detected (i.e. the root_paragraph is no longer the "deepest" paragraph). Always go for the deepest root.
        if paragraphs_covering_tag[ index_root+1: ]:
            new_root_paragraph=paragraphs_covering_tag[ index_root+1 ]
            value_between_tagtype_seekable_generator.rewind()
            sublines, sublines_offsets =get_other_lines( cas, SofaID, value_between_tagtype_seekable_generator, new_root_paragraph, end=new_root_paragraph.end  )
            lines.append( sublines )
            offsets.append( sublines_offsets )
        else:
            lines.append(  tag.get_covered_text() )
            offsets.append( (tag.begin, tag.end) )
            
    return lines, offsets

#helper function
def get_index_typesystem_elements_in_list( list_typesystem_elements: list, xmiID: int  ) -> int:
    
    '''
    Helper function to get index of certain typesystem element (with given xmiID) in list of typesystem elements
    Necessary because list_typesystem_elements.index( element ) does not return correct index,
    because all elements in list_typesystem_elements are considered equal (due to bug in dkpro-cassis)
    '''
    
    for index, item in enumerate(  list_typesystem_elements ):
        if item.xmiID == xmiID:
            return index
        
    return -1


def transform_lines( lines: list, offsets: list  ) -> Tuple[list,list]:
    
    '''
    Function to transform the 'nested' lists produced by the function get_other_lines to merged sentences through folding of sublists (via function fold_sublist)
    and via hand crafted rules (via function handle_root_list)
    :param lines: list. List of str and lists.
    :param offsets: list. List of offsets in original document for each element in lines. 
    :return: List, List.
    '''

    sentencizer = English()
    sentencizer.add_pipe(sentencizer.create_pipe('sentencizer'))

    other_lines=[]
    merged_sentences=[]
    offsets_merged_sentences=[]

    assert len( lines ) == len( offsets )
    
    for line, offset in zip( lines, offsets ):

        main_line_other_line=()

        if type(line)==str:

            main_line_other_line=( line, None  )  #no other lines (i.e. no enumeration/detected lists)

        elif type(line)==list:

            #an enumeration should start with a string (i.e. type( line[0] )==str ), and should sum up at least one item (len( line )>1  ).  
            if not check_valid_list( line ):
                continue

            main_line=line[0]

            other_lines=[]
            for enumeration in line[1:]:
                if type(enumeration)==list:
                    other_lines.append(fold_sublist(enumeration))
                elif type(enumeration)==str:
                    enumeration=clean_line(enumeration).strip()
                    if enumeration:
                        other_lines.append( enumeration )

            main_line_other_line=( main_line, other_lines  )

        else:
            continue

        #handle root lists
        main_line =main_line_other_line[0].strip()
        if not main_line.strip():
            continue

        if not main_line_other_line[1]: #i.e. no enumeration
            #Maybe should also handle processing of sections
            broken_sentences=break_long_paragraphs( main_line )
            merged_sentences+=broken_sentences
            offsets_merged_sentences+=[offset]*len( broken_sentences )
            continue                                                                                         

        #Handle main lines (i.e. start of enumerations) that do not end with a punctuation. 
        if main_line.strip()[-1] not in string.punctuation:
            main_line=main_line+'.'

        main_sentences = list(map(lambda s: re.sub(r'[)](?![ ,;:.?! ()])(?!th)', r') ',s.text.rstrip()), sentencizer(main_line).sents))
        last_sentence = main_sentences.pop()
        last_sentence = re.sub(r'\s*[:]\s*$', ' ', last_sentence)
        last_sentence = re.sub(r'\s*[.]\s*$', '. ', last_sentence) 

        merged_sentence=handle_root_list( main_line , main_sentences, last_sentence, main_line_other_line[1])
        broken_sentences=break_long_paragraphs( merged_sentence )
        merged_sentences+=broken_sentences
        offsets_merged_sentences+=[offset]*len( broken_sentences )

    return merged_sentences, offsets_merged_sentences

#helper functions
def fold_sublist( sublist: list, open_paren='❬', close_paren='❭'  )-> str: 
    
    start_enumeration=''
    
    other_lines=[]
    
    for i,item in enumerate(sublist):
        
        if type(item)==str:
            item=clean_line(item).strip()
            if not item:
                continue
        
        if type(item)==str and i==0: #enumeration starts in next item
            
            start_enumeration = item
                        
        elif type(item)==str: #actual enumeration
            
            other_lines.append( item )
            
        elif type(item)==list:
            
            other_lines.append( fold_sublist(item, open_paren='⟨', close_paren='⟩'  ) )
                
    return (start_enumeration + ' '  + open_paren +  ' ‖ and/or '.join( other_lines ) + close_paren).strip()


def handle_root_list( main_line:str , main_sentences: list, last_sentence: str, other_lines: list) -> str:
        
    '''
    Hand crafted rules provided by François Remy ( Ugent, Imec) to transform enumerations for processing of reporting obligations.
    :param main_line: String. The current line.
    :param main_sentences: List. The main line split with spacy sentencizer.
    :param last_sentence: String. Processed last element of main_sentences.
    :param other_lines: List. The other lines (enumeration).
    :return: String. Transformed sentence using hand crafted rules.
    '''
        
    # default choice of action
    list_action = 'ADD_IN_SENTENCE'
    list_comma_handling = 'AUTO'

    # detect how to treat the list thanks to the last sentence
    if re.search(r' shall do the following $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
        last_sentence = re.sub(r' shall do the following $', r' shall ', last_sentence)
    if re.search(r' and do the following $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
        last_sentence = re.sub(r' and do the following $', r' and ', last_sentence)
    elif re.match(r'The following( definitions?|requirements)? shall apply ', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
        main_sentences.append(last_sentence+'.')
        last_sentence = ''
    elif re.search(r' the following( definitions?)? shall apply ', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'COMMA'
        last_sentence = re.sub(r' ?,? the following( definitions?)? shall apply $', r' ', last_sentence)
    elif re.search(r' the following requirements? shall apply ', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'COMMA'
        last_sentence = re.sub(r' ?,? the following( requirements?)? shall apply $', r' ', last_sentence)
    elif re.search(r' the following requirements ', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
        main_sentences.append(last_sentence+'.')
        last_sentence = ''
    elif re.search(r'\b[Tt]he( .*)? standards relating to .* are the following ', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
        main_sentences.append(last_sentence+'.')
        last_sentence = ''
    elif re.search(r' following ', last_sentence):
        list_action = 'KEEP_OUT'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r' as follows $', last_sentence):
        list_action = 'KEEP_OUT'
        list_comma_handling = 'NO_COMMA'
        last_sentence = re.sub(r' as follows $',r' as described in the following list ', last_sentence)
    elif re.search(r' provided $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r' (including|excluding|include|exclude|concerning) $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r' (shall|can|must|should)( not)? $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r' (that|which|who) $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r' (when|where|in the cases?)( it (has|does))? $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r' (of|on|by|for|from|to|using) $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r' (more|less) than $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r' (is|are|specify|specifies|comprise|comprises|mean|means) $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r' (report|disclose|collect|gather|store) $', last_sentence):
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'NO_COMMA'
    elif re.search(r'^ *(For\b|When|Where)[^,]+$', last_sentence): #word break added after For
        list_action = 'ADD_IN_SENTENCE'
        list_comma_handling = 'COMMA'
    elif re.search(r' points? \( ?(a|i) ?\)', main_line) and re.search(r' points? \( ?(a|i) ?\)', re.sub(r'(for the purposes? of( the)? points?|points? \([^)]+\)( (and|to) \([^)]+\))? ?of )', r'', re.sub(r' ?of this paragraph',r'',main_line, re.IGNORECASE), re.IGNORECASE)):
        list_action = 'KEEP_OUT'
        list_comma_handling = 'NO_COMMA'
        
    # detect whether to add a comma at the end of not
    if list_action == 'ADD_IN_SENTENCE' and list_comma_handling == 'AUTO':
        # TODO: list_comma_handling == AUTO
        list_comma_handling = 'NO_COMMA'

    # duplicate the last sentence as many times as required by the list
    sentence_spacer = " "
    if list_action == 'ADD_IN_SENTENCE':
        # output one per line if there's no shared context
        if len(main_sentences) == 0:
            sentence_spacer = '\n'
        elif len(main_sentences) == 1 and re.match('[0-9]+[.]', main_sentences[0]):
            sentence_spacer = '\n'
            last_sentence = main_sentences[0].rstrip() + ' ' + last_sentence
            main_sentences = []
        # also output one per line if we end up in a case where we wanted each list item to be its own sentence
        elif len(last_sentence) == 0: 
            main_sentences = [ ' '.join(map(lambda s: str(s).rstrip(), main_sentences)) ]
            sentence_spacer = '\n'
        # also output one per line if merging would result in a too long paragraph
        elif len(other_lines) > 9:
            sentence_spacer = '\n'
            last_sentence = ' '.join(map(lambda s: str(s).rstrip(), main_sentences)) + ' ' + last_sentence
            main_sentences = []
        # also output one per line if merging would result in a too long paragraph
        elif len(last_sentence) * len(other_lines) >= 200: 
            main_sentences = [ ' '.join(map(lambda s: str(s).rstrip(), main_sentences)) ]
            sentence_spacer = '\n'
        # deal with the comma, if necessary
        if list_comma_handling == 'COMMA':
            last_sentence = re.sub(r' *$', r', ', last_sentence)
        elif list_comma_handling != 'NO_COMMA':
            raise ValueError("Invalid list comma handling: " + str(list_comma_handling))
        # generate the filled-in sentences
        for other_line in other_lines:
            main_sentences.append(last_sentence + other_line + '.')
    elif list_action == 'KEEP_OUT':
        # append the options between brackets
        main_sentences.append(last_sentence.rstrip() + ' ❮' + ' ‖ '.join(other_lines) + '❯')
    else:
        raise ValueError("Invalid list action: " + str(list_action))

    if sentence_spacer == '\n':
        def convert_to_strong_list_if_possible(sentence):
            if '❬' in sentence:
                sentence_other = re.sub(r'(^[^❬]+|[^❭]+$)',r'',sentence)
                if len(sentence_other) > 0 and not ('❬' in sentence_other): 
                    sentence = sentence.replace(sentence_other, '', 1)
                    sentence = re.sub(r'\s*[:.;]\s*$', ' ', sentence)
                    sentence_other = sentence_other[1:len(sentence_other)-1]
                    return handle_root_list( main_line ,[], sentence, sentence_other.split(' ‖ and/or '))
                else:
                    return sentence
            else:
                return sentence
        main_sentences = list(map(convert_to_strong_list_if_possible, main_sentences))

    return sentence_spacer.join(main_sentences)

#helper functions:

def deepest_child( cas:Cas, SofaID:str , tag ,tagnames: Set[str] = set( 'p' ), \
                  value_between_tagtype: str="com.crosslang.uimahtmltotext.uima.type.ValueBetweenTagType"  ) -> bool:
    #helper function
    if len( [item for item in cas.get_view( SofaID ).select_covered(  value_between_tagtype , tag ) \
             if (item.tagName in tagnames and item.get_covered_text() ) ] ) > 1:
        return False
    else:
        return True
    
def check_valid_list(  line: list ) -> bool:
    
    if len( line )<=1:
        return False
    
    if type( line[0])!=str:
        return False
    
    return True

def clean_line(  line: str ) -> str:

    line = re.sub(r'^( *\(([0-9]+|[a-z]|x?v?[i]+v?x?|xv?|v)\)|-|—|•)',r'',line)
    #delete strings solely consisting of "1. " ==> can occur inside nested list, and mess up function handle_root_lists:
    line = re.sub(r'^( *([0-9]+[.])) *$',r'',line)  
    line = re.sub(r'[;.,] *(or|and)? *$',r'', line)
    line = re.sub(r'\s*[:]\s*$', ' ', line)
    
    return line

def break_long_paragraphs(text: str ) -> list:
    
    if len(text) > 1000:
        text = re.sub(r'([^❮❬‖❭❯]{1000}(?:[^❮❬‖❭❯.]|[.][^❮❬‖❭❯ ])*[.]) (?=[A-Z])', r'\1\n', text, re.MULTILINE + re.UNICODE)
    
    break_lines = [line.strip() for line in text.split( "\n" ) if line.strip()]

    return break_lines

def flatten(container:list):
    
    '''
    Helper function to flatten lists
    '''
    
    for i in container:
        if isinstance(i, (list)):
            for j in flatten(i):
                yield j
        else:
            yield i

def flatten_offsets(  offsets: list ):
    
    '''
    Helper function to flatten nested list of offsets
    '''
    
    for i,item in enumerate(offsets):
        if type(item)==list:
            flattened_list=list( flatten( item ) )
            if flattened_list:
                offsets[i]=( flattened_list[0][0], flattened_list[-1][-1] )
                
                
def postprocess_nested_lines( lines, offsets, cutoff:int = 50 ):
    
    '''
    Helper function to flatten long nested lists. Necessary for performance reasons.
    '''
    
    new_lines=[]
    new_offsets=[]

    for line, offset in zip( lines, offsets ):
        if type( line ) == list:
            if len( line )>cutoff:
                new_lines+=line
                new_offsets+=[offset]*len( line )
                continue
                
        new_lines.append( line )
        new_offsets.append( offset )
        
    return new_lines, new_offsets
