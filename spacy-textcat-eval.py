import spacy
from spacy.util import minibatch
import random
import torch
import time
import copy

LABELS = [ "1", "2", "3" ]
CATS = [
    {"cats": { "1": 0.5, "2": 0.5, "3": 0.0 }},
    {"cats": { "1": 1.0, "2": 0.0, "3": 0.0 }},
    {"cats": { "1": 0.0, "2": 1.0, "3": 0.0 }},
    {"cats": { "1": 0.0, "2": 0.0, "3": 1.0 }}
]

print("====================================================================")
print("loading the data...")
print("")

TEST_DATA = [
    ("In accordance with Article 16 of Regulation ( EU ) No 1093/2010 EBA shall provide advice to the Commission by 31 December 2017 on whether a binding technical standard is required", CATS[1]),
    ("Institutions shall provide senior management and the appropriate committee of the management body with regular reports on both Specific and General Wrong - Way risks and the steps being taken to manage those risks.", CATS[3]),
    ("An institution shall demonstrate to the satisfaction of the competent authority , at least quarterly , that the stress period used for the calculation under this paragraph coincides with a period of increased credit default swap or other credit ( such as loan or corporate bond ) spreads for a representative selection of its counterparties with traded credit spreads", CATS[3]),
    ("The institutions shall notify to the competent authorities the use they make of paragraph 1", CATS[2]),
    ("The institution shall report at least quarterly to the competent authorities the results , including comparisons with the institution 's own funds requirement in accordance with this Article", CATS[3]),
    ("EBA shall report to the Commission annually on measures taken by the competent authorities in order to ensure the compliance with the requirements of Titles II and III by institutions", CATS[3]),
    ("every time it snows, we report a snowman", CATS[2]),
    ("every time it snowed, we reported a snowman", CATS[2]),
    ("when it snowed, we reported a snowman", CATS[1]),
    ("when, finally, it snowed, we reported a snowman", CATS[1]),
    ("by Friday, we reported a snowman", CATS[1]),
    ("on Friday, we reported a snowman", CATS[1]),
    ("on Friday, we often reported a snowman", CATS[2]),
    ("every Friday, we reported a snowman", CATS[3]),
    ("this Friday, we reported a snowman", CATS[1]),
    ("monthly, we reported a snowman", CATS[3]),
    ("semiyearly, we reported a snowman", CATS[3]),
    ("semimonthly, we reported a snowman", CATS[3]),
    ("trimonthly, we reported a snowman", CATS[3]),
    ("halfquarterly, we reported a snowman", CATS[3]),
    ("half-quarterly, we reported a snowman", CATS[3]),
    ("every other day, we reported a snowman", CATS[3]),
    ("ooops, we reported a snowman", CATS[1]),
    ("we reported a snowman", CATS[1]),
    ("we reported the snowman", CATS[1]),
    ("the Commission shall report on the state of the union by 28 February 2050.",CATS[1]),
    ("as soon as Japan attacked Holland, we reported a snowman", CATS[1]),
    ("when Japan attacked Holland, we reported a snowman", CATS[1]),
    ("whenever Japan attacked Holland, we reported a snowman", CATS[2]),
    ("if Japan attacked Holland, then we reported a snowman", CATS[1]),
    ("when Holland was attacked by another country, we reported a snowman", CATS[1]),
    ("all times when Holland was attacked by another country, we reported a snowman", CATS[2]),
    ("many times when Holland was attacked by another country, we reported a snowman", CATS[2]),
    ("often when Holland was attacked by another country, we reported a snowman", CATS[2]),
    ("every time when Holland was attacked by another country, we reported a snowman", CATS[2]),
    ("when a company meets those conditions, it shall submit a weekly report to us", CATS[2]),
    ("whenever a company meets those conditions, it shall submit a weekly report to us", CATS[2]),
    ("where a company meets those conditions, it shall submit a weekly report to us", CATS[2]),
    ("when the company meets those conditions, it shall submit a weekly report to us", CATS[2]),
    ("when any company meets those conditions, it shall submit a weekly report to us", CATS[2]),
    ("when the law was voted, this was reported to us", CATS[1]),
    ("when the law was voted, this was not reported to us", CATS[1]),
    ("when the war ends, this shall be reported to us", CATS[1]),
    ("when the conflict ends, this shall be reported to us", CATS[1]),
    ("when a conflict ends, this shall be reported to us", CATS[2]),
]

for line in open("./data/argm-tmp-sentences.txt"):
    cat, sen_text = line.split("\t")
    cat = '0' if cat == '?' else cat
    TEST_DATA.append((sen_text.rstrip("\n\r"), CATS[int(cat)]))

nlp = spacy.load("./spacy-textcat")

print("====================================================================")
print("making predictions...")
print("")

for TEXT, CAT in TEST_DATA:
    CAT_ID = str(CATS.index(CAT))
    CAT_ID = '1' if CAT_ID == '0' else CAT_ID
    PREDICTIONS = nlp(TEXT)
    print(PREDICTIONS)
    print(
        '\033[93m' + str(int(PREDICTIONS.cats[CAT_ID] * 100)) + '\033[0m', 
        "( "+str(int(1000*PREDICTIONS.cats["1"])/100)+" | "+str(int(1000*PREDICTIONS.cats["2"])/100)+" | "+str(int(1000*PREDICTIONS.cats["3"])/100)+" )"
    )