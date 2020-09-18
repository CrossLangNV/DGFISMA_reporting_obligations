import pytest
import pickle
import json
import base64

from tests.fixtures import *

from src.transform import ListTransformer, get_other_lines, transform_lines, fold_sublist
from src.utils import SeekableIterator

from cassis.typesystem import load_typesystem
from cassis.xmi import load_cas_from_xmi

#test the main class: ReportingObligationsFinder

@pytest.mark.parametrize("get_path_json, get_path_sofa, get_path_typesystem", [
                       ("small_nested_tables_response.json", "small_nested_tables.txt", "typesystem.xml" ), 
                       ("minus_lesser_of_response.json", "minus_lesser_of.txt", "typesystem.xml" ) ,
                       ("doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767_response.json", "doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767.txt", "typesystem.xml" ) ,
                       ("double_nested_list_response.json", "double_nested_list.txt", "typesystem.xml" ) ],  
                         indirect=["get_path_json", "get_path_sofa", "get_path_typesystem"  ])
def test_reporting_obligations_finder( get_path_json, get_path_sofa, get_path_typesystem ): 
    
    with open( get_path_typesystem , 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open( get_path_json ) as json_file:
        response = json.load(json_file)
        
    decoded_cas=base64.b64decode( response[ 'cas_content' ] ).decode( 'utf-8' )

    cas=load_cas_from_xmi( decoded_cas, typesystem=typesystem  )
    
    #first check if nothing wrong with the ListTransformer class:
    
    transformer=ListTransformer( cas )
    
    transformer.add_reporting_obligation_view( OldSofaID = 'html2textView', NewSofaID = 'ListView' )
    
    sofa_reporting_obligations=cas.get_view( "ListView" ).sofa_string
    
    sofa_reporting_obligations_ok=open( get_path_sofa , 'r'   ).read()
    
    assert sofa_reporting_obligations == sofa_reporting_obligations_ok
    
    #next check if ReportingObligationsFinder is ok:
    
    #TODO:
    
    #reporting_obligations_finder = ReportingObligationsFinder( cas, ALLEN_NLP_PATH, SPACY_PATH )
    #list_xml=reporting_obligations_finder.process_sentences( ListSofaID='ListView'  )
    #reporting_obligations_finder.add_xml_to_cas( list_xml, ROSofaID='ReportingObligationsView' )
    
    