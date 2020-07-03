To use this project:

1. clone this repository
2. install dependencies 'torch' (1.4.0), 'spacy' (2.1.9), 'allennlp' (0.9.0)
3. follow the instructions below to download the models

When this is done, you need to download the models:

1. download `bert-base-srl-2019.06.17.tar.gz` from the latest github release
2. download `spacy-textcat.zip` from the latest github release
3. unzip `spacy-textcat.zip` (you should have a `sapcy-textcat` folder as a result)
4. execute `python extract-relation-info.py celex-32013R0575-1.txt.flat-lists.txt`

If you want to execute on a different file:

1. download the text version of the eur-lex law, save it as a text file
2. reformat the text file to match the space conventions found in `celex-32013R0575-1.txt`
3. execute `python process-article-lists.py <yourfile>.txt`
4. execute `python extract-relation-info.py <yourfile>.txt.flat-lists.txt`

This program generates two outputs

1. an html file, which is human-friendly
2. a console outut, which outputs for every line the found relation-sentences and their categorization

It's probably wise to add code to output a json or another format which can easily be imported in a database