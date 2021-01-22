#!/usr/local/bin/python
from flask import Flask
from flask import request
from flask import abort

import binascii
import base64

from cassis.typesystem import load_typesystem
from cassis.xmi import load_cas_from_xmi

from allennlp.predictors.predictor import Predictor
import spacy

from src.transform import ListTransformer
from src.reporting_obligations import ReportingObligationsFinder

app = Flask(__name__)
   
BERT_PATH="/work/models/bert_models/bert-base.tar.gz"
SPACY_PATH="/work/models/spacy_models/spacy-textcat"
TEMPLATE_PATH="/work/templates/out.html.template"    
TYPESYSTEM_PATH="/work/typesystems/typesystem.xml"

GPU=0  #0,1,...-1(CPU)
reporting_obligations_finder = ReportingObligationsFinder(  BERT_PATH, SPACY_PATH, GPU  )
 
@app.route('/add_reporting_obligations', methods=['POST'])
def add_reporting_obligations():    
    if not request.json:
        abort(400) 
    output_json={}
    
    if ('cas_content' not in request.json) or ( 'content_type' not in request.json ):
        print( "'cas_content' and/or 'content type' field missing" )
        output_json['cas_content']=''
        output_json['content_type']=''
        return output_json
        
    try:
        decoded_cas_content=base64.b64decode( request.json[ 'cas_content' ] ).decode( 'utf-8' )
    except binascii.Error:
        print( f"could not decode the 'cas_content' field. Make sure it is in base64 encoding." )
        output_json['cas_content']=''
        output_json['content_type']=request.json[ 'content_type' ]
        return output_json

    with open( TYPESYSTEM_PATH , 'rb') as f:
        typesystem = load_typesystem(f)

    #load the cas:
    cas=load_cas_from_xmi( decoded_cas_content, typesystem=typesystem  )

    if request.json[ 'content_type'] == 'pdf' or request.json[ 'content_type'] == 'html' or request.json[ 'content_type'] == 'xhtml':

        #List processing and add to cas:
        
        transformer=ListTransformer( cas )
        transformer.add_list_view( OldSofaID='html2textView', NewSofaID = 'ListView' )

        #Find reporting obligations and add to cas:
        
        reporting_obligations_finder.process_sentences( cas, ListSofaID='ListView'  )
        reporting_obligations_finder.add_xml_to_cas( cas, TEMPLATE_PATH, ROSofaID='ReportingObligationsView' )
                
    else:
        print( f"content type { request.json[ 'content_type'] } not supported by paragraph annotation app" )   
        output_json['cas_content']=request.json['cas_content']
        output_json['content_type']=request.json[ 'content_type' ]
        return output_json   
    
    #.decode() because json can't serialize a bytes type object.
    output_json['cas_content']=base64.b64encode(  bytes( cas.to_xmi()  , 'utf-8' ) ).decode()   
    output_json[ 'content_type']=request.json[ 'content_type']
        
    return output_json
    
@app.route('/')
def index():
    return "Up and running"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True, threaded=False, use_reloader=False)