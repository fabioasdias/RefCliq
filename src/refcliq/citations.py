import networkx as nx
from networkx.readwrite import json_graph
from fuzzywuzzy.fuzz import ratio
from tqdm import tqdm
from itertools import combinations
from collections import Counter
from math import floor
from string import punctuation
from collections import Counter
from nltk.corpus import stopwords
from nltk import WordNetLemmatizer, download, bigrams
from math import log
from nltk.tokenize import word_tokenize
from nltk.stem import snowball

from src.refcliq.geocoding import ArticleGeoCoder
from src.refcliq.preprocess import import_bibs

from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from scipy.sparse import coo_matrix

from os.path import exists
import klepto
import pickle

download('stopwords')
download('punkt')
download('wordnet')

stemmer = snowball.EnglishStemmer()
remove_punct = str.maketrans('', '', punctuation)


def tokens_from_sentence(sentence: str, remove_duplicates: bool=True)->list:
    """
      Returns a list of "important" words in a sentence.
      Only works in English but returned tokens may not be proper English.
    """
    stop_words = stopwords.words('english')
    words = [word.translate(remove_punct).lower()
             for word in word_tokenize(sentence)]
    words = [stemmer.stem(word) for word in words if (
        word not in stop_words) and (word != '')]
    if remove_duplicates:
        return(list(set(words)))
    else:
        return(words)


# https://medium.com/analytics-vidhya/automated-keyword-extraction-from-articles-using-nlp-bfd864f41b34
def sort_coo(coo_matrix):
    tuples = zip(coo_matrix.col, coo_matrix.data)
    return sorted(tuples, key=lambda x: (x[1], x[0]), reverse=True)


def extract_topn_from_vector(feature_names, sorted_items, topn=10):
    """get the feature names and tf-idf score of top n items"""

    score_vals = []
    feature_vals = []

    # word index and corresponding tf-idf score

    to_remove = set()
    for idx, score in sorted_items:
        # do not add keywords that are contained in other keywords: sao paulo, sao, paulo.
        skip = False
        # we already added that

        for i, keywords in enumerate(feature_vals):
            for already in keywords.split():
                for toAdd in feature_names[idx].split():
                    if toAdd in already:
                        skip = True
                        # let's keep the longest keyword
                        if len(feature_vals[i]) < len(feature_names[idx]):
                            feature_vals[i] = feature_names[idx]

        if not skip and(feature_names[idx] not in feature_vals):
            score_vals.append(round(score, 6))
            feature_vals.append(feature_names[idx])

            for i in range(len(feature_vals)):
                for j in range(i+1, len(feature_vals)):
                    if feature_vals[i] == feature_vals[j]:
                        score_vals[i] += score_vals[j]
                        to_remove.add(j)
            if (len(score_vals)-len(to_remove)) == topn:
                break

    for j in sorted(to_remove, reverse=True):
        del(feature_vals[j])
        del(score_vals[j])

    # create a tuples of feature,score
    results = zip(feature_vals, score_vals)

    return(list(results))


def _merge_keywords(keywords: list, how_many_works: int)->list:
    """
        Removes duplicate keywords from a list, updating the tf-idf (summing the
        occurences). How_many_works is used to re-normalize the values.
    """
    merged = {}
    for k, v in keywords:
        if k not in merged:
            merged[k] = v
        else:
            merged[k] += v
    return([(k, merged[k]/how_many_works) for k in merged])

# @profile


def same_article(a1: dict, a2: dict)->bool:
    """
    Tests if two articles are the same based on their info. 

    Uses fuzzy string matching and the Person structure from pybtex.
    """

    # usefulFields=list(set([k for k in a1 if a1[k]]).intersection(set([k for k in a2 if a2[k]])))

    if ('year' in a1) and ('year' in a2):
        if (a1['year'] != a2['year']):
            return(False)

    # two articles can have the same doi!
    # if 'doi' in usefulFields:
    #     if (a1['doi']!=a2['doi']):
    #         return(False)

    # article from references only have one author that we know of
    L1 = len(a1['authors'])
    L2 = len(a2['authors'])
    if (L1 != 1) and (L2 != 1) and (L1 != L2):
        return(False)

    for field in ['title', 'journal', 'page', 'vol']:
        if (field in a1) and (field in a2) and (ratio(a1[field], a2[field]) <= 80):
            return(False)

    for i in range(min([L1, L2])):
        if (ratio(str(a1['authors'][i]), str(a2['authors'][i])) <= 80) and (ratio(' '.join(a1['authors'][i].last_names), ' '.join(a2['authors'][i].last_names)) <= 80):
            return(False)

    return(True)


class CitationNetwork(nx.DiGraph):
    def __init__(self):
        nx.DiGraph.__init__(self)
        # self._G=nx.DiGraph() #the network
        self._year = {'None': set()}  # indexes
        self._authors = {1: set()}
        self._journal = {0: set()}
        self._title = {0: set()}
        self._authorName = {0: set()}  # None might be a part of a name
        self._equivalentDOIs = {}  # yes, one paper can have more than one DOI

    def save(self, filename: str):
        """Saves the citation network structure to filename"""
        graph = json_graph.node_link_data(self)
        d = klepto.archives.hdf_archive(filename, {'year': self._year,
                                                   'authors': self._authors,
                                                   'title': self._title,
                                                   'authorName': self._authorName,
                                                   'DOIs': self._equivalentDOIs,
                                                   'graph': graph}, cached=False, serialized=True)
        d.dump()

    def load(self, filename: str):
        """Loads the citation network structure from filename"""
        d = klepto.archives.hdf_archive(
            filename, cached=False, serialized=True)

        d.load('graph')
        G = json_graph.node_link_graph(d['graph'])
        self.add_nodes_from(G.nodes(data=True))
        self.add_edges_from(G.edges(data=True))

        for saved, internal in [('DOIs', '_equivalentDOIs'), ('authorName', '_authorName'), ('title', '_title'), ('authors', '_authors'), ('year', '_year')]:
            d.load(saved)
            self.__dict__[internal] = d[saved]

    # @profile
    def build(self, bibs: list, google_key: str='', min_citations: int=2):
        """
        Builds a directed graph to represent the citation network of the file list bibs.
        Ignores any references cited less than min_citation times, along with the citing papers.
        """

        geoCoder = ArticleGeoCoder(google_key)
        articles = import_bibs(bibs)

        print('citation network - Full citation in the .bibs')
        for article in tqdm(articles):
            citing = self.find(article)

        print('citation network - Cited-References')
        for article in tqdm(articles):
            citing = self.find(article)
            for cited_article in article['references']:
                cited = self.find(cited_article)
                self.add_edge(citing, cited)

        to_remove = []
        for n in self:
            # if this article has fewer than min_citations citations AND doesn't cite anything that has more than min_citations
            if (len(list(self.predecessors(n))) < min_citations) and ((len(list(self.successors(n))) == 0) or (max([len(list(self.predecessors(x))) for x in self.successors(n)]) < min_citations)):
                to_remove.append(n)

        for n in to_remove:
            self.remove(n)

        geoCoder.add_authors_location_inplace(self)
        print('Outgoing geocoding calls ', geoCoder._outgoing_calls)

    def remove(self, n: any):
        """
            Removes the node n from the network and the indices.
        """
        self._year[self.node[n]['index']['year']].remove(n)
        self._authors[self.node[n]['index']['authors']].remove(n)
        for index in self.node[n]['index']['journal']:
            self._journal[index].remove(n)
        for index in self.node[n]['index']['title']:
            self._title[index].remove(n)
        for index in self.node[n]['index']['name']:
            self._authorName[index].remove(n)
        self.remove_node(n)

    def add(self, article: dict, replaceNode: str=None)->str:
        """
        Adds a new citation to the network.
        if replaceNode is given, replaces that node in the network
        (this is used to update the name to use a previously unknown DOI)

        Returns the node.
        """

        if ('doi' in article) and (article['doi'] is not None):
            ID = article['doi']
            if replaceNode:
                # print('Replacing {0} with {1}'.format(replaceNode,ID))
                n = replaceNode
                if n[0] != '-':  # aka this is already a DOI!
                    self._equivalentDOIs[ID] = n  # mark as equivalent
                    return(n)  # short-circuits the rest

                for nn in self.predecessors(n):
                    self.add_edge(nn, ID)
                for nn in self.successors(n):
                    self.add_edge(ID, nn)
                # removes from the indexes

                for field in [f for f in self.node[n]['data'] if self.node[n]['data'][f]]:
                    if (field == 'abstract') and (self.node[n]['data'][field] != '') and ((field not in article) or (article[field] == '')):
                        article[field] = self.node[n]['data'][field]
                    elif (field == 'authors') and len(self.node[n]['data']['authors']) > len(article['authors']):
                        article['authors'] = self.node[n]['data']['authors'][:]
                    elif (field not in article) or (not article[field]):
                        article[field] = self.node[n]['data'][field]

                self.remove(n)
        else:
            ID = '-'+str(len(self.nodes()))  # flags as non-DOI

        self.add_node(ID)
        self.node[ID]['data'] = {**article}

        # store which index in the node to make update easier
        self.node[ID]['index'] = {}

        # if ('doi' not in article) or (article['doi'] is None):
        #     self._noDOI.append(ID)

        if 'year' in article:
            yearIndex = article['year']
            self.node[ID]['index']['year'] = yearIndex
            if yearIndex not in self._year:
                self._year[yearIndex] = set()
            self._year[yearIndex].add(ID)
        else:
            self.node[ID]['index']['year'] = 'None'
            self._year['None'].add(ID)

        # authors is the only field that always exists.
        authorIndex = len(article['authors'])
        self.node[ID]['index']['authors'] = authorIndex
        if authorIndex not in self._authors:
            self._authors[authorIndex] = set()
        self._authors[authorIndex].add(ID)

        if ('journal' in article) and (article['journal'] is not None):
            tokens = tokens_from_sentence(article['journal'])
            self.node[ID]['index']['journal'] = tokens
            for token in tokens:
                if token not in self._journal:
                    self._journal[token] = set()
                self._journal[token].add(ID)
        else:
            self._journal[0].add(ID)
            self.node[ID]['index']['journal'] = [0, ]

        if ('title' in article) and (article['title'] is not None):
            tokens = tokens_from_sentence(article['title'])
            self.node[ID]['index']['title'] = tokens
            for token in tokens:
                if token not in self._title:
                    self._title[token] = set()
                self._title[token].add(ID)
        else:
            self._title[0].add(ID)
            self.node[ID]['index']['title'] = [0, ]

        if ('authors' in article) and len(article['authors']) > 0:
            self.node[ID]['index']['name'] = set()
            for author in article['authors']:
                for name in author.last_names:
                    token = name.lower()
                    self.node[ID]['index']['name'].add(token)
                    if token not in self._authorName:
                        self._authorName[token] = set()
                    self._authorName[token].add(ID)
        else:  # no authors
            self._authorName[0].add(ID)
            self.node[ID]['index']['name'] = [0, ]
        return(ID)
    # @profile

    def _find_article_no_doi(self, article: dict):
        """
        Finds the article without using the DOI
        """
        fields = [k for k in article if (article[k])]

        possibles_year = self._year['None'].copy()
        if ('year' in fields) and (article['year'] in self._year):
            possibles_year = possibles_year.union(self._year[article['year']])
        if not possibles_year:
            return(None)

        possibles_authors = self._authors[1].intersection(possibles_year)
        nAuthors = len(article['authors'])
        if (nAuthors != 1) and (nAuthors in self._authors):
            possibles_authors = possibles_authors.union(
                self._authors[nAuthors])
        possibles = possibles_authors.intersection(possibles_year)
        if not possibles:
            return(None)

        if ('title' in fields):
            possibles_title = set()
            tokens = tokens_from_sentence(article['title'])
            for token in tokens:
                if token in self._title:
                    possibles_title = possibles_title.union(self._title[token])

            # if we didn't find anything, dont filter by it
            if possibles_title:
                possibles_title = possibles_title.union(self._title[0])
                possibles = possibles.intersection(possibles_title)
                if not possibles:
                    return(None)

        if ('authors' in fields):
            possibles_authorName = set()
            for author in article['authors']:
                for name in author.last_names:
                    token = name.lower()
                    if token in self._authorName:
                        possibles_authorName = possibles_authorName.union(
                            self._authorName[token])

            # if we didn't find anything, dont filter by it
            if possibles_authorName:
                possibles_authorName = possibles_authorName.union(
                    self._authorName[0])
                possibles = possibles.intersection(possibles_authorName)
                if not possibles:
                    return(None)

        if ('journal' in fields):
            possibles_journal = set()
            tokens = tokens_from_sentence(article['journal'])
            for token in tokens:
                if token in self._journal:
                    possibles_journal = possibles_journal.union(
                        self._journal[token])

            # if we didn't find anything, dont filter by it
            if possibles_journal:
                possibles_journal = possibles_journal.union(self._journal[0])
                possibles = possibles.intersection(possibles_journal)
                if not possibles:
                    return(None)

        for n in possibles:
            if same_article(self.node[n]['data'], article):
                return(n)
        return(None)

    def find(self, article: dict):
        """
        Finds the node corresponding to article a.
        Adds, in place, if it isn't in the graph.
        Replaces the node if the new article has a DOI.
        """
        # find by DOI
        if ('doi' in article) and (article['doi'] is not None):
            if (article['doi'] in self):
                return(article['doi'])
            # we have that DOI, but replaced with another. We follow the path!
            if (article['doi'] in self._equivalentDOIs):
                eq = article['doi']
                while eq not in self:
                    eq = self._equivalentDOIs[eq]
            # article might be there, just not with a DOI yet
            return(self.add(article, self._find_article_no_doi(article)))

        # article doesnt have a DOI
        n = self._find_article_no_doi(article)
        if (n is not None):
            return(n)
        else:
            return(self.add(article))
    # @profile

    def cocitation(self, count_label: str='count', copy_data: bool=True, min_cocitations: int=1)->nx.Graph:
        """
        Builds a co-citation network from the citation network.
        G[n1][n2][count_label] stores the co-citation count. 
        "copy_data" determins if the ['data'] structure from the references will
        also be copied to the co-citation network.
        min_cocitations limits the co-citation network to consider only pairs with >= min_cocitations.

        If the citation network has more than 500k articles, min_cocitations rises to 2.
        """
        G = nx.Graph()
        print('Building co-citation')
        useful_nodes = [n for n in self if list(self.successors(n))]
        useful_targets = [n for n in self if len(
            list(self.predecessors(n))) >= min_cocitations]
        for citing in tqdm(useful_nodes):
            cited = [x for x in self.successors(citing) if x in useful_targets]
            for w1, w2 in combinations(cited, 2):
                G.add_edge(w1, w2)
                if count_label not in G[w1][w2]:
                    G[w1][w2][count_label] = 0
                G[w1][w2][count_label] += 1

        # removing isolated nodes
        G.remove_nodes_from([n for n in G if len(list(G.neighbors(n))) == 0])

        if (copy_data):
            for n in G:
                G.node[n]['data'] = {**self.node[n]['data']}

        return(G)

    def compute_keywords(self, number_of_words=20, keyword_label: str='keywords', citing_keywords_label: str='citing-keywords'):
        """
        For each article that has an abstract, compute the corresponding keywords
        and add them to the 'data' dictionary, under "keyword_label".
        The whole dataset is necessary to compute the idf part of tf-idf.
        """
        corpus = []
        stop_words = list(set(stopwords.words('english')+['do', 'and', 'among', 'findings', 'is', 'in', 'results', 'an', 'as', 'are', 'only', 'number',
                                                          'have', 'using', 'research', 'find', 'from', 'for', 'to', 'with', 'than', 'since', 'most',
                                                          'also', 'which', 'between', 'has', 'more', 'be', 'we', 'that', 'but', 'it', 'how', 'approaches', 'approach',
                                                          'they', 'not', 'article', 'on', 'data', 'by', 'a', 'both', 'this', 'of', 'studies', 'lens', 'analysis', 'take', 'took',
                                                          'their', 'these', 'social', 'the', 'or', 'may', 'whether', 'them'', only', 'limit',
                                                          'implication', 'our', 'less', 'who', 'all', 'based', 'less', 'was', 'vital', 'taken', 'wide', 'view',
                                                          'its', 'new', 'one', 'use', 'these', 'focus', 'result', 'test', 'property', 'properties',
                                                          'finding', 'relationship', 'different', 'their', 'more', 'between', 'supposed', 'another',
                                                          'article', 'study', 'paper', 'research', 'sample', 'effect', 'case', 'argue', 'three', 'upon',
                                                          'affect', 'extent', 'when', 'implications', 'been', 'data', 'even', 'examine', 'toward', 'particularly',
                                                          'effects', 'analysis', 'into', 'support', 'show', 'within', 'what', 'were', 'per', 'focusing', 'focus',
                                                          'associated', 'suggest', 'those', 'over', 'however', 'while', 'indicate', 'about', 'second', 'first',
                                                          'terms', 'processes', 'tactics', 'strategies', 'de', 'involved', 'issues', 'successful', 'unfinished',
                                                          'such', 'other', 'because', 'can', 'both', 'n', 'find', 'using', 'have', 'not', 'role', 'rather',
                                                          'some', 'likely', 'findings', 'but', 'results', 'among', 'has', 'how', 'which', 'understand',
                                                          'they', 'be', 'i', 'two', 'than', 'how', 'which', 'be', 'across', 'also', 'it', 'through', 'at']))
        lemmatizer = WordNetLemmatizer()
        useful_nodes = [n for n in self if ('data' in self.node[n]) and (
            'abstract' in self.node[n]['data']) and (len(self.node[n]['data']['abstract']) > 0)]

        for n in useful_nodes:
            lemmas = [lemmatizer.lemmatize(word.translate(remove_punct), pos='s').lower(
            ) for word in word_tokenize(self.node[n]['data']['abstract'])]
            corpus.append(" ".join([word for word in lemmas if (
                word not in stop_words) and (word != '')]))

        cv = CountVectorizer(max_df=0.85, stop_words=stop_words,
                             max_features=10000, ngram_range=(1, 3))
        X = cv.fit_transform(corpus)
        tfidf_transformer = TfidfTransformer(use_idf=False)
        tfidf_transformer.fit(X)
        # get feature names
        feature_names = cv.get_feature_names()

        for i, doc in enumerate(corpus):
            # generate tf-idf for the given document
            tf_idf_vector = tfidf_transformer.transform(cv.transform([doc]))
            # sort the tf-idf vectors by descending order of scores
            sorted_items = sort_coo(tf_idf_vector.tocoo())
            # extract only the top n
            self.node[useful_nodes[i]]['data'][keyword_label] = extract_topn_from_vector(
                feature_names, sorted_items, number_of_words)

        print('Citing keywords')
        for n in tqdm(self):
            keywords = []
            used_documents = 0
            for citing in self.predecessors(n):
                # not all citing articles have abstracts
                if keyword_label in self.node[citing]['data']:
                    used_documents += 1
                    keywords.extend(self.node[citing]['data'][keyword_label])
            if keywords:
                keywords = _merge_keywords(keywords, used_documents)
                if len(keywords) > number_of_words:
                    keywords = sorted(keywords, key=lambda x: x[1], reverse=True)[
                        :number_of_words]
            self.node[n]['data'][citing_keywords_label] = keywords
