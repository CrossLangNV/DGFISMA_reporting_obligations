Instructions
------------

use "dbuild.sh" to build the docker image <br />
use "dcli.sh" to start a docker container

Don't forget to:

1) download BERT model `bert-base-srl-2019.06.17.tar.gz` from the latest github release

2) download `spacy-textcat.zip` from the latest github release

3) Set the path to the directory where the BERT/SPACY model is located in: https://github.com/CrossLangNV/DGFISMA_reporting_obligations/blob/dev/dbuild.sh 

4) Set the path to the correct template (template provided here: tests/test_files/templates/out.html.template) in dbuild.sh ( e.g. https://github.com/CrossLangNV/DGFISMA_definition_extraction/blob/master/dbuild.sh )

5) Set the path to the correct typesystem (provided: tests/test_files/typesystems/typesystem.xml) in dbuild.sh ( e.g. https://github.com/CrossLangNV/DGFISMA_definition_extraction/blob/master/dbuild.sh )


Given a json with a *cas_content* (UIMA cas object encoded in base64) and *content_type* field (see tests/test_files/response_json_paragraph_annotations for examples), the POST request to */add_reporting_obligations* will return a json with the same fields, but now the *cas* object in *cas_content* will contain a *ReportingObligationsView*. See below for more details.


See notebooks/test_transform_RO.ipynb, for an example on how to use the code. Basically, given a Cas object (cas) with paragraph annotations (obtained using https://github.com/CrossLangNV/DGFISMA_paragraph_detection) one should do the following:

*from src.transform import ListTransformer \
from src.reporting_obligations import ReportingObligationsFinder \
transformer=ListTransformer( cas ) \
transformer.add_list_view( OldSofaID='html2textView', NewSofaID = 'ListView'  ) \
reporting_obligations_finder = ReportingObligationsFinder( cas, BERT_PATH, SPACY_PATH  ) \
reporting_obligations_finder.process_sentences( ListSofaID='ListView'  ) \
reporting_obligations_finder.add_xml_to_cas( TEMPLATE_PATH, ROSofaID='ReportingObligationsView' ) \
reporting_obligations_finder.print_to_html(  TEMPLATE_PATH, OUTPUT_PATH )*


*transform.py* is a refactoring of *process-article-lists.py*, but now it uses paragraph annotations in the cas, obtained via https://github.com/CrossLangNV/DGFISMA_paragraph_detection for transformation of sentences/lists/sublists. The OldSofaID should contain these paragraph annotations. The ListTransformer will add a *ListView* to the cas, see *tests/test_files/sofa_listview* for examples. 

*reporting_obligations.py* is a refactoring of *extract-relation-info.py*. It will use the sentences in the *ListView* (ListSofaID).

A human-friendly *.html* file is created (and added to cas via method *.add_xml_to_cas*, or printed to a html file via *.print_to_html*).

Unit tests (type pytest in command line from this directory) will pass when using bert and spacy models from first github release.
https://github.com/CrossLangNV/DGFISMA_reporting_obligations/releases/tag/v1.0

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