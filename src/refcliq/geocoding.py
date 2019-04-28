from os.path import exists
from src.refcliq.util import cleanCurlyAround
import re
import networkx as nx
from fuzzywuzzy.process import extractOne
from fuzzywuzzy.fuzz import ratio
from time import sleep, monotonic
from tqdm import tqdm
import json
import googlemaps
import spacy
from titlecase import titlecase
from sys import stderr

CACHE = 'cache.json'

_US = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO',
       'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']


def _computeFV(s: str)->list:
    """
        Computes a normalized histogram of the (common) letters in s.
    """
    trans = {}
    for i, c in enumerate('abcdefghiklmnopqrstuvwxyz'):
        trans[c] = i

    ret = [0, ]*len(trans)
    for c in s.lower():
        if (c in trans):
            ret[trans[c]] += 1
    return([x/sum(ret) for x in ret])


def _distanceFV(v1: list, v2: list)->float:
    """
        Computes the distance between two feature vectors
    """
    ret = 0
    for i in range(len(v1)):
        ret += abs(v1[i]-v2[i])
    return(ret/2.0)


def _find(d: dict, k: str, T: int=75)->str:
    """
        Finds the key most similar to k in d. 
        Returns none if no key is at least T similar (fuzzywuzzy ratio)
    """

    if k in d:
        return(k)
    if (k == ''):
        return(None)
    ret = extractOne(k, d.keys(), score_cutoff=T)
    if ret:
        return(ret[0])
    return(None)


def _remove_numbers(s: str)->str:
    """
        Removes all continuous sequences of characters that contain numbers. 
        Ex. 11215, F-93160, etc...
    """
    return(','.join([' '.join([word for word in x.split() if not any([c.isdigit() for c in word])]) for x in s.split(',')]).replace(',,', ',').replace(',', ', '))


def _count_useful_parts(address_parts: list, google_result: dict, T: int=75)->int:
    """
        Determines how many address_parts are needed for city-level geocoding.
    """
    ret = 0
    for a in address_parts:
        found = False
        for p in google_result["address_components"]:
            if (ratio(a.lower(), p['long_name'].lower()) > T) or (ratio(a.lower(), p['short_name'].lower()) > T):
                found = True
                break
        if found:
            ret += 1

    return(ret)


def _filter_geocode(google_result: dict):
    useful = set(['postal_town', 'administrative_area_level_1',
                  'administrative_area_level_2', 'country', 'locality'])

    to_remove = []
    for i, part in enumerate(google_result["address_components"]):
        if len(set(part['types']).intersection(useful)) == 0:
            to_remove.append(i)

    for i in sorted(to_remove, reverse=True):
        del(google_result["address_components"][i])

    return(google_result)


class ArticleGeoCoder:
    def __init__(self, google_key: str=''):
        self._cache = {}
        if (google_key != ''):
            self._gmaps = googlemaps.Client(key=google_key)
        else:
            self._gmaps = None

        # those always pose a problem
        self._parts_by_country = {'peoples r china': 3, 'United States': 3,
                                  'czech republic': 2, 'ireland': 2, 'norway': 2, 'italy': 2, 'finland': 2}
        self._last_request = monotonic()  # keeps track of the last time we used nominatim
        self._outgoing_calls = 0

        if exists(CACHE):
            with open(CACHE, 'r') as fin:
                data = json.load(fin)
                self._cache = data['cache']
                self._parts_by_country.update(data['parts'])

    def _save_state(self):
        # 'fv':self._cacheFV
        to_save = {'cache': self._cache, 'parts': self._parts_by_country}
        with open('cache.json', 'w') as fout:
            json.dump(to_save, fout, indent=4, sort_keys=True)

    def add_authors_location_inplace(self, G: nx.Graph):
        """
            For every node of G (a reference in the network), finds the
            coordinates based from the 'Affiliation' bibtex field, if present.
            _Alters the data of G_.
        """
        #https://stackoverflow.com/questions/53383352/spacy-and-spacy-models-in-setup-py
        try:
            nlp = spacy.load('en_core_web_sm')
        except OSError:
            print('Downloading language model for spaCy\n'
                "(don't worry, this will only happen once)", file=stderr)
            from spacy.cli import download
            download('en_core_web_sm')
            nlp = spacy.load('en_core_web_sm')
        
        trees = {}
        print('Compiling addresses')
        for n in tqdm(G):
            G.node[n]['data']['countries'] = []
            G.node[n]['data']['coordinates'] = []
            addresses = []
            if ('data' in G.node[n]) and ('Affiliation' in G.node[n]['data']) and (G.node[n]['data']['Affiliation'] is not None) and (len(G.node[n]['data']['Affiliation']) > 0):
                aff = G.node[n]['data']['Affiliation'].replace('(Reprint Author)', '').replace(
                    ".,", ',').replace("'", '')  # O'lastname / Jesusm. / Redone.  mess sentence identification
                doc = nlp(aff)
                add = ''
                for sent in doc.sents:
                    if sent.text.endswith('.'):
                        current = _remove_numbers(
                            (add+' '+sent.text).strip().replace('  ', ' '))
                        if current.endswith('.'):
                            current = current[:-1]
                        # special cases: NY 10012 USA / LOS ANGELES,CA.
                        vals = [x.strip() for x in current.split(',')]
                        # ,CA.
                        if (len(vals[-1]) == 2) and vals[-1].upper() in _US:
                            addresses.append(
                                [titlecase(vals[-2]), vals[-1], 'United States'])
                        elif (vals[-1].endswith(' USA')):
                            addresses.append(
                                [titlecase(vals[-2]), vals[-1].split(' ')[0], 'United States'])
                        else:
                            if len(vals) > 3:  # name, dept, etc
                                addresses.append([titlecase(x)
                                                  for x in vals[-3:]])
                            else:
                                addresses.append([titlecase(x) for x in vals])
                        add = ''
                    else:
                        add = add + ' ' + sent.text

                for vals in addresses:
                    G.node[n]['data']['countries'].append(vals[-1])
                    if self._gmaps is not None:
                        v = [x.lower() for x in vals]
                        if len(v) < 3:
                            v = ['', ]*(3-len(v)) + v
                        # not really city / state / country, but it is easier to
                        # code with names
                        # there is probably a shorter way of doing this using defaultdicts
                        country = _find(trees, v[-1])
                        if country is None:
                            country = v[-1]
                            trees[country] = {}

                        state = _find(trees[country], v[-2])
                        if state is None:
                            state = v[-2]
                            trees[country][state] = {}

                        city = _find(trees[country][state], v[-3])
                        if city is None:
                            city = v[-3]
                            trees[country][state][city] = []

                        trees[country][state][city].append(n)

        
        for country in trees:
            cached = _find(self._parts_by_country, country)

            if cached is None:
                i = 0
                j = 0
                geo = []
                while not geo:
                    try:
                        sample_state = list(trees[country].keys())[i]
                        sample_city = list(trees[country][sample_state])[j]
                        parts = [sample_city, sample_state, country]
                        geo = self._google(parts)
                        j += 1
                        if j == len(trees[country][sample_state].keys()):
                            j = 0
                            i += 1
                            if i == len(trees[country]):
                                # didn't find anything, run all... very unlikely. Very.
                                to_use = 3
                    except:
                        print('Could not find anything using "{0}" as a country, please check the affiliation field.'.format(
                            country))
                        print(
                            '(This can happen when a author name has a dot at the end of a non-abreviation.)')
                        # print(trees[country])
                        raise
                if geo:
                    self._parts_by_country[country] = _count_useful_parts(
                        parts, geo)
                    self._save_state()

        print('Getting coordinates')
        for country in tqdm(trees):
            cached = _find(self._parts_by_country, country)
            to_use = self._parts_by_country[cached]

            for state in trees[country]:
                for city in trees[country][state]:
                    parts = [city, state, country][-to_use:]
                    parts = ['', ]*(3-len(parts)) + parts
                    geo = self._cache_search(parts)
                    if geo is None:
                        geo = self._google(parts)
                        if not geo:
                            continue
                        self._cache_add(parts, geo)

                    for n in trees[country][state][city]:
                        G.node[n]['data']['coordinates'].append(
                            [geo['geometry']['location']['lng'], geo['geometry']['location']['lat']])

        return(G)

    def _cache_search(self, address_parts: list):
        vals = ['', ]*(3-(len(address_parts))) + address_parts

        country = _find(self._cache, vals[-1])
        if country is None:
            return(None)

        state = _find(self._cache[country], vals[-2])
        if state is None:
            return(None)

        city = _find(self._cache[country][state], vals[-3])
        if city is None:
            return(None)

        return(self._cache[country][state][city])

    def _cache_add(self, address_parts: list, google_geocode: dict):
        vals = ['', ]*(3-(len(address_parts))) + address_parts

        country = _find(self._cache, vals[-1])
        if country is None:
            country = vals[-1]
            self._cache[country] = {}

        state = _find(self._cache[country], vals[-2])
        if state is None:
            state = vals[-2]
            self._cache[country][state] = {}

        city = _find(self._cache[country][state], vals[-3])
        if city is None:
            city = vals[-3]

        self._cache[country][state][city] = google_geocode
        self._save_state()

    def _google(self, address_parts: list)->list:
        """
            Queries google's geocoding service for the address.
            Limited to 50 queries per second. A key is necessary.
            Returns (lng,lat) for the point.
        """
        minTime = 1/50
        delta = monotonic() - self._last_request
        res = None
        address = ', '.join([x for x in address_parts if x != ''])
        if delta <= minTime:
            sleep(minTime-delta)

        res = self._gmaps.geocode(address)
        # with open('testing.json','r') as fin:
        #     res = json.load(fin)
        if res:
            res = _filter_geocode(res[0])

        # print('google ', address)
        self._outgoing_calls += 1
        self._last_request = monotonic()
        return(res)
