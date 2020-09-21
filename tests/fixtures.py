import os

import pytest

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_files")
    
@pytest.fixture(scope='function')
def get_path_json( request ):
    return os.path.join( FIXTURE_DIR , "response_json_paragraph_annotations", request.param )

@pytest.fixture(scope='function')
def get_path_typesystem( request ):
    return os.path.join( FIXTURE_DIR , "typesystems", request.param )

@pytest.fixture(scope='function')
def get_path_pickle( request ):
    return os.path.join( FIXTURE_DIR , "pickle", request.param )

@pytest.fixture(scope='function')
def get_path_sofa( request ):
    return os.path.join( FIXTURE_DIR , "sofa_listview", request.param )

@pytest.fixture(scope='function')
def get_path_bert_model( request ):
    return os.path.join( FIXTURE_DIR , "models", 'bert_model' , request.param )

@pytest.fixture(scope='function')
def get_path_spacy_model( request ):
    return os.path.join( FIXTURE_DIR , "models", 'spacy_model' , request.param )

@pytest.fixture(scope='function')
def get_path_output_ro( request ):
    return os.path.join( FIXTURE_DIR , "output_reporting_obligations" , request.param )

@pytest.fixture(scope='function')
def get_path_template( request ):
    return os.path.join( FIXTURE_DIR , "templates" , request.param )