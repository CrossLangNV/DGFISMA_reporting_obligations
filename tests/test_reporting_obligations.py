import pytest
import pickle
import json
import base64

from tests.fixtures import *

from src.transform import ListTransformer
from src.reporting_obligations import ReportingObligationsFinder
from src.utils import SeekableIterator

from cassis.typesystem import load_typesystem
from cassis.xmi import load_cas_from_xmi

#test the main class: ReportingObligationsFinder

@pytest.mark.parametrize("get_path_json, get_path_sofa, get_path_output_ro, get_path_bert_model, get_path_spacy_model, get_path_template , get_path_typesystem", [
                       ("small_nested_tables_response.json", "small_nested_tables.txt", "small_nested_tables.html",
                        "bert-base-srl-2019.06.17.tar.gz" , "spacy-textcat", "out.html.template", "typesystem.xml" ), 
                       ("minus_lesser_of_response.json", "minus_lesser_of.txt", "minus_lesser_of.html",
                        "bert-base-srl-2019.06.17.tar.gz" , "spacy-textcat", "out.html.template", "typesystem.xml" ),
                       ("doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767_response.json", "doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767.txt",
                        "doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767.html", "bert-base-srl-2019.06.17.tar.gz" , "spacy-textcat", "out.html.template" ,"typesystem.xml" ),
                       ("double_nested_list_response.json", "double_nested_list.txt", "double_nested_list.html",
                        "bert-base-srl-2019.06.17.tar.gz" , "spacy-textcat", "out.html.template", "typesystem.xml" )],  
                         indirect=["get_path_json", "get_path_sofa", "get_path_output_ro", "get_path_bert_model", "get_path_spacy_model",
                                   "get_path_template", "get_path_typesystem"  ])
def test_reporting_obligations_finder( get_path_json, get_path_sofa, get_path_output_ro, get_path_bert_model, get_path_spacy_model, get_path_template , get_path_typesystem ): 
    
    with open( get_path_typesystem , 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open( get_path_json ) as json_file:
        response = json.load(json_file)
        
    decoded_cas=base64.b64decode( response[ 'cas_content' ] ).decode( 'utf-8' )

    cas=load_cas_from_xmi( decoded_cas, typesystem=typesystem  )
    
    #first check if nothing wrong with the ListTransformer class:
    
    transformer=ListTransformer( cas )
    
    transformer.add_list_view( OldSofaID = 'html2textView', NewSofaID = 'ListView' )
    
    sofa_listview=cas.get_view( "ListView" ).sofa_string
    
    sofa_listview_ok=open( get_path_sofa , 'r'   ).read()
    
    assert sofa_listview == sofa_listview_ok
    
    #next check if ReportingObligationsFinder class is ok:
        
    reporting_obligations_finder = ReportingObligationsFinder( cas, get_path_bert_model , get_path_spacy_model )
    reporting_obligations_finder.process_sentences( ListSofaID='ListView'  )
    reporting_obligations_finder.add_xml_to_cas( get_path_template , ROSofaID='ReportingObligationsView' )
    
    
    sofa_reporting_obligations=cas.get_view( "ReportingObligationsView" ).sofa_string
    
    sofa_reporting_obligations_ok=open( get_path_output_ro, 'r' ).read()
    
    assert sofa_reporting_obligations == sofa_reporting_obligations_ok
    
    