#!/usr/bin/python
# encoding: utf-8

import random
import csv
import json
import wikipedia
import re
import logging
import os.path
import sys
import subprocess

from nltk import *
import nltk

logging.captureWarnings(True)

################################################################################
#                         Constant Definitions                                 #
################################################################################

flags = {
    '-e': {'configVar': 'entropy', 'type': 'num'},
    '-r': {'configVar': 'readMoreLimit', 'type': 'num'},
    '-d': {'configVar': 'dictionaryFile', 'type': 'string'},
    '-nosave': {'configVar': 'saveDictionary', 'type': 'unary'},
    '-n': {'configVar': 'numSentences', 'type': 'num'},
    '-delete': {'configVar': 'deleteDictionary', 'type': 'unary'},
    '-sync': {'configVar': 'syncMaster', 'type': 'unary'},
    '-nomaster': {'configVar': 'useMaster', 'type': 'unary'}
    }

def isnum(input): return input.isdigit()
def isString(input): return True
types = {'num': isnum, 'string': isString}

config = {
    'entropy': 1,
    'readMoreLimit': 1,
    'searchTerms': [],
    'dictionaryFile': 'dictionary',
    'saveDictionary': True,
    'deleteDictionary': False,
    'numSentences': 1,
    'useMaster': True,
    'syncMaster': False
    }

################################################################################
#                         Function Definitions                                 #
################################################################################
def newDictionary():
    return ({}, {}, {})

def saveDictionary(dictionaryToSave, meta, name):
    content = {'content': dictionaryToSave, 'meta': meta}
    with open(name,'w+') as contents:
        contents.write(json.dumps(content, indent=2))

def deleteDictionary(name):
    os.remove(name)

def loadFileContents(name):
    if os.path.isfile(name):
        with open(name,'r') as contents:
            dictionary = json.loads(contents.read())
        return dictionary
    else:
        return {'content': {}, 'pos': {}, 'meta': {'config': config}}

def loadDictionary(name):
    dictionary = loadFileContents(name)
    return (dictionary['content'], dictionary['pos'], dictionary['meta'])

def getRandomDictionaryWord():
    return random.choice(dictionary.keys())

def addWord(firstWord, secondWord):
    firstWord = firstWord.lower().replace("\n", '').replace('.', '')
    secondWord = secondWord.lower().replace("\n", '').replace('.', '')
    firstWord = ''.join(c for c in firstWord if c.isalnum() or c in allowedChars)
    secondWord = ''.join(c for c in secondWord if c.isalnum() or c in allowedChars)

    if firstWord != "" and secondWord != "":
        if firstWord in dictionary:
            if secondWord in dictionary[firstWord]:
                dictionary[firstWord][secondWord] += 1
            else:
                dictionary[firstWord][secondWord] = 1
        else:
            dictionary[firstWord] = {}
            dictionary[firstWord][secondWord] = 1

        if firstWord in master:
            if secondWord in master[firstWord]:
                master[firstWord][secondWord] += 1
            else:
                master[firstWord][secondWord] = 1
        else:
            master[firstWord] = {}
            master[firstWord][secondWord] = 1



def hasPunctuation(word):
    if word[-1:] in punctuationMap:
        return True
    else:
        return False

def isFullStop(word):
    if word.lower() in ['<<period>>', '<<question>>', '<<exclamation>>']:
        return True
    else:
        return False

def getPunctuation(word):
    return punctuationMap[word[-1:]]

def removePunctuation(word):
    return word[:-1]

def isQuestion(word):
    return word in questionWords

def getFileContents(filename):
    if not filename == '':
        with open (filename, "r") as myfile:
            data=myfile.read().replace('\n', ' ')
        return data
    else:
        return ""

def getNextWordSuggestions(word):
    suggestions = []
    if word in dictionary:
        suggestions = dictionary[word]
    else:
        while suggestions == []:
            randChoice = random.choice(dictionary.keys())
            if randChoice in dictionary:
                suggestions = dictionary[randChoice]
    return suggestions

def chooseNextWord(word):
    choices = getNextWordSuggestions(word)

    totalWeight = 0
    currentWeight = 0
    weightedArray = []

    for choice in choices:
        totalWeight += int(choices[choice])
        for i in range(0, (choices[choice] ** config['entropy'])):
            weightedArray.append(choice)
    return random.choice(weightedArray)

def iterateInput(input):
    input = input.replace("\n", ' ')

    text = word_tokenize(input)
    print nltk.pos_tag(text)

    # words = input.split(" ")
    # for i in range(0, (len(words)-1)):
    #     word = words[i]
    #     word = word.replace(' ', '')
    #     word = word.lower()
    #     nextWord = words[i+1].lower()
    #
    #     word = ''.join([i if ord(i) < 128 else '' for i in word])
    #     nextWord = ''.join([i if ord(i) < 128 else '' for i in nextWord])
    #
    #     if hasPunctuation(word):
    #         punctuation = getPunctuation(word)
    #         word = removePunctuation(word)
    #         addWord(word, punctuation)
    #         if not punctuation.lower() == '<<period>>':
    #             addWord(word, nextWord)
    #             addWord(punctuation, nextWord)
    #     else:
    #         addWord(word.lower(), nextWord.lower())


def finalize(sentence):
    sentence = sentence.capitalize()
    sentence = sentence.replace(' <<', '<<')
    for mark in finalizeMap:
        sentence = sentence.replace(mark.lower(), finalizeMap[mark])
    return sentence

def makeSentence(word):
    word = word.lower()
    parts = []
    def makeSentenceHelper(word, sentenceParts):
        if isFullStop(word):
            sentenceParts.append(word)
            return sentenceParts
        else:
            sentenceParts.append(word)
            nextWord = chooseNextWord(word.lower())
            if (nextWord.lower() == '<<comma>>'):
                sentenceParts.append('<<comma>>')
                while (nextWord.lower() == '<<comma>>'):
                    nextWord = chooseNextWord(word)
            return makeSentenceHelper(nextWord, sentenceParts)
    try:
        parts = makeSentenceHelper(word, [])
    except KeyError:
        print parts
        parts = makeSentenceHelper(word, [])
    if isQuestion(parts[0]):
        parts[len(parts) - 1] = '<<question>>'

    sentence = ' '.join(parts)


    sentence = finalize(sentence)

    return sentence

def crawlAndLearn(topic):
    print 'topic: ' + str(topic)
    if not 'educatedOn' in meta:
        meta['educatedOn'] = []

    if topic in meta['educatedOn']:
        print "Already Learned: " + topic
    else:
        search = wikipedia.search(topic, results=int(config['readMoreLimit']))
        for page in search:
            print "Learning about: " + page
            try:
                article = wikipedia.page(page)
                content = re.sub(r'=+\sSee also\s=+.+$', ' ', article.content, flags=re.M | re.S)
                content = re.sub(r'=+\s.+\s=+', ' ', content)
                content = re.sub(r'\(.+\)', ' ', content, flags=re.M | re.S)
                #print content
                iterateInput(content)
            except wikipedia.exceptions.DisambiguationError:
                content = ""
            except wikipedia.exceptions.PageError:
                content = ""
        if not 'educatedOn' in meta:
            meta['educatedOn'] = []
        meta['educatedOn'].append(topic)



def learnAbout(topics):
    try:
        for topic in topics.split(): # string case
            crawlAndLearn(topic)
    except AttributeError:
        for topic in topics:
            crawlAndLearn(topic)

def matchesType(value, type):
    # return value.isdigit()
    return types[type](value)

def parseArguments(argv):
    if len(argv) > 1:
        i = 1
        while(i < len(argv)):
            if argv[i] in flags:
                if flags[argv[i]]['type'] == 'unary':
                    config[flags[argv[i]]['configVar']] = not config[flags[argv[i]]['configVar']]
                else:
                    if i+1 < len(argv):
                        if matchesType(argv[i+1], flags[argv[i]]['type']):
                            if flags[argv[i]]['type'] == 'num':
                                config[flags[argv[i]]['configVar']] = int(argv[i+1])
                            else:
                                config[flags[argv[i]]['configVar']] = argv[i+1]
                            i += 1
                        else:
                            print "ERROR: Value entered for flag '" + argv[i] + "' is expected to be type '" + flags[argv[i]]['type'] + "'"
                    else:
                        print "ERROR: value not found for flag '" + argv[i] + "'. Defaulting to " + str(config[flags[argv[i]]['configVar']])
            else:
                config['searchTerms'].append(argv[i])
            i += 1

def configDiffersFromMeta(config, meta):
    return config['readMoreLimit'] != meta['config']['readMoreLimit']

def generateSentences():
    for i in range(0, config['numSentences']):
        print
        print makeSentence(getRandomDictionaryWord())
        print

def loadMasterFile():
    if os.path.isfile('robowriter-master-dictionary/master-dictionary'):
        with open('robowriter-master-dictionary/master-dictionary','r') as contents:
            master = json.loads(contents.read())
        return master
    else:
        return {}

def loadMasterToDictionary(masterFile):
    for word in masterFile:
        for nextWord in masterFile[word]:
            if word in dictionary:
                dictionary[word][nextWord] = 1
            else:
                dictionary[word] = {}
                dictionary[word][nextWord] = 1

def saveMaster():
    with open('robowriter-master-dictionary/master-dictionary','w+') as contents:
        contents.write(json.dumps(master, indent=2))

def syncMaster():
    bashCommand = "./robowriter-master-dictionary/sync.sh"
    process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]



################################################################################
#                         Run The Program                                      #
################################################################################
parseArguments(sys.argv)

if (config['deleteDictionary']):
    deleteDictionary(config['dictionaryFile'])

(dictionary, meta) = loadDictionary(config['dictionaryFile'])
if configDiffersFromMeta(config, meta):
    print "Config changed. Making new dictionary."
    (dictionary, meta) = newDictionary()

meta['config'] = config

# master = loadMasterFile()
# print "master: " + str(master)

# print "using master: " + str(config['useMaster'])
# if config['useMaster']:
#     loadMasterToDictionary(master)

learnAbout(config['searchTerms'])

if config['saveDictionary']:
    print "saving to " + config['dictionaryFile']
    saveDictionary(dictionary, meta, config['dictionaryFile'])

# saveMaster()
# if config['syncMaster']: syncMaster()
