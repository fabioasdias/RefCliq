import networkx as nx
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

from src.refcliq.geocoding import ArticleGeoCoder
from src.refcliq.textprocessing import tokens_from_sentence

download('wordnet')

class CitationNetwork(nx.DiGraph):
    def __init__(self, articles:list=None, geocode:bool=True):
        nx.DiGraph.__init__(self)
        # self._G=nx.DiGraph() #the network
        self._year={'None':[]}        #indexes
        self._authors={1:[]}
        self._journal={0:[]}
        self._title={0:[]}
        self._authorName={0:[]} #None might be a part of a name
        self._equivalentDOIs={} #yes, one paper can have more than one DOI
        if articles:
            self.build(articles, geocode)


    

    def build(self, articles:list, geocode:bool=True):
        """
        Builds a directed graph to represent the citation network in the list of
        articles.
        """
        if geocode:
            gc=ArticleGeoCoder()


        print('citation network - Full citation in the .bibs')
        for article in tqdm(articles):
            citing=self.find(article)
        if geocode:
            gc.add_authors_location_inplace(self)
            print('Nominatim calls ', gc._nominatim_calls)

        print('citation network - Cited-References')            
        for article in tqdm(articles):
            citing=self.find(article)
            for cited_article in article['references']:
                cited=self.find(cited_article)
                self.add_edge(citing,cited)

    def add(self, article:dict, replaceNode:str=None)->str:
        """
        Adds a new citation to the network.
        if replaceNode is given, replaces that node in the network
        (this is used to update the name to use a previously unknown DOI)

        Returns the node.
        """

        if ('doi' in article) and (article['doi'] is not None):
            ID=article['doi']
            if replaceNode:
                # print('Replacing {0} with {1}'.format(replaceNode,ID))
                n=replaceNode
                if n[0] != '-': #aka this is already a DOI!
                    self._equivalentDOIs[ID]=n #mark as equivalent
                    return(n) #short-circuits the rest


                for nn in self.predecessors(n):
                    self.add_edge(nn,ID)
                for nn in self.successors(n):
                    self.add_edge(ID,nn)
                #removes from the indexes
                self._year[self.node[n]['index']['year']].remove(n)
                self._authors[self.node[n]['index']['authors']].remove(n)
                for index in self.node[n]['index']['journal']:
                    self._journal[index].remove(n)
                for index in self.node[n]['index']['title']:
                    self._title[index].remove(n)
                for index in self.node[n]['index']['name']:
                    self._authorName[index].remove(n)

                for field in [f for f in self.node[n]['data'] if self.node[n]['data'][f]]:
                    if (field=='abstract') and (self.node[n]['data'][field]!='') and (article[field]==''):
                        article[field]=self.node[n]['data'][field]
                    elif (field=='authors') and len(self.node[n]['data']['authors'])>len(article['authors']):
                        article['authors']=self.node[n]['data']['authors'][:]
                    elif (field not in article) or (not article[field]):
                        article[field]=self.node[n]['data'][field]

                self.remove_node(n)
        else:
            ID='-'+str(len(self.nodes())) #flags as non-DOI

        self.add_node(ID)
        self.node[ID]['data']=article

        #store which index in the node to make update easier
        self.node[ID]['index']={}

        # if ('doi' not in article) or (article['doi'] is None):
        #     self._noDOI.append(ID)

        if 'year' in article:
            yearIndex=article['year']
            self.node[ID]['index']['year']=yearIndex
            if yearIndex not in self._year:
                self._year[yearIndex]=[]
            self._year[yearIndex].append(ID)
        else:
            self.node[ID]['index']['year']='None'
            self._year['None'].append(ID)

        #authors is the only field that always exists.
        authorIndex=len(article['authors'])
        self.node[ID]['index']['authors']=authorIndex
        if authorIndex not in self._authors:
            self._authors[authorIndex]=[]
        self._authors[authorIndex].append(ID)
        
        if ('journal' in article) and (article['journal'] is not None):
            tokens=tokens_from_sentence(article['journal'])
            self.node[ID]['index']['journal']=tokens
            for token in tokens:
                if token not in self._journal:
                    self._journal[token]=[]
                self._journal[token].append(ID)
        else:
            self._journal[0].append(ID)
            self.node[ID]['index']['journal']=[0,]

        if ('title' in article) and (article['title'] is not None):
            tokens=tokens_from_sentence(article['title'])
            self.node[ID]['index']['title']=tokens
            for token in tokens:
                if token not in self._title:
                    self._title[token]=[]
                self._title[token].append(ID)
        else:
            self._title[0].append(ID)
            self.node[ID]['index']['title']=[0,]

        if ('authors' in article) and len(article['authors'])>0:
            self.node[ID]['index']['name']=[]
            for author in article['authors']:
                for name in author.last_names:
                    token=name.lower()
                    self.node[ID]['index']['name'].append(token)
                    if token not in self._authorName:
                        self._authorName[token]=[]
                    self._authorName[token].append(ID)
        else:#no authors
            self._authorName[0].append(ID)
            self.node[ID]['index']['name']=[0,]
        return(ID)

    def _find_article_no_doi(self, article:dict):
        """
        Finds the article without using the DOI
        """
        fields=[k for k in article if (article[k])]        

        possibles_year=self._year['None'][:]
        if ('year' in fields) and (article['year'] in self._year):
            possibles_year.extend(self._year[article['year']][:])
        if not possibles_year:
            return(None)
        possibles_year=set(possibles_year)

        possibles_authors=self._authors[1][:]
        nAuthors=len(article['authors'])
        if (nAuthors!=1) and (nAuthors in self._authors):
            possibles_authors.extend(self._authors[nAuthors][:])
        if not possibles_authors:
            return(None)        
        possibles_authors=set(possibles_authors)

        possibles=possibles_authors.intersection(possibles_year)
        if not possibles:
            return(None)

        if ('journal' in fields):
            possibles_journal=[]
            tokens=tokens_from_sentence(article['journal'])
            for token in tokens:
                if token in self._journal:
                    possibles_journal.extend(self._journal[token][:])

            #if we didn't find anything, dont filter by it
            if possibles_journal:
                possibles_journal.extend(self._journal[0][:])
                possibles_journal=set(possibles_journal)
                possibles=possibles.intersection(possibles_journal)
                if not possibles:
                    return(None)

        if ('title' in fields):
            possibles_title=[]
            tokens=tokens_from_sentence(article['title'])
            for token in tokens:
                if token in self._title:
                    possibles_title.extend(self._title[token][:])

            #if we didn't find anything, dont filter by it
            if possibles_title:
                possibles_title.extend(self._title[0][:])
                possibles_title=set(possibles_title)
                possibles=possibles.intersection(possibles_title)
                if not possibles:
                    return(None)

        if ('authors' in fields):
            possibles_authorName=[]
            for author in article['authors']:
                for name in author.last_names:
                    token=name.lower()
                    if token in self._authorName:
                        possibles_authorName.extend(self._authorName[token][:])

            #if we didn't find anything, dont filter by it
            if possibles_authorName:
                possibles_authorName.extend(self._authorName[0][:])
                possibles_authorName=set(possibles_authorName)
                possibles=possibles.intersection(possibles_authorName)
                if not possibles:
                    return(None)

        for n in possibles: 
            if same_article(self.node[n]['data'],article):
                return(n)
        return(None)

    def find(self, article: dict):
        """
        Finds the node corresponding to article a.
        Adds, in place, if it isn't in the graph.
        Replaces the node if the new article has a DOI.
        """
        #find by DOI
        if ('doi' in article) and (article['doi'] is not None):
            if (article['doi'] in self):
                return(article['doi'])
            #we have that DOI, but replaced with another. We follow the path!
            if (article['doi'] in self._equivalentDOIs):
                eq=article['doi']
                while eq not in self:
                    eq=self._equivalentDOIs[eq]
            #article might be there, just not with a DOI yet                                    
            return(self.add(article,self._find_article_no_doi(article)))

        #article doesnt have a DOI
        n=self._find_article_no_doi(article)
        if (n is not None):
            return(n)
        else:
            return(self.add(article))

    def cocitation(self, count_label:str='count', copy_data:bool=True)->nx.Graph:
        """
        Builds a co-citation network from the citation network.
        G[n1][n2][count_label] stores the co-citation count. 
        "copy_data" determins if the ['data'] structure from the references will
        also be copied to the co-citation network.
        """
        G=nx.Graph()
        print('Building co-citation')
        useful_nodes=[n for n in self if list(self.successors(n))]
        for citing in tqdm(useful_nodes):
            cited=list(self.successors(citing))
            for w1,w2 in combinations(cited,2):
                G.add_edge(w1,w2)
                if count_label not in G[w1][w2]:
                    G[w1][w2][count_label]=0
                G[w1][w2][count_label]+=1

        #removing isolated nodes
        G.remove_nodes_from([n for n in G if len(list(G.neighbors(n)))==0])
        if (copy_data):
            for n in G:
                G.node[n]['data']={**self.node[n]['data']}

        return(G)

    # this needs to be done in the interface, otherwise it loses consistency with the count threshold

    # def subgraph_keywords(self, nbunch:list, keyword_label:str='keywords', number_of_words:int=20)->list:
    #     """
    #         Computes the top 'number_of_words' keywords considering only the publications in nbunch
    #     """
    #     keywords=[]
    #     used=0
    #     for n in nbunch:
    #         if keyword_label in self.node[n]['data']:
    #             used+=1
    #             keywords.extend(self.node[n]['data'][keyword_label])
    #     return(_merge_keywords(keywords, used))

    def compute_keywords(self, number_of_words=20, keyword_label:str='keywords', citing_keywords_label:str='citing-keywords'):
        """
        For each article that has an abstract, compute the corresponding keywords
        and add them to the 'data' dictionary, under "keyword_label".
        The whole dataset is necessary to compute the idf part of tf-idf.
        """
        corpus={}
        tfs={}
        stop_words = stopwords.words('english')
        lemmatizer=WordNetLemmatizer()
        remove_punct = str.maketrans('', '', punctuation)
        idfs={}
        useful_nodes=[n for n in self if ('data' in self.node[n]) and ('abstract' in self.node[n]['data']) and (len(self.node[n]['data']['abstract']) > 0)]
        print('Computing tf')
        for n in tqdm(useful_nodes):
            lemmas=[lemmatizer.lemmatize(word.translate(remove_punct),pos='s').lower() for word in word_tokenize(self.node[n]['data']['abstract'])]
            corpus[n]=[word for word in lemmas if (word not in stop_words) and (word!='')]
            corpus[n]=bigrams(corpus[n])
            count=Counter(corpus[n])
            most=count.most_common(1)[0]
            tfs[n]={word:(count[word]/most[1]) for word in count}
            for word in count:
                idfs[word]=idfs.get(word,0)+1
        idfs={word:log(len(corpus)/(1+idfs[word])) for word in idfs}

        print('Keywords')
        for n in tqdm(tfs):#*idfs[w]
            self.node[n]['data'][keyword_label]=sorted([(w,tfs[n][w]) for w in tfs[n]],key=lambda x:x[1],reverse=True)[:number_of_words]

        print('Citing keywords')
        for n in tqdm(self):
            keywords = []
            used_documents=0
            for citing in self.predecessors(n):
                if keyword_label in self.node[citing]['data']: #not all citing articles have abstracts
                    used_documents+=1
                    keywords.extend(self.node[citing]['data'][keyword_label])
            if keywords:
                keywords=_merge_keywords(keywords, used_documents)
                if len(keywords) > number_of_words:
                    keywords=sorted(keywords, key=lambda x:x[1], reverse=True)[:number_of_words]
            self.node[n]['data'][citing_keywords_label] = keywords



def _merge_keywords(keywords:list, how_many_works:int)->list:
    """
        Removes duplicate keywords from a list, updating the tf-idf (summing the
        occurences). How_many_works is used to re-normalize the values.
    """
    merged={}
    for k,v in keywords:
        if k not in merged:
            merged[k]=v
        else:
            merged[k]+=v
    return([(k,merged[k]/how_many_works) for k in merged])


def same_article(a1:dict, a2:dict)->bool:
    """
    Tests if two articles are the same based on their info. 

    Uses fuzzy string matching and the Person structure from pybtex.
    """

    usefulFields=list(set([k for k in a1 if a1[k]]).intersection(set([k for k in a2 if a2[k]])))

    if 'year' in usefulFields:
        if (a1['year']!=a2['year']):
            return(False)

    # two articles can have the same doi! 
    # if 'doi' in usefulFields:
    #     if (a1['doi']!=a2['doi']):
    #         return(False)


    #article from references only have one author that we know of
    L1=len(a1['authors'])
    L2=len(a2['authors'])
    if (L1!=1) and (L2!=1) and (L1!=L2):
        return(False)
    
    for i in range(min([L1,L2])):
        if (ratio(str(a1['authors'][i]),str(a2['authors'][i]))<=80) and (ratio(' '.join(a1['authors'][i].last_names),' '.join(a2['authors'][i].last_names))<=80):
            return(False)

    for field in ['title','journal','page','vol']:
        if (field in usefulFields) and (ratio(a1[field],a2[field])<=80):
            return(False)

    return(True)