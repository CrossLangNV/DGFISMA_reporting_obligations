import os
import re
from typing import Tuple
from xml.dom.minidom import parseString
from allennlp.predictors.semantic_role_labeler import SemanticRoleLabelerPredictor

import spacy
from spacy.lang.en import English

from cassis import Cas

from src.keywords_nouns_verbs import ALL_ARG2_KEYWORDS, PLURAL_OR_NODET_ARG2_KEYWORDS, INTERESTING_VERBS, OBLIGATION_VERBS, INTERESTING_NOUNS, OBLIGATION_NOUNS, INTERESTING_NOUNS_VALID_VERBS_DIRECT, INTERESTING_NOUNS_VALID_VERBS_SUBJ, PENDING_LOCATION_TYPES

from src.utils import looks_like_arg0, looks_like_arg2, match_class_in_list, match_class , update_class, text_of

class ReportingObligationsFinder():
    
    def __init__( self, cas:Cas , bert_model: SemanticRoleLabelerPredictor , nlp: English  ):
        
        '''
        Find reporting obligations in text. See method process_sentences.
        :param sentences: List. List of Strings (i.e. sentences).
        :param bert_model: SemanticRoleLabelerPredictor. Bert based parser.
        :param nlp: Spacy model.
        '''
        
        self.cas=cas
            
        self.bert_model=bert_model
        self.nlp=nlp
        self.last_known_subject= ''
        #remember the current location ( i.e. part/annex/title/chapter/... )
        self.pending_location_names=list(map(lambda x: '', PENDING_LOCATION_TYPES))  
        
        
    def update_pending_location_names( self, input_sentence:str ):
        
        '''
        Given a sentence, the method updates self.pending_location_names (i.e. (part, annex), title, chapter, section, sub-section, article). If a new title, chapter,... is found, self.last_known_subject is reset.
        :param input_sentence: String.
        :return: None. 
        '''
               
        for i, loc_type_names in enumerate(PENDING_LOCATION_TYPES):
            for loc_type in loc_type_names:
                if str(input_sentence[0:len(loc_type)]).lower() == loc_type:
                    for j in range(i,len(self.pending_location_names)):
                        self.pending_location_names[j] = ''
                    self.pending_location_names[i] = input_sentence
                    self.last_known_subject='' # reset last known subject every article
     
    
    def get_and_flush_pending_location_names( self ):
        
        '''
        Method resets self.pending_location_names. Current locations (self.pending_location_names) are converted to an xml element and stored in a List. 
        :return: List.
        '''
        
        list_location_xml=[]
        
        for i, loc_name in enumerate(self.pending_location_names):
            if len(loc_name) > 0: 
                list_location_xml.append(  parseString( '<h' + str(i+1) + '>' + loc_name + '</h' + str(i+1) + '>' ) )      
            self.pending_location_names[i] = ''

        return list_location_xml
    
       
    def update_last_known_subject(self, input_sentence:str):
        
        '''
        Given a sentence, method updates self.last_known_subject using various regexes.
        :param input_sentence: String.
        :return: None.
        '''

        input_sentence = re.sub(r'^ *[0-9]*[.] *', r'', input_sentence)
        input_sentence = re.sub(r'^ *\([a-z0-9]*\) *', r'', input_sentence)
        # general "when" lookup
        subj_match = re.search(r'(?i:(?:when|where|if|as soon as))(?: ?[,][^,.]+[,])? ((an?|the|this|that|their|its|one|two|three|any( such( an?)?)?|such( an?)?|all|every|each) ([^ ]+)( ([^ ]+ )?(?i:' + ALL_ARG2_KEYWORDS + r'))?|([^ ]+ ){0,2}(?i:' + PLURAL_OR_NODET_ARG2_KEYWORDS + r')|[A-Z][A-Z]+|([A-Z][a-z]+ )+)', input_sentence)
        subj_match_str = str(subj_match.group(1)) if subj_match else ''
        when_clause_subject = re.sub(r'^(an?|the|this|that|their|its|one|any( such( an?)?)?|such( an?)?) (?![A-Z][A-Z])', 'this ', subj_match_str, re.I).strip()
        when_clause_subject = re.sub(r'^(an?|one|any( such( an?)?)?|such( an?)?) ', 'this ', when_clause_subject, re.I).strip()
        if when_clause_subject and looks_like_arg0(when_clause_subject): 
            self.last_known_subject = when_clause_subject

        if re.search(r'shall|may|must', input_sentence):
            # shall lookup
            subj_match = re.search(r'(?:^|(?=[A-Z])|, |‖ (?:and/or )?)((?i:(an?|the|this|that|their|its|one|two|three|any( such( an?)?)?|such( an?)?|all|every|each)) ([^ ]+)( ([^ ]+ )?(?i:' + ALL_ARG2_KEYWORDS + r'))?|([^ ]+ ){0,2}(?i:' + PLURAL_OR_NODET_ARG2_KEYWORDS + r')|[A-Z][A-Z]+|([A-Z][a-z]+ )+) (shall|may|must) ', input_sentence)
            subj_match_str = str(subj_match.group(1)) if subj_match else ''
            when_clause_subject = re.sub(r'^(an?|the|this|that|their|its|one|any( such( an?)?)?|such( an?)?) (?![A-Z][A-Z])', 'this ', subj_match_str, re.I).strip()
            when_clause_subject = re.sub(r'^(an?|one|any( such( an?)?)?|such( an?)?) ', 'this ', when_clause_subject, re.I).strip()
            if when_clause_subject and looks_like_arg0(when_clause_subject):
                self.last_known_subject = when_clause_subject
              
    def parse_sentence(  self, input_sentence:str ) -> dict:
        
        '''
        Given a sentence, method parses the sentences using AllenNLP parser (self.bert_model) 
        :param input_sentence: String.
        :return parsed_sentence: dict.
        '''
    
        parsed_sentence=self.bert_model.predict(
            sentence=input_sentence
        )
        
        return parsed_sentence
                
    @staticmethod
    def check_if_interesting_sentence_and_process_via_regexes( input_sentence:str ) -> str:
        
        '''
        Method checks if the input_sentence is a potential reporting obligation. If yes, the sentence is cleaned and returned, if no, it returns None.
        :param input_sentence: String.
        :return: String or None. 
        '''
        
        # detected definitions should be skipped... AD  (first do annotation of definition, next reporting obligation...)

        if '" means ' in input_sentence: return
        if '’ means ' in input_sentence: return

        input_sentence = re.sub(r'^ *[0-9]*[.] *', r'', input_sentence)
        input_sentence = re.sub(r'^ *\([a-z0-9]*\) *', r'', input_sentence)
        input_sentence = re.sub(r' (?:keep|maintain) ([^,]+) (?:informed of |posted on |updated on ) ', r' continuously inform \1 of ', input_sentence)
        input_sentence = re.sub(r' (?:keep|maintain) ([^,]+) (?:informed|posted|updated)\b ?', r' continuously inform \1 ', input_sentence)
        input_sentence = re.sub(r' (?:issue) ((?:a|the|its|their|this) certificate|(?:a|the|its|their|this) copy|(?:a|the|its|their|this) declaration|(?:a|the|its|their|this) directive|(?:a|the|its|their|this) draft|(?:a|the|its|their|this) final|(?:a|the|its|their|this) required|(?:a|the|its|their|this) memorendum|(?:a|the|its|their|this) contract|(?:a|the|its|their|this) new|(?:a|the|its|their|this) notice|(?:a|the|its|their|this) policy|(?:a|the|its|their|this) public statement|(?:a|the|its|their|this) report|(?:a|the|its|their|this) revised|(?:a|the|its|their|this) supplementary|(?:a|the|its|their|this) warning|(?:an|the|its|their|this) additional|(?:an|the|its|their|this) annual|(?:an|the|its|their|this) official|(?:an|the|its|their|this) order|(?:new |additional |supplementary|revised |official|draft |final |annual )?directives|(?:new |additional |supplementary|revised |official|draft |final |annual )?guidance|(?:new |additional |supplementary|revised |official|draft |final |annual )?guidelines|(?:new |additional |supplementary|revised |official|draft |final |annual )?recommendations|(?:new |additional |supplementary|revised |official|draft |final |annual )?regulation rules|(?:new |additional |supplementary|revised |official|draft |final |annual )?regulations|(?:new |additional |supplementary|revised |official|draft |final |annual )?regulatory guidelines|the following)\b ?', r' publish \1 ', input_sentence)
        input_sentence = re.sub(r' (?:issues) ((?:a|the|its|their|this) certificate|(?:a|the|its|their|this) copy|(?:a|the|its|their|this) declaration|(?:a|the|its|their|this) directive|(?:a|the|its|their|this) draft|(?:a|the|its|their|this) final|(?:a|the|its|their|this) required|(?:a|the|its|their|this) memorendum|(?:a|the|its|their|this) contract|(?:a|the|its|their|this) new|(?:a|the|its|their|this) notice|(?:a|the|its|their|this) policy|(?:a|the|its|their|this) public statement|(?:a|the|its|their|this) report|(?:a|the|its|their|this) revised|(?:a|the|its|their|this) supplementary|(?:a|the|its|their|this) warning|(?:an|the|its|their|this) additional|(?:an|the|its|their|this) annual|(?:an|the|its|their|this) official|(?:an|the|its|their|this) order|(?:new |additional |supplementary|revised |official|draft |final |annual )?directives|(?:new |additional |supplementary|revised |official|draft |final |annual )?guidance|(?:new |additional |supplementary|revised |official|draft |final |annual )?guidelines|(?:new |additional |supplementary|revised |official|draft |final |annual )?recommendations|(?:new |additional |supplementary|revised |official|draft |final |annual )?regulation rules|(?:new |additional |supplementary|revised |official|draft |final |annual )?regulations|(?:new |additional |supplementary|revised |official|draft |final |annual )?regulatory guidelines|the following)\b ?', r' publishes \1 ', input_sentence)
        input_sentence = re.sub(r' (?:issued) ((?:a|the|its|their|this) certificate|(?:a|the|its|their|this) copy|(?:a|the|its|their|this) declaration|(?:a|the|its|their|this) directive|(?:a|the|its|their|this) draft|(?:a|the|its|their|this) final|(?:a|the|its|their|this) required|(?:a|the|its|their|this) memorendum|(?:a|the|its|their|this) contract|(?:a|the|its|their|this) new|(?:a|the|its|their|this) notice|(?:a|the|its|their|this) policy|(?:a|the|its|their|this) public statement|(?:a|the|its|their|this) report|(?:a|the|its|their|this) revised|(?:a|the|its|their|this) supplementary|(?:a|the|its|their|this) warning|(?:an|the|its|their|this) additional|(?:an|the|its|their|this) annual|(?:an|the|its|their|this) official|(?:an|the|its|their|this) order|(?:new |additional |supplementary|revised |official|draft |final |annual )?directives|(?:new |additional |supplementary|revised |official|draft |final |annual )?guidance|(?:new |additional |supplementary|revised |official|draft |final |annual )?guidelines|(?:new |additional |supplementary|revised |official|draft |final |annual )?recommendations|(?:new |additional |supplementary|revised |official|draft |final |annual )?regulation rules|(?:new |additional |supplementary|revised |official|draft |final |annual )?regulations|(?:new |additional |supplementary|revised |official|draft |final |annual )?regulatory guidelines|the following)\b ?', r' published \1 ', input_sentence)

        # input_sentence = re.sub(r'(?<!(?: that | which | who | if it | if they )) (?:is|are) required to ', r' must ', input_sentence)
        input_sentence = re.sub(r' (?:is|are) required to ', r' must ', input_sentence)
        input_sentence = re.sub(r' shall be required to ', r' shall, as required, ', input_sentence)
        input_sentence = re.sub(r' and be required to ', r' and, as required, ', input_sentence)
        input_sentence = re.sub(r' (?:is|are) able to ', r' can ', input_sentence)
        input_sentence = re.sub(r' shall be able to ', r' shall, if needed, ', input_sentence)
        input_sentence = re.sub(r' and be able to ', r' and, if needed, ', input_sentence)
        input_sentence = re.sub(r' (?:is|are) responsible for ', r' monitor ', input_sentence)
        input_sentence = re.sub(r' shall be responsible for ', r' shall monitor ', input_sentence)
        input_sentence = re.sub(r' and be responsible for ', r' and monitor ', input_sentence)
        input_sentence = re.sub(r' subject to ', r' subjected to ', input_sentence)
        input_sentence = re.sub(r'\bThere shall be ', r'One shall implement ', input_sentence)
        input_sentence = re.sub(r'\bthere shall be ', r'one shall implement ', input_sentence)
        input_sentence = re.sub(r' have in place ', r' maintain ', input_sentence)
        input_sentence = re.sub(r' have( [^.;‖]{0,35})? in place ', r' maintain\1 ', input_sentence)
        input_sentence = re.sub(r' have( [^.;‖]{0,20})?(?= (systems|procedures?|policy|policies|process|processes|strategy|strategies|practice|practices|methodology|methodologies) )', r' maintain\1 ', input_sentence)
        input_sentence = re.sub(r' prior to ', r' before ', input_sentence)
        input_sentence = re.sub(r' where, ', r' when, ', input_sentence)
        input_sentence = re.sub(r' where ', r' when ', input_sentence)
        input_sentence = re.sub(r'^where ', r'when ', input_sentence)
        input_sentence = re.sub(r' Where, ', r' When, ', input_sentence)
        input_sentence = re.sub(r' Where ', r' When ', input_sentence)
        input_sentence = re.sub(r'^Where ', r'When ', input_sentence)
        input_sentence = re.sub(r' prior to ', r' before ', input_sentence)
        input_sentence = re.sub(r' Prior to ', r' Before ', input_sentence)
        input_sentence = re.sub(r'^Prior to ', r'Before ', input_sentence)

        # fast-skip sentences that cannot lead to a match
        if not(False
            or any((verb in input_sentence) for verb in INTERESTING_VERBS)
            or any((noun in input_sentence) for noun in INTERESTING_NOUNS)
        ): return


        #this code block does the same as the one above???
        if not(False
            or re.search(r'\b(' + '|'.join(INTERESTING_VERBS) + r')\b', input_sentence)
            or re.search(r'\b(' + '|'.join(INTERESTING_NOUNS) + r')s?\b', input_sentence)
        ): return

        return input_sentence 
    
    
    @staticmethod
    def filter_data_to_relevant_verbs(  parsed_sentence: dict ) -> list:
        
        '''
        Method iterates over all the 'verbs' from a sentence parsed with AllenNLP model. Next, it checks if the verb is interesting or not, using hand crafted rules. It returns a List containing Tuples of len==3. The Tuples contain the verb (dict), a boolean indicating if it is 'relevant_case_based_on_verb', and a boolean indicating if it is a 'relevant_case'.   
        :param parsed_sentence: Dict.
        :return: List. 
        '''
        
        if not isinstance( parsed_sentence , dict ):
            raise TypeError( f"{parsed_sentence} must be a dict" )
        
        #keep track of detected relevant and irrelevant verbs, AD
        verbs=[]

        for verb_data in parsed_sentence['verbs']:

            # filter the data to relevant usages of those verbs
            is_relevant_case=False
            is_relevant_case_based_on_verb=False

            verb = verb_data['verb']
            srl_output = str(verb_data['description'])

            # do not go further if we don't have a verb (or if the verb is shall)
            if verb == '' or verb == 'shall': 
                #print( verb,  ":", "verb is shall or missing" )
                verbs.append( (verb_data , is_relevant_case_based_on_verb , is_relevant_case )  )
                continue


            # (filter for verbs)
            verb_pos = srl_output.index("[V:") if "[V:" in srl_output else 0
            is_relevant_case = (is_relevant_case or (False
                or (verb in OBLIGATION_VERBS)
                or (verb in INTERESTING_VERBS and (False
                    or ("[ARGM-MOD:" in srl_output and not('[ARGM-MOD: may' in srl_output))
                    or (" shall " in srl_output[max(0,verb_pos-50):verb_pos] and not(" shall include " in srl_output[max(0,verb_pos-50):verb_pos]) and "[ARG0: " in srl_output and "[ARG1: " in srl_output)
                ))
            ))

            # TODO

            # (filter for nouns)
            is_relevant_case_based_on_verb = is_relevant_case
            is_forgiving_noun_verb = True #verb == 'include' or verb == 'included' or verb == 'consist' or verb == 'consisted' or verb == 'comprise' or verb == 'comprised' or verb in forgiving_noun_verbs
            is_relevant_case = (is_relevant_case or (True
                and (verb != 'assigned') # just found it caused errors, and I don't see why this could be useful
                and ("[ARGM-MOD:" in srl_output and not('[ARGM-MOD: may' in srl_output))
                and (False
                    or (True
                        and verb in INTERESTING_NOUNS_VALID_VERBS_SUBJ
                        and re.search(r'\[ARG[0-9]: [^\]]*\b(' + '|'.join(INTERESTING_NOUNS) + r')s?\b', srl_output)
                    )
                    or (True
                        and verb in INTERESTING_NOUNS_VALID_VERBS_DIRECT
                        and re.search(r'\[ARG[1-9]: [^\]]*\b(' + '|'.join(INTERESTING_NOUNS if is_forgiving_noun_verb else OBLIGATION_NOUNS) + r')s?\b', srl_output)
                    )
                )
                and (verb != 'comply' or not(" following " in srl_output))
            ))

            verbs.append( ( verb_data, is_relevant_case_based_on_verb , is_relevant_case  )  )

            #print( verb  , "( is it a relevant case):",  is_relevant_case )

        return verbs

    
    @staticmethod
    def convert_to_xml_and_fix_tags_hand_crafted( verb_tuple: Tuple[ dict, bool, bool ] ,  subsentence: str  ):
        
        '''
        Input is a tuple (dict, boolean, boolean) (element from the list generated via staticmethod filter_data_to_relevant_verbs). dict is converted to xml. Some tags are fixed using hand crafted rules.
        :param verb_tuple: Tuple.
        :subsentence: str. The subsentence, i.e. enumeration/list, see method process_sentences and src.transform.
        :return: xml.dom.minidom.Document. 
        '''
        
        srl_output = str( verb_tuple[0]['description'] )  #only process the relevant cases...  ( i.e., check the flag "is_relevant_case" )
        verb=verb_tuple[0]['verb']
        is_relevant_case_based_on_verb=verb_tuple[1]

        #Add html tags to srl_output:

        srl_html_output = srl_output
        srl_html_output = re.sub(r'>', r'&gt;', srl_html_output)
        srl_html_output = re.sub(r'<', r'&lt;', srl_html_output)
        srl_html_output = re.sub(r'\[([a-zA-Z0-9]+[^\[\]:]*)\]', r'\1', srl_html_output) # fix a weird bug where a span has no tag, for some reason
        srl_html_output = re.sub(r'\[([^ ]+): ', r'<span class="\1">', srl_html_output)
        srl_html_output = re.sub(r'\]', r'</span>', srl_html_output)
        '''
        next line adds context to the input sentence, it replaces <span class="ARG2">to the commision following ... </span> with 
        <span class="ARG2">to the commision following ... < input_sentence_following_data  >  </span> .
        '''
        if len(subsentence) > 0: srl_html_output = re.sub(r'(<span[^>]*>[^<]* following\b[^<]*)(</span>)', lambda m: m.group(1)+' '+subsentence+m.group(2), srl_html_output)
        srl_html_output = re.sub(r'<span[^>]+>([,.;])</span>', r'\1', srl_html_output)
        srl_html_output = re.sub(r'( ?[,.;])</span>', r'</span>\1', srl_html_output)
        srl_html_output = re.sub(r'(?<=[a-z][a-z][a-z])( ?[)])</span>', r'</span>\1', srl_html_output)
        srl_html_output = re.sub(r'(\([^<>]*?)</span> \)', r'\1 )</span>', srl_html_output)
        srl_html_output = '<p>' + srl_html_output + '</p>'

        try:
            srl_dom_output = parseString(srl_html_output)
        except:
            raise ValueError(srl_html_output)


        # fix particular verb constructions
        args = list(filter(lambda s: match_class(s, r'^(ARG[12]|ARGM-ADV|ARGM-MNR)$'), srl_dom_output.getElementsByTagName("span")))
        args_pred = list(map(lambda arg: re.sub(
            r'^(?:only |at least )?(?:(about|of|to|on|for|with|in|that|where|when|if) )?(?:.*)$' if match_class(arg, r'^(ARG[12])$') else r'^(?:only |at least )?(?:(about|of|to|on|for|with) )?(?:.*)$', 
            r'ARGS[\1]' if match_class(arg, r'^(ARG[12])$') else r'ARGM[\1]', 
            text_of(arg), re.I), args))

        #print(srl_output)
        #print(" ".join(args_pred))

        # get some metadata
        verb_is_provide = re.match(r'^(provide|provides|provided|providing)$', verb)
        verb_is_notify = re.match(r'^(notify|notifies|notifying|notified)$', verb)
        verb_is_inform = re.match(r'^(inform|informs|informing|informed)$', verb)
        verb_is_demonstrate = re.match(r'^(demonstrate|demonstrates|demonstrating|demonstrated)$', verb)
        verb_is_analyze = re.match(r'^(analyze[sd]?|analyse[sd]?|analy[zs]ing)$', verb)
        verb_is_include = re.match(r'^(include|includes|included)$', verb)
        verb_is_consist = re.match(r'^(consist(|s|ed)|comprise(|s|d)|incorporate(|s|d))$', verb)
        #verb_is_be = re.match(r'^(be|been|is|are|was|were|being|become|becomes|became|becoming)$', verb)

        # fix big but frequent argument-class mistakes
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG1,ARG2'.split(',')):
                if re.search(r'^(on the basis of )', text_of(arg), re.I):
                    update_class(arg, 'ARGM-MNR')
                elif re.match(r'^(into account)', text_of(arg), re.I):
                    update_class(arg, 'ARGM-MNR')


        # now let's fix "provide with"
        if (verb_is_provide) and (('ARGS[with]' in args_pred) or ('ARGM[with]' in args_pred)):
            for i, arg in enumerate(args):
                arg_pred = args_pred[i]
                arg_class = arg.getAttribute('class')
                if arg_pred[0:4] == 'ARGS' and arg_pred != 'ARGS[with]' and looks_like_arg2(text_of(arg)):
                    update_class(arg,"ARG2")
                elif arg_pred[4:] == '[with]':
                    update_class(arg,"ARG1")

        # now let's fix "notify something to someone"
        elif (verb_is_notify or verb_is_provide or verb_is_demonstrate) and (('ARGS[to]' in args_pred) or ('ARGM[to]' in args_pred)):
            for i, arg in enumerate(args):
                arg_pred = args_pred[i]
                arg_class = arg.getAttribute('class')
                print(arg_pred, arg_class, text_of(arg))
                if arg_class == 'ARG1' and (arg_pred == 'ARGS[to]' or looks_like_arg2(text_of(arg),allow_them=False)):
                    update_class(arg, 'ARG2')
                elif arg_class == 'ARG2' and arg_pred != 'ARGS[to]' and not(looks_like_arg2(text_of(arg),allow_them=False)):
                    update_class(arg, 'ARG1')
                elif arg_pred == 'ARGM[to]' and looks_like_arg2(text_of(arg)):
                    update_class(arg, 'ARG2')
                elif arg_pred == 'ARGS[that]':
                    update_class(arg, 'ARG1')

        # now let's fix "notify someone of something"
        elif (verb_is_notify or verb_is_inform) and (('ARGS[about]' in args_pred ) or ('ARGM[about]' in args_pred) or ('ARGS[of]' in args_pred) or ('ARGM[of]' in args_pred)  or ('ARGS[on]' in args_pred)  or ('ARGM[on]' in args_pred) or ('ARGS[that]' in args_pred)):
            did_remap_1_to_2 = False
            for i, arg in enumerate(args):
                arg_pred = args_pred[i]
                arg_class = arg.getAttribute('class')
                if arg_class == 'ARG1':
                    if arg_pred[4:] != '[that]':
                        did_remap_1_to_2 = True
                        update_class(arg, 'ARG2')
                elif arg_pred[4:] == '[about]':
                    update_class(arg, 'ARG1')
                elif arg_pred[4:] == '[that]' and not(looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG1')
                elif arg_pred[4:] == '[of]' and not(looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG1')
                elif arg_pred == 'ARGS[on]' and not(looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG1')
                elif arg_class == 'ARG2' and did_remap_1_to_2 and not(looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG1')
        elif (verb_is_notify or verb_is_inform):
            for i, arg in enumerate(args):
                arg_pred = args_pred[i]
                arg_class = arg.getAttribute('class')
                if arg_class == 'ARG1' and (looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG2')
                elif arg_pred[4:] == '[about]' and not(looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG1')
                elif arg_pred[4:] == '[that]' and not(looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG1')
                elif arg_pred[4:] == '[of]' and not(looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG1')
                elif arg_pred == 'ARGS[on]' and not(looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG1')
                elif arg_pred == 'ARGS[with]' and not(looks_like_arg2(text_of(arg))):
                    update_class(arg, 'ARG1')
                elif re.match(r'^whether ', text_of(arg)):
                    update_class(arg, 'ARG1')
        elif (verb_is_analyze):
            for i, arg in enumerate(args):
                arg_pred = args_pred[i]
                arg_class = arg.getAttribute('class')
                if arg_class == 'ARG2':
                    update_class(arg, 'ARG3')
        elif (verb_is_include):
            for i, arg in enumerate(args):
                arg_pred = args_pred[i]
                arg_class = arg.getAttribute('class')
                if arg_class == 'ARG2':
                    update_class(arg, 'ARG0')
        elif (verb_is_consist):
            for i, arg in enumerate(args):
                arg_pred = args_pred[i]
                arg_class = arg.getAttribute('class')
                if arg_class == 'ARG2':
                    update_class(arg, 'ARG1')
                if arg_class == 'ARG1':
                    update_class(arg, 'ARG0')

        # now let's fix "when requested / when asked / upon request" not being considered a time argument
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARGM-MNR,ARGM-ADV,ARGM-CAU,ARGM-LOC,ARGM-PRD'.split(',')):
                if re.search(r'\b(when(ever)? requested|when(ever?) asked|(up)?on (the )?request|if requested|on demand|in cases? of|in the ([^ ]+ )?cases?|on( at least)? an? ((semi|bi|tri) ?-? ?)?((annual|monthly|quarterly|daily|regular|frequent|scheduled|ongoing) )basis|continuously|constantly|regularly|promptly|thereafter|(after|before) [^ ]ing)\b', text_of(arg), re.I):
                    update_class(arg, 'ARGM-TMP')
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG2,ARG3'.split(',')):
                if re.search(r'\b(when(ever)? requested|when(ever?) asked|(up)?on (the )?request|if requested|on demand|in cases? of|in the ([^ ]+ )?cases?|on( at least)? an? ((semi|bi|tri) ?-? ?)?((annual|monthly|quarterly|daily|regular|frequent|scheduled|ongoing) )basis|continuously|constantly|regularly|promptly|thereafter|(after|before) [^ ]ing)\b', text_of(arg), re.I):
                    update_class(arg, 'ARGM-TMP')

        # now let's fix "of the following" not being considered a complement to C1 argument
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARGM-MNR,ARGM-ADV,ARGM-CAU,ARGM-LOC,ARGM-PRD,ARG2'.split(',')):
                if match_class_in_list(arg,'ARG2') and looks_like_arg2(text_of(arg)): continue
                if re.search(r'\b(the following)\b', text_of(arg), re.I):
                    if re.search(r'^([^ ]+ )?(in the following ways?|by using|based on|on the basis of)\b', text_of(arg), re.I):
                        update_class(arg, 'ARGM-MNR')
                    elif re.search(r'^([^ ]+ )?(when(ever)?|where|if)\b', text_of(arg), re.I):
                        update_class(arg, 'ARGM-TMP')
                    else:  
                        update_class(arg, 'C-ARG1')
                else:
                    if re.search(r'^(only |at least )?(by using|based on|on the basis of)\b', text_of(arg), re.I):
                        update_class(arg, 'ARGM-MNR')


        # now let's fix "when/if" not being considered a time/condition argument
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARGM-ADV,ARGM-LOC'.split(',')):
                if re.search(r'^([^ ]+ )?(when(ever)?|where|if)\b', text_of(arg), re.I):
                    update_class(arg, 'ARGM-TMP')

        # now let's fix "publicized to the masses" where "to the masses" is a ARGM-GOL
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARGM-GOL'.split(',')):
                if looks_like_arg2(text_of(arg)):
                    update_class(arg, 'ARG2')
                else:
                    update_class(arg, 'ARGM-TMP')
        # transform into ARGM-MNR any "for each" block
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG1,ARG2'.split(',')):
                if (True
                    and (re.match("for (each|all|every)\b", text_of(arg)))
                ):
                    update_class(arg, 'ARGM-MNR')
        # transform ARG2 into ARG3 if it's "subject to"
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG2'.split(',')):
                if (True
                    and not(is_relevant_case_based_on_verb)
                    and not(looks_like_arg2(text_of(arg)))
                    and (not(verb in INTERESTING_VERBS ) or re.match("subject to", text_of(arg)))
                ):
                    update_class(arg, 'ARG3')
        # transform ARG0 into ARG3 if it's not an institution
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG0'.split(',')):
                if (True
                    and not(is_relevant_case_based_on_verb)
                    and not(looks_like_arg0(text_of(arg)))
                ):
                    update_class(arg, 'ARG3')
        # enable has a special ARG2->ARG0
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG2'.split(',')):
                if (True
                    and (verb == 'enable' or verb == 'enabled')
                ):
                    update_class(arg, 'ARG0')
        # special rule for ARG3 that actually look like an institution
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG3'.split(',')):
                if (True
                    and ((text_of(arg)[0:3] == 'to ') or (text_of(arg)[0:4] == 'for '))
                    and (looks_like_arg2(text_of(arg)))
                ):
                    update_class(arg, 'ARG2')

        return srl_dom_output
    
    
    def predict_obligation_frequency( self, input_sentence:str , srl_dom_output  ):
        
        '''
        Input is an xml element, and the sentence the xml element (verb+context) was part of. Method calculates the obligation frequence using spacy model (self.nlp), and accordingly adds tags to the xml element.
        :param input_sentence: String.
        :param srl_dom_output: xml.dom.minidom.Document.
        :return: xml.dom.minidom.Document. 
        '''
        
        def get_verb( srl_dom_output  ):
            verb=''
            for item in srl_dom_output.getElementsByTagName( "span" ):
                if item.getAttribute('class')=='V':
                    verb=text_of(item)
                    return verb
            return verb
        
        verb=get_verb( srl_dom_output )
        
        # deduce obligation frequency from full paragraph
        paragraph_frequence_predictions = self.nlp(input_sentence)

        # deduce obligation frequence from analyzed sentence
        sentence_frequence_predictions = self.nlp(' '.join(map(lambda arg: text_of(arg), srl_dom_output.getElementsByTagName("span"))))

        # deduce obligation frequency from simplified sentence
        argmtmp_sentence = "they shall report it"
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARGM-TMP'.split(',')):
                argmtmp_sentence += ', ' + text_of(arg)
        argmtmp_sentence += '.'
        argmtmp_frequence_predictions = self.nlp(argmtmp_sentence) if "," in argmtmp_sentence else sentence_frequence_predictions

        par_pred_balance = 0.45
        sen_pred_balance = 0.25 
        cat1_pred = par_pred_balance * paragraph_frequence_predictions.cats['1'] + sen_pred_balance * sentence_frequence_predictions.cats['1'] + (1.0-par_pred_balance-sen_pred_balance) * argmtmp_frequence_predictions.cats['1']
        cat2_pred = par_pred_balance * paragraph_frequence_predictions.cats['2'] + sen_pred_balance * sentence_frequence_predictions.cats['2'] + (1.0-par_pred_balance-sen_pred_balance) * argmtmp_frequence_predictions.cats['2']
        cat3_pred = par_pred_balance * paragraph_frequence_predictions.cats['3'] + sen_pred_balance * sentence_frequence_predictions.cats['3'] + (1.0-par_pred_balance-sen_pred_balance) * argmtmp_frequence_predictions.cats['3']

        # apply corrective actions for by-dates
        if re.search(r'[Bb](y|efore)(no later than )?( the)? [0-9]+ (January|February|March|April|May|June|July|August|September|October|November|December) [0-9][0-9][0-9]+', argmtmp_sentence):
            cat1_pred = 0.35 + 0.65 * cat1_pred
            cat2_pred = 0.65 * cat2_pred
            cat3_pred = 0.65 * cat3_pred

        # apply corrective actions depending on verb (collect, gather, maintain, monitor)
        if verb in "collect|gather|maintain|monitor|maintained|monitored":
            cat3_pred = 0.35 + 0.65 * cat3_pred
            cat2_pred = 0.65 * cat2_pred + 0.35 * cat1_pred
            cat1_pred = 0.30 * cat1_pred

        # apply corrective actions for obvious demand-based requests
        if re.search(r'\b(upon request|when requested|on demand|when asked|as needed|when required)\b', argmtmp_sentence, re.I):
            cat2_pred = 0.25 + 0.75 * cat2_pred
            cat1_pred = 0.75 * cat1_pred
            cat3_pred = 0.75 * cat3_pred

        best_cat = max([1,2,3], key=lambda i: [cat1_pred,cat2_pred,cat3_pred][i-1])

        srl_dom_output.lastChild.setAttribute('data-frequency-split', str(cat1_pred)+'|'+str(cat2_pred)+'|'+str(cat3_pred))
        srl_dom_output.lastChild.setAttribute('data-frequency-class', str(best_cat))
        srl_dom_output.lastChild.setAttribute('data-frequency-could-be-3', 'true' if cat3_pred > 0.35 else 'false')
        srl_dom_output.lastChild.setAttribute('data-frequency-could-be-2', 'true' if cat2_pred > 0.35 else 'false')
        srl_dom_output.lastChild.setAttribute('data-frequency-could-be-1', 'true' if cat1_pred > 0.35 else 'false')
        srl_dom_output.lastChild.setAttribute('data-frequency-might-be-3', 'true' if cat3_pred > 0.15 else 'false')
        srl_dom_output.lastChild.setAttribute('data-frequency-might-be-2', 'true' if cat2_pred > 0.15 else 'false')
        srl_dom_output.lastChild.setAttribute('data-frequency-might-be-1', 'true' if cat1_pred > 0.15 else 'false')

        return srl_dom_output
    
    
    def co_reference_resolution(  self, srl_dom_output ):

        '''
        Input is an xml element. Method solves co-reference resolution, and changes tags accordingly. For this it uses self.last_known_subject. 
        :param srl_dom_output: xml.dom.minidom.Document.
        :return: xml.dom.minidom.Document. 
        '''
        
        when_clause = None
        when_clause_uppercase = False
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARGM-TMP'.split(',')):
                if re.match(r'^(when|where|if|as soon as) ',text_of(arg), re.IGNORECASE):
                    when_clause = text_of(arg)
                    when_clause_uppercase = when_clause[0].isupper() or (arg.previousSibling == None or arg.previousSibling.previousSibling == None)

        when_clause_subject = ''
        if when_clause:
            subj_match = re.match(r'(?i:(?:when|where|if|as soon as))(?: ?[,][^,.]+[,])? ((an?|the|this|that|their|its|one|two|three|any( such( an?)?)?|such( an?)?|all|every|each) ([^ ]+)( ([^ ]+ )?(?i:' + ALL_ARG2_KEYWORDS + r'))?|([^ ]+ ){0,2}(?i:' + PLURAL_OR_NODET_ARG2_KEYWORDS + r')|[A-Z][A-Z]+|([A-Z][a-z]+ )+)', when_clause)
            subj_match_str = subj_match.group(1) if subj_match else ''
            when_clause_subject = re.sub(r'^(an?|the|this|that|their|its|one|any( such( an?)?)?|such( an?)?) (?![A-Z][A-Z])', 'this ', subj_match_str).strip()
            when_clause_subject = re.sub(r'^(an?|one|any( such( an?)?)?|such( an?)?) ', 'this ', when_clause_subject).strip()

        if when_clause_subject:
            # when an institution does X, it shall report Y to Z.
            for arg in srl_dom_output.getElementsByTagName("span"):
                if match_class_in_list(arg, 'ARG0'.split(',')):
                    if (False
                        or text_of(arg).lower() == 'it'
                        or text_of(arg).lower() == 'they'
                    ):
                        if text_of(arg).lower() == 'they': when_clause_subject = re.sub(r'^this ', 'these ', when_clause_subject)
                        arg.setAttribute('data-old-text', text_of(arg))
                        arg.firstChild.data = when_clause_subject
                    else:
                        old_text = arg.firstChild.data
                        new_text = re.sub(r'^(its|their) ', when_clause_subject + " 's ", text_of(arg))
                        if old_text != new_text:
                            arg.setAttribute('data-old-text', old_text)
                            arg.firstChild.data = new_text

        if when_clause:
            # when something happens, it shall be reported to Z.
            for arg in srl_dom_output.getElementsByTagName("span"):
                if match_class_in_list(arg, 'ARG1'.split(',')):
                    if (False
                        or (text_of(arg).lower() == 'it' and (when_clause_uppercase or verb == 'reported'))
                    ):
                        arg.setAttribute('data-old-text', text_of(arg))
                        arg.firstChild.data = re.sub(r'^(?i:(if|when)) ', 'the fact that ', when_clause)
                    elif (False
                        or (text_of(arg) == 'them' and when_clause_uppercase)
                    ):
                        #TODO: find object of when clause, use that
                        arg.setAttribute('TODO','true')

        # last_known_subject co-reference resolution (for subjects, obviously)
        if self.last_known_subject:
            for arg in srl_dom_output.getElementsByTagName("span"):
                if match_class_in_list(arg, 'ARG0'.split(',')):
                    if (False
                        or (text_of(arg).lower() == 'it')
                        or (text_of(arg).lower() == 'they')
                    ):
                        current_last_known_subject = self.last_known_subject
                        if text_of(arg).lower() == 'they': current_last_known_subject = re.sub(r'^this ', 'these ', self.last_known_subject)
                        arg.setAttribute('data-old-text', text_of(arg))
                        arg.setAttribute('data-last-known-subject','true')
                        arg.firstChild.data = current_last_known_subject

        #TODO: broader co-reference resolution
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG0,ARG1,ARG2,ARG3'.split(',')):
                if (False
                    or (text_of(arg).lower() == 'it')
                    or (text_of(arg).lower() == 'they')
                    or (text_of(arg).lower() == 'them')
                    or (text_of(arg).lower() == 'this')
                    or (text_of(arg).lower() == 'that')
                ):
                    arg.setAttribute('TODO','true')

        return srl_dom_output
    
    def process_sentence( self, sentence:str, subsentence:str, main_sentence: bool=True ):
        
        '''
        Method processes a sentence, either a main sentence or a subsentence (in between ❮  ❯, see transform.py ).
        :param sentence: String. Sentence to process
        :param subsentence: String. Subsentence, i.e. sentence in between ❮  ❯. 
        :param main_sentence: Boolean. If it is main sentence or subsentence. If it is subsentence, then we do not update the last known subject and location.
        :return: List.
        '''
        
        list_xml=[]
        
        if main_sentence:
        
            self.update_pending_location_names( sentence )

            self.update_last_known_subject( sentence )

        sentence=self.check_if_interesting_sentence_and_process_via_regexes( sentence )

        if not sentence: #if not an interesting sentence (i.e., it is a definition, it does not contain interesting verbs), then continue
            return []

        #parse the sentence with ALLEN_NLP model:
        parsed_sentence=self.parse_sentence( sentence )

        verbs=self.filter_data_to_relevant_verbs( parsed_sentence )

        #check if verbs is not empty:
        if not verbs:
            return []

        for verb in verbs:

            is_relevant_case=verb[2]

            if not is_relevant_case:
                continue

            #if relevant verb, and if it is the first interesting verb in this section/paragraph, ..., then save the location (section/paragraph) as an xml element in list_xml:
            list_location_xml=self.get_and_flush_pending_location_names()
            list_xml+=list_location_xml

            srl_dom_output=self.convert_to_xml_and_fix_tags_hand_crafted(  verb, subsentence  )

            #process the paragraph (sentence) and 'verb' with spacy model
            srl_dom_output=self.predict_obligation_frequency( sentence, srl_dom_output  )

            srl_dom_output=self.co_reference_resolution(  srl_dom_output  )

            list_xml.append( srl_dom_output )
    
        return list_xml
    
    def process_sentences( self, ListSofaID: str='ListView'  ) ->list:
        
        '''
        Method iterates over self.sentences. Sentences are parsed using allenNLP model. Interesting verbs and context in each sentence are converted to an xml element. Tags are fixed using hand crafted rules. Obligation frequency (using Spacy model) and co-reference resolution is also taken care of (via updating tags in the xml element). xml elements are appended to a list and returned. 
        Subsentences, i.e. sentence in between ❮  ❯ are subsentences, and if they contain a reporting obligation, they are also parsed.
        :param spacy_path: String. Path to spacy model. 
        :return: List.
        '''
        
        self._list_xml=[]

        #sentences=self.cas.get_view( ListSofaID ).sofa_string.split( "\n" )
        
        offsets=[]
        sentences=[]
        for item in self.cas.get_view( ListSofaID ).sofa_string.split( "\n" ):
            offset=eval(item.split( "|" )[-1])
            assert type( offset ) ==tuple
            offsets.append( offset )
            sentences.append( "|".join(item.split( "|" )[:-1]) )

        #sanity check
        assert( len( offsets ) == len( sentences ) )
        
        for sentence, offset in zip(sentences, offsets):
            
            sentence=sentence.rstrip( '\r\n' )
            subsentence = re.sub(r'(^[^❮]+|[^❯]+$)',r'', sentence)  #finds everything between " ❮ ❯ " ==>the main sentence
            if len(subsentence) > 0: sentence = sentence.replace(subsentence, '', 1)  #remove everything inside " ❮ ❯ " from the string
    
            #process the main_sentence
            list_xml_sentence=self.process_sentence( sentence, subsentence, True )
            
            #set the offset
            #for xml_item in list_xml_sentence:
            [xml_item.lastChild.setAttribute( 'original_document_begin', str(offset[0])) for xml_item in list_xml_sentence]
            [xml_item.lastChild.setAttribute( 'original_document_end', str(offset[1])) for xml_item in list_xml_sentence]

            self._list_xml+=list_xml_sentence
            
            #process subsentence:
            
            if " shall " in subsentence:
                list_subsentences = re.sub(r' ‖ and/or ', r' and/or ', subsentence).lstrip('❮').rstrip('❯').split(' ‖ ')
                for item_subsentence in list_subsentences:
                    list_xml_subsentence=self.process_sentence( item_subsentence, '', False )
                    #set the offset
                    [xml_item.lastChild.setAttribute( 'original_document_begin', str(offset[0])) for xml_item in list_xml_subsentence]
                    [xml_item.lastChild.setAttribute( 'original_document_end', str(offset[1])) for xml_item in list_xml_subsentence]
                    self._list_xml+=list_xml_subsentence
                
        return self._list_xml
    
    def add_xml_to_cas( self , template_path: str , ROSofaID: str='ReportingObligationsView' ):
        
        '''
        Method creates the view ROSofaID, and adds the xml elements from the list of xml's (xml.dom.minidom.Document) elements as sofa to the view (html), using template_path.
        :param template_path: String. Path to html template.
        :param ROSofaID: String. Name of the view.
        :return: None.
        '''
        
        self.cas.create_view(ROSofaID)
        
        list_xml_string=[]
        for xml in self._list_xml:
            list_xml_string.append(xml.lastChild.toxml())
                
        html_template=open(  template_path ).read()
                
        self.cas.get_view( ROSofaID ).sofa_string=html_template + "\n".join( list_xml_string )
        
    def print_to_html( self, template_path:str, output_path:str):
        
        '''
        Method prints xml element from a list of xml's (xml.dom.minidom.Document) elements (self._list_xml, see method process_sentences) to html, using template_path.
        :param template_path: String. Path to html template. 
        :param output_path: String. Output path. 
        :return: None.
        '''

        os.makedirs( os.path.dirname( output_path ) , exist_ok=True  )

        print( f"Writing output to {output_path} using {template_path} as html template"  )

        list_xml_string=[]
        for xml in self._list_xml:
            list_xml_string.append(xml.lastChild.toxml())
        
        html_template=open(  template_path ).read()
        
        with open( output_path , "w"  ) as f:
            f.write( html_template + "\n".join( list_xml_string )  )
         