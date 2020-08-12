from allennlp.predictors.predictor import Predictor
from xml.dom.minidom import parseString
import spacy
import sys
import re

import inspect

#INPUT:
input_sentences = [
    "2. Institutions shall have in place clearly defined policies and procedures for the overall management of the trading book. These policies and procedures shall at least address the activities the institution considers to be trading and as constituting part of the trading book for own funds requirement purposes. These policies and procedures shall at least address the extent to which a position can be marked-to-market daily by reference to an active, liquid two-way market. These policies and procedures shall at least address for positions that are marked-to-model, the extent to which the institution can ❬identify all material risks of the position ‖ and/or hedge all material risks of the position with instruments for which an active, liquid two-way market exists ‖ and/or derive reliable estimates for the key assumptions and parameters used in the model❭. These policies and procedures shall at least address the extent to which the institution can, and is required to, generate valuations for the position that can be validated externally in a consistent manner. These policies and procedures shall at least address the extent to which legal restrictions or other operational requirements would impede the institution's ability to effect a liquidation or hedge of the position in the short term. These policies and procedures shall at least address the extent to which the institution can, and is required to, actively manage the risks of positions within its trading operation. These policies and procedures shall at least address the extent to which the institution may transfer risk or positions between the non-trading and trading books and the criteria for such transfers.",
    #"The EBA shall issue additional guidelines twice a year on what types of investments are considered at risk.",
]


input_sentences=[  'EBA shall review something and they should notify this to the commision'   ]

input_sentences = open('input_dir/sentences-small.txt')

#input_sentences=[  "Section 1", "Article 1", "EBA shall review something and they should notify this to the commision following " ] 



outfile_path = "output_dir/out_francois.html"

if len(sys.argv) > 1 and len(sys.argv[1])>=1:
    input_sentences = open(sys.argv[1])
    if sys.argv[1].endswith('.txt'): outfile_path = sys.argv[1] + '.relations.html'

if len(sys.argv) > 2 and len(sys.argv[2])>=1:
    outfile_path = sys.argv[2]

outfile = open(outfile_path, 'w+')
for template_line in open('./out.html.template'):
    outfile.write(template_line)

# helpers
def text_of(element):
    return str(element.firstChild.data)

no_determiner_arg2_keywords = "EBA|ESMA|ECB|EIF|EIB|EIOPA|ESRB|BIS|FSA|PRA|EIOPA|FSB|SRB|FMI|IRSG|OPSG|AMICE|(member )?state|(senior |upper |lower )?management|(office )?(staff|personnel)|(US |American )?(Senate|Congress)|someone|somebody"
singular_arg2_keywords = "Commission|Institution|EBA|European|Parliament|Council|Senate|ESMA|ECB|EIF|EIB|EIOPA|ESRB|BIS|FSA|PRA|EIOPA|FSB|SRB|CCP|SFT|MMF|ETF|REIT|FMI|IORP|ODTI|G-SIB|G-SIFI|CMG|CSD|AIF|NCA|RCA|((competent|resolution||national|regional) )?authority|government|entity|(member )?state|(central )?bank|party|counterparty|(senior |upper |lower )?management|provider|originator|firm|seller|buyer|agent|lawyer|(control |audit(ing)? )unit|group|member( state)?|central body|head of (the )?[^ ]+|company|organization|organisation|committee|supervisor|personnel|staff|actuary|accountant|manager|person|lender|issuer|leader|customer|individual|association|team|corporation|enterprise|university|foundation|intermediary|insurer|borrower|depositor|(bond|policy)holder|liquidator|debtor|creditor|transferor|transferee|distributor|broker|custodian|client|investor|agency|subsidiary|(financial )?conglomerate|competitor"
plural_arg2_keywords = "Commissions|Institutions|Parliaments|Councils|Senates|CCPs|SFTs|MMFs|ETFs|REITs|FMIs|IORPs|ODTIs||G-SIBs|G-SIFIs|CMGs|CSDs|AIFs|NCAs|RCAs|((competent|resolution|national|regional) )?authorities|governments|entities|(member )?states|(central )?banks|parties|counterparties|(senior |upper |lower )?managements|providers|originators|firms|sellers|buyers|agents|lawyers|(control |audit(ing)? )units|groups|members?( states)?|central bodies|heads of (the )?[^ ]+|companies|organizations|organisations|committees|supervisors||personnels|staffs|actuaries|accountants|managers|persons|people|lenders|issuers|leaders|customers|individuals|associations|teams|corporations|enterprises|universities|foundations|intermediaries|insurers|borrowers|depositors|(bond|policy)holders|liquidators|debtors|creditors|transferors|transferee|distributors|brokers|custodians|clients|investors|agencies|subsidiaries||(financial )?conglomerates|competitors"
all_arg2_keywords = singular_arg2_keywords + '|' + plural_arg2_keywords
plural_or_nodet_arg2_keywords = plural_arg2_keywords + '|' + no_determiner_arg2_keywords
def looks_like_arg2(text:str,allow_them=True):
    text_start = text[0:35]
    if re.search(r'(?<!of the )(?<!of an )(?<!of a )\b(' + all_arg2_keywords + r')\b(?! ?\'s)', text_start, re.I):
        return True
    if re.match(r'^([^ ]+ |at least )?(to |for )?(us|him|her|the others?)\b', text_start, re.I):
        return True
    if allow_them and re.match(r'^([^ ]+ |at least )?(to |for )?(them)\b', text_start, re.I):
        return True
    return False

def looks_like_arg0(text: str):
    return looks_like_arg2(text, False) or text.lower() in 'they|it'.split('|')

def match_class(span, reg): 
    return re.search(reg, span.getAttribute('class'))
def match_class_in_list(span, list): 
    return span.getAttribute('class') in list

def update_class(arg, new_class):
    arg_class = arg.getAttribute('class')
    if arg_class != new_class:
        #print(">"+new_class+":" + arg.toxml())
        arg.setAttribute('class', new_class)
        last_frame = inspect.getouterframes(inspect.currentframe())[1]
        last_frame_str = last_frame.filename + ':' + str(last_frame.lineno)
        arg.setAttribute('data-update-stack', last_frame_str)
        #print(">"+last_frame_str)

# start loading
print("Loading the various models...")

# load the srl model
srl = Predictor.from_path("./bert-base-srl-2019.06.17.tar.gz")

# load the spacy frequency model
nlp = spacy.load("./spacy-textcat")



# small trick to remember the last subject of a "shall expression"
last_known_subject = ''
def update_last_known_subject(input_sentence):
    global last_known_subject
    input_sentence = re.sub(r'^ *[0-9]*[.] *', r'', input_sentence)
    input_sentence = re.sub(r'^ *\([a-z0-9]*\) *', r'', input_sentence)
    # general "when" lookup
    subj_match = re.search(r'(?i:(?:when|where|if|as soon as))(?: ?[,][^,.]+[,])? ((an?|the|this|that|their|its|one|two|three|any( such( an?)?)?|such( an?)?|all|every|each) ([^ ]+)( ([^ ]+ )?(?i:' + all_arg2_keywords + r'))?|([^ ]+ ){0,2}(?i:' + plural_or_nodet_arg2_keywords + r')|[A-Z][A-Z]+|([A-Z][a-z]+ )+)', input_sentence)
    subj_match_str = str(subj_match.group(1)) if subj_match else ''
    when_clause_subject = re.sub(r'^(an?|the|this|that|their|its|one|any( such( an?)?)?|such( an?)?) (?![A-Z][A-Z])', 'this ', subj_match_str, re.I).strip()
    when_clause_subject = re.sub(r'^(an?|one|any( such( an?)?)?|such( an?)?) ', 'this ', when_clause_subject, re.I).strip()
    if when_clause_subject and looks_like_arg0(when_clause_subject): 
        last_known_subject = when_clause_subject

    if re.search(r'shall|may|must', input_sentence):
        # shall lookup
        subj_match = re.search(r'(?:^|(?=[A-Z])|, |‖ (?:and/or )?)((?i:(an?|the|this|that|their|its|one|two|three|any( such( an?)?)?|such( an?)?|all|every|each)) ([^ ]+)( ([^ ]+ )?(?i:' + all_arg2_keywords + r'))?|([^ ]+ ){0,2}(?i:' + plural_or_nodet_arg2_keywords + r')|[A-Z][A-Z]+|([A-Z][a-z]+ )+) (shall|may|must) ', input_sentence)
        subj_match_str = str(subj_match.group(1)) if subj_match else ''
        when_clause_subject = re.sub(r'^(an?|the|this|that|their|its|one|any( such( an?)?)?|such( an?)?) (?![A-Z][A-Z])', 'this ', subj_match_str, re.I).strip()
        when_clause_subject = re.sub(r'^(an?|one|any( such( an?)?)?|such( an?)?) ', 'this ', when_clause_subject, re.I).strip()
        if when_clause_subject and looks_like_arg0(when_clause_subject):
            last_known_subject = when_clause_subject

    # print("last_known_subject: " + last_known_subject, file=sys.stderr)


# store the current location in the file
pending_location_types = [['part ','annex '],['title '],['chapter '],['section '],['sub-section '],['article ']]
pending_location_names = list(map(lambda x: '', pending_location_types))
def update_pending_location_names(input_sentence):
    global last_known_subject
    for i, loc_type_names in enumerate(pending_location_types):
        for loc_type in loc_type_names:
            if str(input_sentence[0:len(loc_type)]).lower() == loc_type:
                for j in range(i,len(pending_location_names)):
                    pending_location_names[j] = ''
                pending_location_names[i] = input_sentence
                last_known_subject = '' # reset last known subject every article
def flush_pending_location_names():
    for i, loc_name in enumerate(pending_location_names):
        if len(loc_name) > 0: outfile.write('<h' + str(i+1) + '>' + loc_name + '</h' + str(i+1) + '>\r\n')
        pending_location_names[i] = ''
        

def process_sentence(input_sentence, input_sentence_following_data):
    print('==========================================================')
    print(input_sentence)

    # skip obvious definitions
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
    interesting_verbs = "notify|notifies|notified|notifying|inform|informs|informed|informing|report|reports|reported|reporting|provide|provides|provided|providing|submit|submits|submitted|submitting|demonstrate|demonstrates|demonstrated|demonstrating|prove|proves|proved|proving|communicate|communicates|communicated|communicating|send|sends|sent|sending|issue|issues|issued|issuing|publish|publishes|published|publishing|state|disclose|discloses|disclosed|share|shares|shared|document|documents|documented|review|reviews|reviewed|monitor|monitors|monitored|audit|audits|audited|transmit|transmits|transmitted|collect|collects|collected|fill|fills|filled|analyze|analyzes|analyzed|analyse|analyses|analysed|assess|assesses|assessed|alert|alerts|alerted|gather|gathers|gathered|declare|declares|declared|file|files|filed|deliver|delivers|delivered|supply|supplies|supplied|record|records|recorded|maintain|maintains|maintained|record|recorded|compile|compiled".split('|')
    obligation_verbs = "report|reports|notify|notifies|inform|informs|send|sends|submits|disclose|discloses|alert|alerts".split('|')
    interesting_nouns = "review|audit|disclosure|report|documentation|plan|system|procedure|process|processes|analysis|analyses|assessment|evaluation|This material|This document".split('|')
    obligation_nouns = "review|audit|disclosure|report|documentation".split('|')
    interesting_nouns_valid_verbs_direct = "carry|carried|conduct|conducted|repeat|repeated|perform|performed|produce|produced|implement|implemented|prepare|prepared|subject|subjected|draw|drawn|write|written".split('|')
    interesting_nouns_valid_verbs_subj = "include|included|comprise|comprised|consist|consisted|address|addressed|support|supported|meet|met|specify|specified|capture|captured|incorporate|incorporated|contain|contained|enable|enabled|allow|allowed|make|made".split('|')
    if not(False
        or any((verb in input_sentence) for verb in interesting_verbs)
        or any((noun in input_sentence) for noun in interesting_nouns)
    ): return

    
    #this "if statement" checks the same thing as the previous statement?? AD
    if not(False
        or re.search(r'\b(' + '|'.join(interesting_verbs) + r')\b', input_sentence)
        or re.search(r'\b(' + '|'.join(interesting_nouns) + r')s?\b', input_sentence)
    ): return

    # use the model to make predictions
    try:
        data = srl.predict(
            sentence=input_sentence
        )
    except BaseException as e:
        print("bad day :(\n" + str(e))
        return
        #raise ValueError(input_sentence, e)

    # filter the data to relevant verbs, and apply rules to fix the output
    for verb_data in data['verbs']:
        verb = verb_data['verb']
        srl_output = str(verb_data['description'])

        # do not go further if we don't have a verb (or if the verb is shall)
        if verb == '' or verb == 'shall': continue

        # filter the data to relevant usages of those verbs
        is_relevant_case = False

        # (filter for verbs)
        verb_pos = srl_output.index("[V:") if "[V:" in srl_output else 0
        is_relevant_case = (is_relevant_case or (False
            or (verb in obligation_verbs)
            or (verb in interesting_verbs and (False
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
                    and verb in interesting_nouns_valid_verbs_subj
                    and re.search(r'\[ARG[0-9]: [^\]]*\b(' + '|'.join(interesting_nouns) + r')s?\b', srl_output)
                )
                or (True
                    and verb in interesting_nouns_valid_verbs_direct
                    and re.search(r'\[ARG[1-9]: [^\]]*\b(' + '|'.join(interesting_nouns if is_forgiving_noun_verb else obligation_nouns) + r')s?\b', srl_output)
                )
            )
            and (verb != 'comply' or not(" following " in srl_output))
        ))

        # (abort if none found a match)
        if not(is_relevant_case): continue

        # write pending locations in the file
        flush_pending_location_names()

        srl_html_output = srl_output
        srl_html_output = re.sub(r'>', r'&gt;', srl_html_output)
        srl_html_output = re.sub(r'<', r'&lt;', srl_html_output)
        srl_html_output = re.sub(r'\[([a-zA-Z0-9]+[^\[\]:]*)\]', r'\1', srl_html_output) # fix a weird bug where a span has no tag, for some reason
        srl_html_output = re.sub(r'\[([^ ]+): ', r'<span class="\1">', srl_html_output)
        srl_html_output = re.sub(r'\]', r'</span>', srl_html_output)
        if len(input_sentence_following_data) > 0: srl_html_output = re.sub(r'(<span[^>]*>[^<]* following\b[^<]*)(</span>)', lambda m: m.group(1)+' '+input_sentence_following_data+m.group(2), srl_html_output)
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
                    and (not(verb in interesting_verbs) or re.match("subject to", text_of(arg)))
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

        # deduce obligation frequency from full paragraph
        paragraph_frequence_predictions = nlp(input_sentence)

        # decude obligation frequence from analyzed sentence
        sentence_frequence_predictions = nlp(' '.join(map(lambda arg: text_of(arg), srl_dom_output.getElementsByTagName("span"))))
        
        # deduce obligation frequency from simplified sentence
        argmtmp_sentence = "they shall report it"
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARGM-TMP'.split(',')):
                argmtmp_sentence += ', ' + text_of(arg)
        argmtmp_sentence += '.'
        argmtmp_frequence_predictions = nlp(argmtmp_sentence) if "," in argmtmp_sentence else sentence_frequence_predictions

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

        # now let's mangle the sentence by fixing pronouns as subjects or objects
        # (co-reference resolution)

        # solve cases where we have a "When" clause
        when_clause = None
        when_clause_uppercase = False
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARGM-TMP'.split(',')):
                if re.match(r'^(when|where|if|as soon as) ',text_of(arg), re.IGNORECASE):
                    when_clause = text_of(arg)
                    when_clause_uppercase = when_clause[0].isupper() or (arg.previousSibling == None or arg.previousSibling.previousSibling == None)

        when_clause_subject = ''
        if when_clause:
            subj_match = re.match(r'(?i:(?:when|where|if|as soon as))(?: ?[,][^,.]+[,])? ((an?|the|this|that|their|its|one|two|three|any( such( an?)?)?|such( an?)?|all|every|each) ([^ ]+)( ([^ ]+ )?(?i:' + all_arg2_keywords + r'))?|([^ ]+ ){0,2}(?i:' + plural_or_nodet_arg2_keywords + r')|[A-Z][A-Z]+|([A-Z][a-z]+ )+)', when_clause)
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
        if last_known_subject:
            for arg in srl_dom_output.getElementsByTagName("span"):
                if match_class_in_list(arg, 'ARG0'.split(',')):
                    if (False
                        or (text_of(arg).lower() == 'it')
                        or (text_of(arg).lower() == 'they')
                    ):
                        current_last_known_subject = last_known_subject
                        if text_of(arg).lower() == 'they': current_last_known_subject = re.sub(r'^this ', 'these ', last_known_subject)
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


        #print(srl_dom_output.lastChild.toxml())
        outfile.write(srl_dom_output.lastChild.toxml()+'\r\n')

        # print the results
        print('==========================================================')

        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG0'.split(',')):
                print("SUBJ: " + text_of(arg).lower())
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'V'.split(',')):
                print("VERB: " + text_of(arg).lower())
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG1,C-ARG1'.split(',')):
                print("DATA: " + text_of(arg).lower())
        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARG2'.split(',')):
                print("DEST: " + text_of(arg).lower())

        if cat3_pred >= 0.75:
            print('FREQ: very likely recurring')
        elif cat3_pred > cat1_pred and cat3_pred > cat2_pred:
            print('FREQ: likely recurring')
        elif cat3_pred >= 0.15:
            print('FREQ: maybe recurring')

        if cat2_pred >= 0.75:
            print('FREQ: very likely reoccurring')
        elif cat2_pred > cat1_pred and cat2_pred > cat3_pred:
            print('FREQ: likely reoccurring')
        elif cat2_pred >= 0.15:
            print('FREQ: maybe reoccurring')

        if cat1_pred >= 0.75:
            print('FREQ: very likely happening once')
        elif cat1_pred > cat2_pred and cat1_pred > cat3_pred:
            print('FREQ: likely happening once')
        elif cat1_pred >= 0.15:
            print('FREQ: maybe happening once')

        for arg in srl_dom_output.getElementsByTagName("span"):
            if match_class_in_list(arg, 'ARGM-TMP'.split(',')):
                print("::::: ARGM-TMP: " + text_of(arg).lower())

        for arg in srl_dom_output.getElementsByTagName("span"):
            if not(match_class_in_list(arg, 'V,ARG0,ARG1,ARG2,ARGM-TMP,C-ARG1'.split(','))):
                if match_class_in_list(arg, 'ARGM-MOD') and text_of(arg) == 'shall': continue
                print("::::: " + arg.getAttribute("class") + ": " + text_of(arg).lower())

        #print(
        #    "( "+str(int(1000*cat1_pred)/100)+" | "+str(int(1000*cat2_pred)/100)+" | "+str(int(1000*cat3_pred)/100)+" )"
        #)

# iterate over the input sentences
print("Running on the input sentences...")
for input_sentence in input_sentences:
    input_sentence = input_sentence.rstrip('\r\n')
    input_sentence_following_data = re.sub(r'(^[^❮]+|[^❯]+$)',r'',input_sentence)  #finds everything between " ❮ ❯ "
    if len(input_sentence_following_data) > 0: input_sentence = input_sentence.replace(input_sentence_following_data, '', 1)  #remove everything inside " ❮ ❯ " from the string
    
    update_pending_location_names(input_sentence)
    #keep track of  ['part ','annex '],['title '],['chapter '],['section '],['sub-section '],['article '], and save sentence to corresponding location in python list pending_location_names

    update_last_known_subject(input_sentence)
    
    process_sentence(input_sentence, input_sentence_following_data)

    if " shall " in input_sentence_following_data:
        input_sub_sentences = re.sub(r' ‖ and/or ', r' and/or ', input_sentence_following_data).lstrip('❮').rstrip('❯').split(' ‖ ')
        for input_sub_sentence in input_sub_sentences:
            process_sentence(input_sub_sentence, '')
        
    # flush at the end of every sentence
    outfile.flush()

print('==========================================================')
outfile.close()