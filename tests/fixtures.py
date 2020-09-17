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
    return os.path.join( FIXTURE_DIR , "sofa_reporting_obligations", request.param )