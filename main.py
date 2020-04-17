#!/usr/bin/env python
# coding: utf-8

from bs4 import BeautifulSoup
from requests import get
from time import sleep
from random import randint
import pandas as pd
import requests
import re


apiKey = 'd85bfac0'


def friendly_fires():
    """Scrape maximumfun.org for list of friendly fire episodes"""

    podcasts = []

    pages = [str(i) for i in range(1,15)]

    for page in pages:
        response = get('https://maximumfun.org/podcasts/friendly-fire/?_paged=' + page)

        html_soup = BeautifulSoup(response.text, 'html.parser')

        pod_containers = html_soup.find_all('div', class_ = 'latest-panel-loop-item-title')

        for pod_container in pod_containers:
            pod_title = pod_container.find('h4').text.strip()
            podcasts.append(pod_title)
        
    return podcasts

def clean_data():
    """Clean maximumfun.org scrape"""

    pods = friendly_fires()
    pod_df = pd.DataFrame([line.strip().split(':', 1) for line in pods], columns=['number', 'episode'])
    pod_df['episode'] = pod_df['episode'].str.replace("’", '')
    pod_df[['episode', 'year', 'none', 'na']] = pod_df['episode'].str.split('(', expand=True)
    pod_df = pod_df.drop(['none', 'na'], axis=1)
    pod_df['year'] = pod_df['year'].str.replace(')', '')
    pod_df = pod_df.dropna()
    pod_df = pod_df[~pod_df['number'].str.contains('TRANSCRIPT|Rogue One|Pork Chop Feed|Bonus')]
    pod_df['number'] = pod_df['number'].str.replace('Ep ', '')
    pod_df['number'] = pod_df['number'].str.replace('Episode ', '')
    pod_df['number'] = pod_df['number'].str.replace('Ep', '100')
    pod_df['episode'] = pod_df['episode'].str.replace('100 Tora! Tora! Tora!', 'Tora! Tora! Tora!')
    pod_df['episode'] = pod_df['episode'].apply(lambda x: re.sub('\W+',' ', x))
    pod_df['episode'] = pod_df['episode'].apply(lambda x: x.lower())
    pod_df["movie-year"] = pod_df["episode"] + pod_df["year"]
    
    return pod_df

def get_id():
    """Query OMDB API using titles obtained from maximumfun.org. Goal is to get imdbIDs so we can then scrape IMDB for viewing options"""
    for episode in episodes:
        year = episode[-4:]
        movieTitle = episode[:-5].lstrip().rstrip().replace(" ", "_")
        URL = 'http://www.omdbapi.com/?t='+movieTitle+'&y='+year+'&apikey='+apiKey
        response = requests.get(URL).json()
        
        responses.append(response)
        urls.append(URL)
        
    return {
        'responses': responses,
        'urls': urls
    }

def where_to_watch():
    """Scrape advertised viewing options for each movie Friendly Fire has done a podcast on."""
    watch_options = []
    urls = []

    for url in movie_data['urls']:
        response = get(url)
        html_soup = BeautifulSoup(response.text, 'html.parser')

        option = html_soup.find('span', class_ = 'buybox__description')
        if option is not None:
            option = option.text
        else: 
            option
        
        watch_options.append(option)
        urls.append(url)
    
    return {
        'watch_options': watch_options,
        'urls': urls
    }

# scrape maximumfun.org
pods = friendly_fires()

# clean maximumfun.org data
pod_df = clean_data()

# Instantiate response and url objects, create episodes df, query OMDB API
responses = []
urls = []
episodes = pod_df['movie-year']
data = get_id()

# Create table from OMDB query, remove rows that did not have imdbID
movie_data = pd.DataFrame(data['responses'])
movie_data = movie_data[movie_data['imdbID'].notna()]

# Create column containing IMDB urls for each movie
movie_data['urls'] = 'https://www.imdb.com/title/' + movie_data['imdbID']

# Scrape IMDB for advertised options to watch each movie
options = where_to_watch()

# Create table for IMDB scrape results
options = pd.DataFrame(options)

# Merge watch options with movie metadata
movie_data = movie_data.merge(options, on = 'urls', how = 'left')

# Remove unnecessary columns and rename
Friendly_fire = movie_data[['Title', 'Year', 'imdbRating', 'watch_options']]
Friendly_fire.columns = ['Title', 'Year', 'imdbRating', 'amazon_watch_options']
