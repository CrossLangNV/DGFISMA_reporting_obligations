#FROM ubuntu:18.04
#gpu
FROM nvidia/cuda:10.0-cudnn7-devel-ubuntu18.04

MAINTAINER arne <arnedefauw@gmail.com>

ARG MODEL_DIR

# Install some basic utilities
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    sudo \
    git \
    bzip2 \
    libx11-6 \
 && rm -rf /var/lib/apt/lists/*

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

# Install miniconda to /miniconda
RUN curl -LO http://repo.continuum.io/miniconda/Miniconda3-py37_4.8.2-Linux-x86_64.sh
RUN bash Miniconda3-py37_4.8.2-Linux-x86_64.sh -p /miniconda -b
RUN rm Miniconda3-py37_4.8.2-Linux-x86_64.sh
ENV PATH=/miniconda/bin:${PATH}
RUN conda update -y conda

RUN conda install -y python=3.7.3 && \
conda install flask==1.1.1 && \
#conda install --name base scikit-learn=0.20.0 && \
conda install pandas=1.0.1 && \
conda install pytorch==1.4.0 cudatoolkit=10.0 -c pytorch

#cpu
#conda install pytorch==1.4.0 cpuonly -c pytorch


#Install Cython
RUN apt-get update
RUN apt-get -y install --reinstall build-essential
RUN apt-get -y install gcc
RUN pip install Cython

RUN pip install docutils==0.15.0 spacy==2.1.9 cloudpickle==1.3.0 torchtext==0.5.0 scikit-learn==0.20.0 scipy==1.4.1 allennlp==0.9.0 bs4==0.0.1 dkpro-cassis==0.3.0 pexpect pytest ipython jupyter jupyterlab


#WORKDIR /work
#copy code:
#COPY app.py /work
#COPY cleaning.py /work
#COPY annotate.py /work
#COPY definition.py /work
#COPY bert_classifier/src/models.py /work/bert_classifier/src/


#copy model:
#COPY $MODEL_DIR/*.pth /work/models/model.pth
#COPY $MODEL_DIR/config.json /work/models/
#COPY $MODEL_DIR/special_tokens_map.json /work/models/
#COPY $MODEL_DIR/tokenizer_config.json /work/models/
#COPY $MODEL_DIR/vocab.txt /work/models/

EXPOSE 8888

VOLUME /notebook
WORKDIR /notebook

CMD ["jupyter", "notebook", "--no-browser", "--allow-root", "--ip='0.0.0.0'"]

#CMD python /work/app.py
