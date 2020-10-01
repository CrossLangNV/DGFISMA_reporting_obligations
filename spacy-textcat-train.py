import spacy
from spacy.util import minibatch
import random
import torch
import time
import copy
import re

USE_TRF = False

MAX_EPOCHS = 2 if USE_TRF else 5
BATCH_SIZE = 8
BASE_MODEL = "en_trf_bertbaseuncased_lg" if USE_TRF else "en_vectors_web_lg"
TEXTCAT_PIPENAME = "trf_textcat" if USE_TRF else "textcat"
MODEL_SAVEPATH = "./bert-textcat" if USE_TRF else "./spacy-textcat"

LABELS = [ "1", "2", "3" ]
CATS = [
    {"cats": { "1": 0.5, "2": 0.5, "3": 0.0 }}, #0, mix 1+2
    {"cats": { "1": 1.0, "2": 0.0, "3": 0.0 }},
    {"cats": { "1": 0.0, "2": 1.0, "3": 0.0 }},
    {"cats": { "1": 0.0, "2": 0.0, "3": 1.0 }},
    {"cats": { "1": 0.0, "2": 0.5, "3": 0.5 }}, #4, mix 2+3
]

TRAIN_DATA = [
#    ("when it rains, we try not to get outside", CATS[2]),
#    ("when it rained, we tried not to get outside", CATS[2]),
#    ("when it rained, we tried to get outside daily", CATS[3]),
#    ("when it finally rained, we tried to get outside", CATS[1]),
#    ("when it finally rained, we tried not to get outside", CATS[1]),
#    ("each time it finally rained, we tried not to get outside", CATS[2]),
#    ("after it starts raining, we shall try to get outside", CATS[1]),
#    ("before it starts raining, we shall try to get outside", CATS[1]),
#    ("by tomorrow, we shall try to get outside", CATS[1]),
#    ("today, we shall try to get outside", CATS[1]),
#    ("as of today, we shall try to get outside once every year", CATS[3]),
#    ("as soon as we have found the exit, we shall try to get outside", CATS[1]),
#    ("as soon as we have found the exit, we shall try to get outside twice a month", CATS[3]),
#    ("by 31 december 2018, we shall try to get outside", CATS[1]),
#    ("by 31 december 2018, we shall try to get outside every week", CATS[3]),
]

print("====================================================================")
print("loading the data...")
print("")

for line in open("./data/argm-tmp.txt"):
    a, b, c, when_text = line.split("\t")
    when_text = when_text.rstrip("\n\r")

    # FUTURE
    when_cat = CATS[0] if c == '?' else CATS[int(c)]
    TRAIN_DATA.append(("it shall be reported " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", it shall be reported.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("they shall report it " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", they shall report it.", copy.deepcopy(when_cat)))

    # FUTURE (different formulation)
    TRAIN_DATA.append(("that shall be reported " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", that shall be reported.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("institutions shall report that " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", institutions shall report that.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("we shall report that " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", we shall report that.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("they shall report it, " + when_text + ' .', copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("they shall " + when_text + ' report it .', copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("they shall , " + when_text + ' , report it .', copy.deepcopy(when_cat)))

    # FUTURE (extra long sentences)
    TRAIN_DATA.append(("the organizations affected by the issue shall friendly report to their management, " + when_text + ', the state of their investment positions .', copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("the units which seem relevant shall diligently be reported, " + when_text + ', to the managers of those units .', copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("the EPA shall report the investement level which would be considered reasonable " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", the EPA shall report the investement level which would be considered reasonable.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("the Commission shall submit a report on whether the current rules are satisfying " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", the Commission shall submit a report on whether the current rules are satisfying.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("rigorously, " + when_text + ', the various tribes shall send a report on their population estimates .', copy.deepcopy(when_cat)))

    # FUTURE (data augmentation)
    if c != '3':
        TRAIN_DATA.append((when_text + ", it shall usually be reported.", copy.deepcopy(CATS[2])))
        TRAIN_DATA.append((when_text + ", it shall be reported daily.", copy.deepcopy(CATS[3])))
        TRAIN_DATA.append((when_text + ", it shall be reported once, the first time.", copy.deepcopy(CATS[1])))
        TRAIN_DATA.append((when_text + ", they shall usually report it.", copy.deepcopy(CATS[2])))
        TRAIN_DATA.append((when_text + ", they shall report it daily.", copy.deepcopy(CATS[3])))
        TRAIN_DATA.append((when_text + ", they shall report it once, the first time.", copy.deepcopy(CATS[1])))
    else:
        TRAIN_DATA.append(("when these requirements are met, they shall report to the authorities " + when_text + '.', copy.deepcopy(CATS[4])))
        TRAIN_DATA.append(("when a company meets those requirements, it shall be reported " + when_text + '.', copy.deepcopy(CATS[4])))
        TRAIN_DATA.append(("where the situation has to be monitored more closely, new cases shall be reported " + when_text + '.', copy.deepcopy(CATS[4])))

    # FUTURE (data augmentation 2)
    if c != '3':
        TRAIN_DATA.append(("often, that shall be reported, "+when_text, copy.deepcopy(CATS[2])))
        TRAIN_DATA.append(("annually, that shall be reported, "+when_text, copy.deepcopy(CATS[3])))
        TRAIN_DATA.append(("that shall be reported this one time, "+when_text, copy.deepcopy(CATS[1])))
        TRAIN_DATA.append(("we often shall report that, "+when_text, copy.deepcopy(CATS[2])))
        TRAIN_DATA.append(("we shall report annually about it, "+when_text, copy.deepcopy(CATS[3])))
        TRAIN_DATA.append(("we shall report once about it, "+when_text, copy.deepcopy(CATS[1])))

    # PAST
    when_cat = CATS[0] if b == '?' else CATS[int(b)]
    TRAIN_DATA.append(("it was reported " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", it was reported.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("they reported it " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", they reported it.", copy.deepcopy(when_cat)))

    # PAST (different formulation)
    TRAIN_DATA.append(("that was reported " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", that was reported.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("institutions reported that " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", institutions reported that.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("we reported that " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", we reported that.", copy.deepcopy(when_cat)))

    # PRESENT
    when_cat = CATS[0] if a == '?' else CATS[int(a)]
    TRAIN_DATA.append(("it is reported " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", it is reported.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("they report it " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", they report it.", copy.deepcopy(when_cat)))

    # PRESENT (different formulation)
    TRAIN_DATA.append(("that is reported " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", that is reported.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("institutions report that " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", institutions report that.", copy.deepcopy(when_cat)))
    TRAIN_DATA.append(("we report that " + when_text + '.', copy.deepcopy(when_cat)))
    TRAIN_DATA.append((when_text + ", we report that.", copy.deepcopy(when_cat)))

# randomly add variants with different years
for text, cat in TRAIN_DATA.copy():
    if re.search(r'\b20[0-9][0-9]\b', text):
        TRAIN_DATA.append((re.sub(r'\b20[0-9][0-9]\b', str(random.choice(range(2000,2050))), text), cat))

# add full sentences
for line in open("./data/argm-tmp-sentences.txt"):
    cat, sen_text = line.split("\t")
    cat = '0' if cat == '?' else cat
    TRAIN_DATA.append((sen_text.rstrip("\n\r"), CATS[int(cat)]))

#TRAIN_DATA = TRAIN_DATA[0:256]
print(len(TRAIN_DATA))
print(TRAIN_DATA[0])
print(TRAIN_DATA[1])
print(TRAIN_DATA[2])
print(TRAIN_DATA[3])

TEST_DATA = [
    ("every time it snows, we report a snowman", CATS[2]),
    ("every time it snowed, we reported a snowman", CATS[2]),
    ("when, finally, it snowed, we reported a snowman", CATS[1]),
    ("by Friday, we reported a snowman", CATS[1]),
    ("on Friday, we reported a snowman", CATS[1]),
    ("on Friday, we often reported a snowman", CATS[2]),
    ("every Friday, we reported a snowman", CATS[3]),
]

is_using_gpu = spacy.prefer_gpu()
if is_using_gpu:
    torch.set_default_tensor_type("torch.cuda.FloatTensor")

nlp = spacy.load(BASE_MODEL) if len(BASE_MODEL)>3 else spacy.blank(BASE_MODEL)
textcat = nlp.create_pipe(TEXTCAT_PIPENAME, config={ "exclusive_classes": True, "architecture":"ensemble", "ngram_size":3, "attr":"lower" })
for label in LABELS:
    textcat.add_label(label)
nlp.add_pipe(textcat, last=True)

print("====================================================================")
print("starting to optimize...")
print("")

optimizer = nlp.resume_training() if USE_TRF else nlp.begin_training()
#optimizer.alpha = 0.001
#optimizer.trf_weight_decay = 0.005
#optimizer.L2 = 0.0

for i in range(MAX_EPOCHS):
    random.shuffle(TRAIN_DATA)
    losses = {}
    t_start_time = time.time()
    t_processed_batches = 0
    t_remaining_batches = int(len(TRAIN_DATA) / BATCH_SIZE)
    for batch in minibatch(TRAIN_DATA, size=BATCH_SIZE):
        texts, cats = zip(*batch)
        nlp.update(texts, cats, sgd=optimizer, losses=losses)
        t_processed_batches += 1
        t_remaining_batches -= 1
        if t_remaining_batches % 16 == 0:
            t_remaining_time = (time.time() - t_start_time) / t_processed_batches * t_remaining_batches
            if t_remaining_time > 90:
                print(str(int(t_remaining_time/15)/4) + " minutes remaining in batch (" + str(i) + "/" + str(MAX_EPOCHS) + ")")
            else:
                print(str(int(t_remaining_time)) + " seconds remaining in batch (" + str(i) + "/" + str(MAX_EPOCHS) + ")")
    print(i, losses)

print("====================================================================")
print("saving the model...")
print("")

nlp.to_disk(MODEL_SAVEPATH)

print("====================================================================")
print("making predictions...")
print("")

for TEXT, CATS in TEST_DATA:
    PREDICTIONS = nlp(TEXT)
    print(PREDICTIONS)
    print(PREDICTIONS.cats)