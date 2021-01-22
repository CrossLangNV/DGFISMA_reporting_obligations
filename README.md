Instructions
------------

use "dbuild.sh" to build the docker image <br />
use "dcli.sh" to start a docker container

Don't forget to:

1) download BERT model `bert-base-srl-2019.06.17.tar.gz` from the latest github release

2) download `spacy-textcat.zip` from the latest github release

3) Set the path to the directory where the BERT/SPACY model is located in: https://github.com/CrossLangNV/DGFISMA_reporting_obligations/blob/dev/dbuild.sh 

4) Set the path to the correct template (template provided here: <em>tests/test_files/templates/out.html.template</em>) in `dbuild.sh`.

5) Set the path to the correct typesystem (provided: <em>tests/test_files/typesystems/typesystem.xml</em>) in `dbuild.sh`.

If the docker was successfully built, and is running, a POST request with a json having a "cas_content" and a "content_type" can be made to <em>{localhost:5004}/add_reporting_obligations/</em>.
The "cas_content" is a UIMA CAS object, encoded in base64, the "content_type" can be "html" or "pdf".

Note that before sending to the Reporting Obligations API, the json should have been POSTed to the API for paragraph detection (https://github.com/CrossLangNV/DGFISMA_paragraph_detection), because the algorithm for detection and processing of reporting obligations relies on annotations/views added to the CAS by this API call. 

Given a json with a "cas_content" and a "content_type" field (see <em>tests/test_files/response_json_paragraph_annotations</em> for examples), the POST request to <em>{localhost:5004}/add_reporting_obligations/</em> will return a json with the same fields, but now the base64 encoded CAS object available via the "cas_content" field will contain a `ReportingObligationsView`. 

## Algorithms

This code repository aims to solve two tasks:

1) Processing of paragraph annotations ( `de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Paragraph` ) added by the paragraph annotation API.

2) Detection and analysis of reporting obligations.


### Processing of paragraph annotations

Processing of paragraph annotations (i.e. detected enumerations) is implemented via the `ListTransformer` class. The class allows adding of a `ListView` containing sentence segments fit for analysis by the `ReportingObligationsFinder` class. I.e. given a CAS, running following commands from a Python interpreter will add a `ListView` to the CAS:

```
from src.transform import ListTransformer
transformer=ListTransformer(CAS)
transformer.add_list_view( OldSofaID='html2textView', NewSofaID = 'ListView'  )
```

### Detection and analysis of reporting obligations

Given a CAS with a `ListView`, a `ReportingObligationsView` can be added running the following commands from a Python interpreter:

```
reporting_obligations_finder = ReportingObligationsFinder( ALLEN_NLP_SRL_PATH, SPACY_PATH  ) \
reporting_obligations_finder.process_sentences(CAS, ListSofaID='ListView'  ) \
reporting_obligations_finder.add_xml_to_cas( CAS, TEMPLATE_PATH, ROSofaID='ReportingObligationsView' ) \
```

With ALLEN_NLP_SRL_PATH, SPACY_PATH, TEMPLATE_PATH the paths to the AllenNLP/Spacy model and the html-template, repectively. 

Running `reporting_obligations_finder.print_to_html(  TEMPLATE_PATH, OUTPUT_PATH )` will print the analyzed reporting obligations to a human "readable" html file (i.e. OUTPUT_PATH). 


### Unit tests

Unit tests (type pytest in command line from this directory) will pass when using bert and spacy models from first github release.
https://github.com/CrossLangNV/DGFISMA_reporting_obligations/releases/tag/v1.0

