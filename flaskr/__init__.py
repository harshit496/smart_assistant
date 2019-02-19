#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 16 18:10:41 2019

@author: harshitshah
"""

import os

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from string import punctuation
from nltk.probability import FreqDist
from heapq import nlargest
from collections import defaultdict
from flask import Flask
from flask_googlecharts import GoogleCharts
import requests
import alpha_vantage
from flask_googlecharts import BarChart
from newsapi.newsapi_client import NewsApiClient
from werkzeug import secure_filename
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from flaskr.db import get_db

import argparse

from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="flaskr/sentimental-75b3e363bd04.json"

def print_result(annotations):
    score = annotations.document_sentiment.score
    magnitude = annotations.document_sentiment.magnitude

    for index, sentence in enumerate(annotations.sentences):
        sentence_sentiment = sentence.sentiment.score
        print('Sentence {} has a sentiment score of {}'.format(
            index, sentence_sentiment))

    print('Overall Sentiment: score of {} with magnitude of {}'.format(
        score, magnitude))
    return score,magnitude


def analyze(movie_review_filename):
    """Run a sentiment analysis request on text within a passed filename."""
    client = language.LanguageServiceClient()

    with open(movie_review_filename, 'r') as review_file:
        # Instantiates a plain text document.
        content = review_file.read()

    document = types.Document(
        content=content,
        type=enums.Document.Type.PLAIN_TEXT)
    annotations = client.analyze_sentiment(document=document)

    # Print the results
    return print_result(annotations)



def parse_arguments():
    """ Parse command line arguments """ 
    parser = argparse.ArgumentParser()
    parser.add_argument('filepath', help='File name of text to summarize')
    parser.add_argument('-l', '--length', default=4, help='Number of sentences to return')
    args = parser.parse_args()

    return args

def read_file(path):
    """ Read the file at designated path and throw exception if unable to do so """ 
    try:
        with open(path, 'r') as file:
            return file.read()

    except IOError as e:
        print("Fatal Error: File ({}) could not be locaeted or is not readable.".format(path))

def sanitize_input(data):
    """ 
    Currently just a whitespace remover. More thought will have to be given with how 
    to handle sanitzation and encoding in a way that most text files can be successfully
    parsed
    """
    replace = {
        ord('\f') : ' ',
        ord('\t') : ' ',
        ord('\n') : ' ',
        ord('\r') : None
    }

    return data.translate(replace)

def tokenize_content(content):
    """
    Accept the content and produce a list of tokenized sentences, 
    a list of tokenized words, and then a list of the tokenized words
    with stop words built from NLTK corpus and Python string class filtred out. 
    """
    stop_words = set(stopwords.words('english') + list(punctuation))
    words = word_tokenize(content.lower())
    
    return [
        sent_tokenize(content),
        [word for word in words if word not in stop_words]    
    ]

def score_tokens(filterd_words, sentence_tokens):
    """
    Builds a frequency map based on the filtered list of words and 
    uses this to produce a map of each sentence and its total score
    """
    word_freq = FreqDist(filterd_words)

    ranking = defaultdict(int)

    for i, sentence in enumerate(sentence_tokens):
        for word in word_tokenize(sentence.lower()):
            if word in word_freq:
                ranking[i] += word_freq[word]

    return ranking

def summarize(ranks, sentences, length):
    """
    Utilizes a ranking map produced by score_token to extract
    the highest ranking sentences in order after converting from
    array to string.  
    """
    if int(length) > len(sentences): 
        print("Error, more sentences requested than available. Use --l (--length) flag to adjust.")
        exit()

    indexes = nlargest(length, ranks, key=ranks.get)
    final_sentences = [sentences[j] for j in sorted(indexes)]
    return ' '.join(final_sentences) 

def call_summarize(filename,length):
    content = read_file(filename)

    content = sanitize_input(content)

    sentence_tokens, word_tokens = tokenize_content(content)  
    sentence_ranks = score_tokens(word_tokens, sentence_tokens)

    return summarize(sentence_ranks, sentence_tokens, length)



def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    from . import db
    db.init_app(app)

    # from . import auth
    # app.register_blueprint(auth.bp)
    
    @app.route('/home/homepage', methods=('GET', 'POST'))
    def homepage():
        key='G43VZ2WHVRWPNNW9'
        # company=['OXY','EOG','APC','APA','COP','PXD']
        # s_list={}
        # for symbol in company:
        #     url='https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol='+symbol+'&apikey='+key
        #     response = requests.get(url).json()

        #     response = response['Global Quote']
        #     print(response)
        #     s_list[symbol]=[response['05. price'],response['09. change']]
        # print (s_list)
        labels = [
                'JAN', 'FEB', 'MAR', 'APR',
                'MAY', 'JUN', 'JUL', 'AUG',
                'SEP', 'OCT', 'NOV', 'DEC']

        values = [
                967.67, 1190.89, 1079.75, 1349.19,
                2328.91, 2504.28, 2873.83, 4764.87,
                4349.29, 6458.30, 9907, 16297]
        if request.method == 'POST':
            code=(request.form.get('search',False)).upper()
            if code=='OXY':
                name='Occidental Petroleum Corporation'
            if code=='EOG':
                name='EOG Resources Inc'
            if code=='APC':
                name='Anadarko Petroleum Corporation'
            if code=='APA':
                name='Apache Corporation'
            if code=='COP':
                name='ConocoPhillips'
            if code=='PXD':
                name='Pioneer Natural Resources'

            if request.form.get('button',False)=='stocks':
                datatype='TIME_SERIES_MONTHLY'

                url='https://www.alphavantage.co/query?function='+datatype+'&symbol='+code+'&apikey='+key

                response = requests.get(url).json()
                response = response['Monthly Time Series']
                current=list(response.keys())[0]
                # print(current)

                #plot graph

                y=[]
                for val in response.values():
                    y.append(val['4. close'])
                x=list(response.keys())
                #print(len(x),len(y))
                x=x[0:30]
                y=y[0:30]
                x=x[::-1]
                y=y[::-1]
                return render_template('home/stocks.html', name=name, max=200, labels=x, values=y)
            elif request.form.get('button',False)=='articles':
                
                newsapi = NewsApiClient(api_key='468fffd8bd8f4768985cf072a1a59e70')
                response=(newsapi.get_everything(q=name))
                a_dict=response['articles']
                # print (a_dict)
                return render_template('home/articles.html', name=name, articles=a_dict)
            elif request.form.get('button',False)=='ect':
                with open("call_transcript.txt") as file:
                    data = file.readlines()
                names=[]
                content = [x.strip() for x in data] 
                for ele in content:
                    if "Operator" in ele:
                        break
                    else:
                        names.append(ele)
                
                participants=[]
                for ele in names:
                    if '-' in ele:
                        n,d=ele.split('-')
                        participants.append(n.strip())
                
                active_participants={}
                for ele in content:
                    if ele in participants:
                        if ele in active_participants:
                            active_participants[ele]+=1
                        else:
                            active_participants[ele]=1
                
               
                # pie chart for frequency
                values=list(active_participants.values())
                labels=list(active_participants.keys())
                print(len(labels),len(values))
                colors = [
                        "#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA",
                        "#ABCDEF", "#DDDDDD", "#ABCABC", "#4169E1",
                        "#C71585", "#FF4500", "#FEDCBA", "#46BFBD"]

                # summarization
                participant=[]
                p1='flaskr/jeff.txt'
                p2='flaskr/vicki.txt'
                p3='flaskr/cedric.txt'
                length=8
                participant.append(call_summarize(p1,length))
                participant.append(call_summarize(p2,length))
                participant.append(call_summarize(p3,length))


                return render_template('home/transcript.html', names=names, ect=data,set=zip(values, labels, colors),legend='Frequency of participants speaking', max=17000, participant=participant)
            elif request.form.get('button',False)=='sentiment':
                f_good="oxy_good.txt"
                f_bad='oxy_bad.txt'
                good,bad=[],[]
                with open(f_good) as file:
                    good.append(file.read())
                with open(f_bad) as file:
                    bad.append(file.read())

                s,m=analyze(f_good)
                good.append('Postive Attitude with Magnitude')
                good.append(round(m))

                s,m=analyze(f_bad)
                bad.append('Negative Attitude with Magnitude')
                bad.append(round(m))

                return render_template('home/sentiment.html', good=good, bad=bad)
        return render_template('home/homepage.html' )


          

    return app