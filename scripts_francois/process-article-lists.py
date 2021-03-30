import spacy
import sys
import re

from spacy.lang.en import English # updated

sentencizer = English()
sentencizer.add_pipe(sentencizer.create_pipe('sentencizer'))

section_regexp = r'^(Part|Title|Chapter|Section|Sub-Section|Article) ([0-9.]|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY|I|II|III|IV|V|VI|VII|VIII|IX|X|X(I|II|III|IV|V|VI|VII|VIII|IX|X))+ *$'

#INPUT:
#input_sentences = open('./process-article-lists.py.input.txt')

if len(sys.argv) > 1 and len(sys.argv[1])>=1:
    input_sentences = open(sys.argv[1])

#outfile_path = "./celex-articles.txt"
#
#if len(sys.argv) > 2 and len(sys.argv[2])>=1:
#    outfile_path = sys.argv[2]
#
#outfile = open(outfile_path, 'w+')

class seekable_iterator:
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

def peek(seekable_iterator):
    return_value = seekable_iterator.next()
    seekable_iterator.rewind()
    return return_value

def do_nothing():
    return

def level0_list():
    for i in range(1,2048):
        yield '('+str(i)+') '

def level1_list():
    for i in range(ord('a'), ord('z')+1):
        yield '('+chr(i)+') '

def level2_list():
    for i in ['i','ii','iii','iv','v','vi','vii','viii','ix','x']:
        yield '('+str(i)+') '
    for i in ['i','ii','iii','iv','v','vi','vii','viii','ix','x']:
        yield '(x'+str(i)+') '
    for i in ['i','ii','iii','iv','v','vi','vii','viii','ix','x']:
        yield '(xx'+str(i)+') '

def level3_list():
    for _ in range(0,2048): yield '— '

def dash_list():
    for _ in range(0,2048): yield '- '

def bullet_list():
    for _ in range(0,2048): yield '• '

def infer_list_bullet_iterator(line):
    line = line.strip()
    if line[0:4] == '(1) ': 
        return list(level0_list())
    if line[0:4] == '(a) ': 
        return list(level1_list())
    if line[0:4] == '(i) ': 
        return list(level2_list())
    if line[0:2] == '— ': 
        return list(level3_list())
    if line[0:2] == '- ': 
        return list(dash_list())
    if line[0:2] == '• ':
        return list(bullet_list())
    return None

def looks_like_list_start(other_line):
    return (False
        or other_line[0:1] == '('
        or other_line[0:2] == '- '
        or other_line[0:2] == '— '
        or other_line[0:2] == '• '
    )

def looks_like_new_section(other_line):
    return (False
        or re.match(section_regexp, other_line, re.IGNORECASE)
        or re.match(r'^[0-9]+[.] ', other_line)
    )

def print_break_long_paragraphs(text):
    if len(text) > 1000:
        text = re.sub(r'([^❮❬‖❭❯]{1000}(?:[^❮❬‖❭❯.]|[.][^❮❬‖❭❯ ])*[.]) (?=[A-Z])', r'\1\n', text, re.MULTILINE + re.UNICODE)
    print(text)

def collect_sub_lines(input_sentences, separator, open_paren='❬', close_paren='❭'):
    other_lines = []
    other_lines_bullets = None
    for other_line in input_sentences:
        # don't accept to start a list without end-separator nor guessable bullet type
        if (True
            and separator == None # if we have a separator, we don't need this
            and not(looks_like_list_start(other_line))
        ):
            input_sentences.rewind()
            break
        else:
            # collect the bullet type
            if other_lines_bullets == None:
                other_lines_bullets = infer_list_bullet_iterator(other_line)
            
            # handle the special case where there is no bullet list type
            # (in that case, we stop on new article or sub-article)
            if (True
                and other_lines_bullets == None
                and looks_like_new_section(other_line)
            ):
                input_sentences.rewind()
                break
            
            # if we find the next item of the parent list, yield to the parent list
            if (True
                and separator != None
                and other_line[0:len(separator)] == separator
            ):
                input_sentences.rewind()
                break
            
            # if we don't find the expected bullet type, yield to the parent list
            expected_bullet = ''
            if other_lines_bullets != None: 
                expected_bullet = other_lines_bullets[len(other_lines)]
            if other_line[0:len(expected_bullet)] != expected_bullet:
                # exception: we have a separator, and we don't think we should split now
                if separator != None and not(looks_like_list_start(other_line)) and not(looks_like_new_section(other_line)):
                    do_nothing()
                else:
                    input_sentences.rewind()
                    break
            
            # clean other_line if possible
            other_line = re.sub(r'^( *\(([0-9]+|[a-z]|x?v?[i]+v?x?|xv?|v)\)|-|—|•) ',r'',other_line)
            other_line = re.sub(r'[;.,] *(or|and)? *$',r'',other_line)

            # handle sublists
            if re.search(r'[:]\s*$',other_line):
                # remove the double-point from the end of th line
                other_line = re.sub(r'\s*[:]\s*$', ' ', other_line)

                # determine what we expect the next line in the list to start with
                sub_separator = None
                if other_lines_bullets != None and len(other_lines_bullets) > len(other_lines):
                    sub_separator = other_lines_bullets[len(other_lines)+1]
                # fold all lines of the sublist into this one
                other_line = (''
                    + other_line + open_paren
                    + ' ‖ and/or '.join(collect_sub_lines(input_sentences,sub_separator,'⟨','⟩'))
                    + close_paren
                )
            # append the sentence to the list
            other_lines.append(other_line.strip())
    return other_lines

def handle_root_list(main_sentences, last_sentence, other_lines):

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
    elif re.search(r'^ *(For|When|Where)[^,]+$', last_sentence):
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
                    return handle_root_list([], sentence, sentence_other.split(' ‖ and/or '))
                else:
                    return sentence
            else:
                return sentence
        main_sentences = list(map(convert_to_strong_list_if_possible, main_sentences))

    return sentence_spacer.join(main_sentences)

# print all the input lines, after merging lists ":"
input_sentences = seekable_iterator(iter(input_sentences))
for main_line in input_sentences:
    main_line = main_line.rstrip("\n")
    try:
        if re.search(r'[:]\s*$',main_line):
            main_sentences = list(map(lambda s: re.sub(r'[)](?![ ,;:.?! ()])(?!th)', r') ',s.text.rstrip()), sentencizer(main_line).sents))
            last_sentence = main_sentences.pop()
            last_sentence = re.sub(r'\s*[:]\s*$', ' ', last_sentence)

            # gather the other lines
            other_lines = collect_sub_lines(input_sentences, separator=None)

            # only continue if there is an actual list
            if len(other_lines) == 0:
                print_break_long_paragraphs(main_line)
                continue

            # handle the merging of the list in the sentences
            content_to_print = handle_root_list(main_sentences, last_sentence, other_lines)

            print_break_long_paragraphs(content_to_print)
        
        #if no double-point in the sentence...
        elif re.match(section_regexp, main_line, re.IGNORECASE):
            next_line = input_sentences.next()
            if re.match(r'^[0-9]+[.] ', next_line):
                input_sentences.rewind()
            else:
                print_break_long_paragraphs(main_line + ' : ' + next_line.rstrip('\r\n'))
        else: #if no double-point in the sentence, nor other special rule
            print_break_long_paragraphs(main_line)
    except KeyboardInterrupt:
        raise
    except:
        print("Error in line: " + main_line, file=sys.stderr)
