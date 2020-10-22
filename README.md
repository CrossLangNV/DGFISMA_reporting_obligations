To use this project:

1. clone this repository
2. install dependencies 'torch' (1.4.0), 'spacy' (2.1.9), 'allennlp' (0.9.0)
3. follow the instructions below to download the models

When this is done, you need to download the models:

1. download `bert-base-srl-2019.06.17.tar.gz` from the latest github release
2. download `spacy-textcat.zip` from the latest github release
3. unzip `spacy-textcat.zip` (you should have a `sapcy-textcat` folder as a result)
4. execute `python extract-relation-info.py celex-32013R0575-1.txt.flat-lists.txt`

If you want to execute on a different file:

1. download the text version of the eur-lex law, save it as a text file
2. reformat the text file to match the space conventions found in `celex-32013R0575-1.txt`
3. execute `python process-article-lists.py <yourfile>.txt`
4. execute `python extract-relation-info.py <yourfile>.txt.flat-lists.txt`

This program generates two outputs

1. an html file, which is human-friendly
2. a console outut, which outputs for every line the found relation-sentences and their categorization

It's probably wise to add code to output a json or another format which can easily be imported in a database

----------------------------------

The output of the SRL is formatted as a <a href="https://www.aclweb.org/anthology/J05-1004.pdf">PropBank frameset</a>, but has adopted unified conventions accross possible verbs.

Here is a description of the "reporting obligation" frameset developed for this project:

- `ARG0`: who needs to report
- `ARG1`: what needs to be reported
- `ARG2`: to who do we need to report it
- `ARG3`: details about what needs to be reported

In addition to that, modifier arguments follow the general Propbank conventions:

- `ARGM-TMP`: time
- `ARGM-LOC`: location
- `ARGM-CAU`: cause
- `ARGM-EXT`: extent
- `ARGM-MNR`: manner
- `ARGM-PNC`: purpose
- `ARGM-ADV`: general purpose
- `ARGM-DIR`: direction
- `ARGM-NEG`: negation marker
- `ARGM-MOD`: modal verb
- `ARGM-DIS`: discourse connectives

----------------------------------

IMPORTANT UPDATES PLANNED:

- In addition to the raw text for source, content, and destination: a list of terms from a linked entity glossary would be linked
- These would come from an embedding space; and the distance between all pairs of token (with distance <= 0.6) would be precomputed and stored in a database, see below

Here is a proposed database schema to handle the reporting obligation in its final form

- `LawParagraph`: ID, TEXT_OF_PARAGRAPH (String), TITLE_SECTION (String), TITLE_PART (String), TITLE_DOC (String), SOURCE_DOCUMENT (see Document database)
- `ObligationTerm`: ID, MAIN_TEXT (String), POSSIBLE_TEXTS (Array of String)
- `ObligationTermsDistance`: ObligationTerm1.ID, ObligationTerm2.ID, Distance (between 0.0 and 1.0)
- `Obligation`: ID, OBLIGATION_PARA (LawParagraph), OBLIGATION_SOURCE (ObligationTerm), OBLIGATION_SOURCE_TEXT (String), OBLIGATION_CONTENTS (Array of ObligationTerms), OBLIGATION_CONTENTS_TEXT (String), OBLIGATION_DESTINATION (ObligationTerm), OBLIGATION_DESTINATION_TEXT (String), OBLIGATION_RECURRENCE (Likely/Possible/Unlikely), OBLIGATION_REOCCURRENCE (Likely/Possible/Unlikely), OBLIGATION_FREQUENCY_TEXT (String)

Then, search would work this way:

- Three text boxes (Source, Content, Destination) where users can type a list of ObligationTerms (with auto-completion)
- For each text box, an acceptable distance is selected (by default: 0.15; options: 0.00; 0.15; 0.25; 0.40; 0.50; 0.60)
- For each text box, a list of acceptable ObligationTerms is computed (all terms whose distance with one of the terms listed in the box is smaller than the acceptable distance)
- Then all obligations which contain one of the acceptable terms in the correct field are returned.
- These can then be reranked based on a distance score, if desired, but other orders are possible (date of source document, etc...)
