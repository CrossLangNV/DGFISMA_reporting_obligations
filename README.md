
To use this project:

1. clone this repository
2. install dependencies 'torch' (1.4.0), 'spacy' (2.1.9), 'allennlp' (0.9.0). A dockerfile is also provided.
3. follow the instructions below to download the models

When this is done, you need to download the models:

1. download `bert-base-srl-2019.06.17.tar.gz` from the latest github release
2. download `spacy-textcat.zip` from the latest github release
3. unzip `spacy-textcat.zip` (you should have a `sapcy-textcat` folder as a result)

See notebooks/test_transform_RO.ipynb, for an example on how to use the code. Basically, given a Cas object (cas) with paragraph annotations one should do the following:

*from src.transform import ListTransformer \
from src.reporting_obligations import ReportingObligationsFinder \
transformer=ListTransformer( cas )
transformer.add_reporting_obligation_view( OldSofaID='html2textView', NewSofaID = 'ReportingObligationView'  )
sentences=cas.get_view( "ReportingObligationView" ).sofa_string
reporting_obligations_finder = ReportingObligationsFinder( sentences = sentences.split( "\n" ) )
list_xml=reporting_obligations_finder.process_sentences( ALLEN_NLP_PATH, SPACY_PATH )
reporting_obligations_finder.print_to_html( list_xml, TEMPLATE_PATH, OUTPUT_PATH )*

*transform.py* is a refactoring of *process-article-lists.py*, but now it uses paragraph annotations in the cas, obtained via https://github.com/CrossLangNV/DGFISMA_paragraph_detection for transformation of sentences/lists/sublists.

*reporting_obligations.py* is a refactoring of *extract-relation-info.py*.

A human-friendly *.html* file is created.

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