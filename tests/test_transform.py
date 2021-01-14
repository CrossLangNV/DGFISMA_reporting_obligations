import pytest
import pickle
import json
import base64

from tests.fixtures import *

from src.transform import ListTransformer, get_other_lines, transform_lines, fold_sublist, flatten_offsets
from src.utils import SeekableIterator

from cassis.typesystem import load_typesystem
from cassis.xmi import load_cas_from_xmi

#test the main class: ListTransformer

@pytest.mark.parametrize("get_path_json, get_path_sofa, get_path_typesystem", [
                       ("small_nested_tables_response.json", "small_nested_tables.txt", "typesystem.xml" ), 
                       ("minus_lesser_of_response.json", "minus_lesser_of.txt", "typesystem.xml" ) ,
                       ("doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767_response.json", "doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767.txt", "typesystem.xml" ) ,
                       ("double_nested_list_response.json", "double_nested_list.txt", "typesystem.xml" ) ],  
                         indirect=["get_path_json", "get_path_sofa", "get_path_typesystem"  ])
def test_list_transformer( get_path_json, get_path_sofa, get_path_typesystem ): 
    
    with open( get_path_typesystem , 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open( get_path_json ) as json_file:
        response = json.load(json_file)
        
    decoded_cas=base64.b64decode( response[ 'cas_content' ] ).decode( 'utf-8' )

    cas=load_cas_from_xmi( decoded_cas, typesystem=typesystem  )
    
    transformer=ListTransformer( cas )
    
    transformer.add_list_view( OldSofaID = 'html2textView', NewSofaID = 'ListView' )
    
    sofa_reporting_obligations=cas.get_view( "ListView" ).sofa_string
    
    sofa_reporting_obligations_ok=open( get_path_sofa , 'r'   ).read() 
    
    assert sofa_reporting_obligations == sofa_reporting_obligations_ok

#test helper functions:

@pytest.mark.parametrize("get_path_json, get_path_pickle, get_path_pickle_offsets , get_path_typesystem", [
                       ("small_nested_tables_response.json", "small_nested_tables_nested_lines.p", "small_nested_tables_offsets.p", "typesystem.xml" ), 
                       ("minus_lesser_of_response.json", "minus_lesser_of_nested_lines.p", "minus_lesser_of_offsets.p", "typesystem.xml" ) ,
                       ("doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767_response.json", "doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767_nested_lines.p", "doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767_offsets.p",  "typesystem.xml" ) ,
                       ("double_nested_list_response.json", "double_nested_list_nested_lines.p", "double_nested_list_offsets.p", "typesystem.xml" ) ],  
                         indirect=["get_path_json", "get_path_pickle", "get_path_pickle_offsets" , "get_path_typesystem"  ])
def test_get_other_lines( get_path_json, get_path_pickle, get_path_pickle_offsets, get_path_typesystem ):
        
    with open( get_path_typesystem , 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open( get_path_json ) as json_file:
        response = json.load(json_file)
        
    decoded_cas=base64.b64decode( response[ 'cas_content' ] ).decode( 'utf-8' )

    cas=load_cas_from_xmi( decoded_cas, typesystem=typesystem  )

    value_between_tagtype_generator=cas.get_view( 'html2textView' ).select( "com.crosslang.uimahtmltotext.uima.type.ValueBetweenTagType" )        

    seek_vbtt=SeekableIterator( iter(value_between_tagtype_generator) )

    lines, offsets=get_other_lines( cas , 'html2textView' , seek_vbtt, 'root', paragraph_type= "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Paragraph" )
        
    with open( get_path_pickle , 'rb') as f:
        # read the data as binary data stream
        lines_ok = pickle.load(f)
        
    with open( get_path_pickle_offsets , 'rb') as f:
        # read the data as binary data stream
        offsets_ok = pickle.load(f)
        
    assert len( lines_ok ) == len( lines )
    assert len( offsets_ok ) == len( offsets )
    assert lines_ok == lines
    assert offsets_ok == offsets

    
def test_fold_sublist():
    
    lists_to_test = [[ 'a', 'b' , 'c'  ] , 
    [ [ 'a', 'b' , 'c'  ] ],
    [ 'a', [ 'a', 'b' , 'c' ]  ],
    [ 'a', [ 'a' ]  ],
    [ 'a', 'a'  ],
    [ '1.', 'b' , 'c'  ] ,     #1. removed via clean_line
    [ '1.', '(a) something' , 'c'  ] ,      #(a) in beginning of string also removed
    [ '  1. ', 'something (a)' , [  'd', ['e','f'] ]  , 'c'  ],         
    [ '  1. some ', 'something (a)' , 'c'  ] ]
    outcomes = [ 'a ❬b ‖ and/or c❭',
    '❬a ⟨b ‖ and/or c⟩❭',
    'a ❬a ⟨b ‖ and/or c⟩❭',
    'a ❬a ⟨⟩❭',
    'a ❬a❭',
    '❬b ‖ and/or c❭',
    '❬something ‖ and/or c❭',
    '❬something (a) ‖ and/or d ⟨e ⟨f⟩⟩ ‖ and/or c❭',
    '1. some ❬something (a) ‖ and/or c❭' ]
    
    #sanity check
    assert len(lists_to_test) == len(outcomes)

    for list_to_test, outcome in zip( lists_to_test, outcomes ):
        assert fold_sublist( list_to_test ) == outcome
    
    
@pytest.mark.parametrize("get_path_json, get_path_sofa, get_path_typesystem", [
                       ("small_nested_tables_response.json", "small_nested_tables.txt", "typesystem.xml" ), 
                       ("minus_lesser_of_response.json", "minus_lesser_of.txt", "typesystem.xml" ) ,
                       ("doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767_response.json", "doc_bf4ef384-bd7a-51c8-8f7d-d2f61865d767.txt", "typesystem.xml" ) ,
                       ("double_nested_list_response.json", "double_nested_list.txt", "typesystem.xml" ) ],  
                         indirect=["get_path_json", "get_path_sofa", "get_path_typesystem"  ])
def test_transform_lines( get_path_json, get_path_sofa, get_path_typesystem ):
        
    with open( get_path_typesystem , 'rb') as f:
        typesystem = load_typesystem(f)
        
    with open( get_path_json ) as json_file:
        response = json.load(json_file)
        
    decoded_cas=base64.b64decode( response[ 'cas_content' ] ).decode( 'utf-8' )

    cas=load_cas_from_xmi( decoded_cas, typesystem=typesystem  )

    value_between_tagtype_generator=cas.get_view( 'html2textView' ).select( "com.crosslang.uimahtmltotext.uima.type.ValueBetweenTagType" )       

    seek_vbtt=SeekableIterator( iter(value_between_tagtype_generator) )

    lines, offsets=get_other_lines( cas , 'html2textView' , seek_vbtt, 'root', paragraph_type= "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Paragraph" )
        
    flatten_offsets( offsets )
    
    assert len( lines ) == len( offsets )
    
    transformed_lines, transformed_lines_offsets=transform_lines( lines, offsets )

    assert len( transformed_lines ) == len( transformed_lines_offsets )

    lines_offsets=[]
    for line, offset in zip( transformed_lines, transformed_lines_offsets  ):
        lines_offsets.append(line + "|" + str( offset ))
        
    sofa_reporting_obligations="\n".join( lines_offsets )
        
    sofa_reporting_obligations_ok=open( get_path_sofa , 'r'   ).read()
   
    assert sofa_reporting_obligations_ok == sofa_reporting_obligations
    
