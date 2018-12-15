import sys
from nltk.corpus import wordnet as wn
synonyms = []
antonyms = []

for syn in wn.synsets(sys.argv[1]):
    for l in syn.lemmas():
        if l.name().lower() not in synonyms:
            synonyms.append(l.name().lower())
            if l.antonyms():
                antonyms.append(l.antonyms()[0].name())
print(set(synonyms))
print(set(antonyms))
