nvidia-docker build \
--build-arg BERT_PATH=tests/test_files/models/bert_model/bert-base-srl-2019.06.17.tar.gz \
--build-arg SPACY_PATH=tests/test_files/models/spacy_model/spacy-textcat \
--build-arg TEMPLATE_PATH=tests/test_files/templates/out.html.template \
--build-arg TYPESYSTEM_PATH=tests/test_files/typesystems/typesystem.xml \
-t reporting_obligation_app .

#docker build \
#--build-arg BERT_PATH=tests/test_files/models/bert_model/bert-base-srl-2019.06.17.tar.gz \
#--build-arg SPACY_PATH=tests/test_files/models/spacy_model/spacy-textcat \
#--build-arg TEMPLATE_PATH=tests/test_files/templates/out.html.template \
#--build-arg TYPESYSTEM_PATH=tests/test_files/typesystems/typesystem.xml \
#-t reporting_obligation_app .


#docker build \
#--no-cache \
#--build-arg BERT_PATH=models/bert_model/bert-base-srl-2019.06.17.tar.gz \
#--build-arg SPACY_PATH=models/spacy_model/spacy-textcat \
#--build-arg TEMPLATE_PATH=templates/out.html.template \
#--build-arg TYPESYSTEM_PATH=tests/test_files/typesystems/typesystem.xml \
#-t reporting_obligation_app .
