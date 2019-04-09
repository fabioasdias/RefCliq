from collections import Counter
from string import punctuation
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords as nltk_stopwords
from nltk import WordNetLemmatizer, download
from nltk.stem import snowball
import networkx as nx
from collections import Counter
from math import log
from tqdm import tqdm

download('stopwords')
download('punkt')
download('wordnet')

stemmer = snowball.EnglishStemmer()

def tokens_from_sentence(sentence:str, remove_duplicates:bool=True)->list:
    """
      Returns a list of "important" words in a sentence.
      Only works in English but returned tokens may not be proper English.
    """
    stop_words = nltk_stopwords.words('english')
    remove_punct=str.maketrans('', '', punctuation)
    words=[word.translate(remove_punct).lower() for word in word_tokenize(sentence)]
    words=[stemmer.stem(word) for word in words if (word not in stop_words) and (word!='')]
    if remove_duplicates:
      return(list(set(words)))
    else:
      return(words)

def compute_keywords_inplace(G: nx.DiGraph, number_of_words=5, keyword_label:str='keywords', citing_keywords_label:str='citing-keywords'):
    """
      For each article that has an abstract, compute the corresponding keywords
      and add them to the 'data' dictionary, under "keyword_label".
      The whole dataset is necessary to compute the idf part of tf-idf.
    """
    corpus={}
    tfs={}
    stop_words = nltk_stopwords.words('english')
    lemmatizer=WordNetLemmatizer()
    remove_punct = str.maketrans('', '', punctuation)
    idfs={}
    print('Computing tf-idf')
    for n in tqdm(G):
        if ('data' in G.node[n]) and ('abstract' in G.node[n]['data']) and (len(G.node[n]['data']['abstract']) > 0):
        # lemmas=[lemmatizer.lemmatize(word.translate(remove_punct)).lower() for word in tokens_from_sentence(G.node[n]['data']['abstract'],remove_duplicates=False)]
            lemmas=[lemmatizer.lemmatize(word.translate(remove_punct),pos='s').lower() for word in word_tokenize(G.node[n]['data']['abstract'])]
            corpus[n]=[word for word in lemmas if (word not in stop_words) and (word!='')]
            count=Counter(corpus[n])
            most=count.most_common(1)[0]
            tfs[n]={word:(count[word]/most[1]) for word in count}
            for word in count:
                idfs[word]=idfs.get(word,0)+1
    idfs={word:log(len(corpus)/(1+idfs[word])) for word in idfs}

    print('Keywords')
    for n in tqdm(tfs):
        G.node[n]['data'][keyword_label]=sorted([(w,tfs[n][w]*idfs[w]) for w in tfs[n]],key=lambda x:x[1],reverse=True)[:number_of_words]

    print('Citing keywords')
    for n in tqdm(G):
        keywords = []
        for citing in G.predecessors(n):
            if keyword_label in G.node[citing]['data']: #not all citing articles have abstracts
                keywords.extend(G.node[citing]['data'][keyword_label])
        if keywords:
            merged={}
            for k,v in keywords:
                if k not in merged:
                    merged[k]=v
                else:
                    merged[k]+=v
            keywords=[(k,merged[k]) for k in merged]
            if len(keywords) > number_of_words:
                keywords=sorted(keywords, key=lambda x:x[1], reverse=True)[:number_of_words]
        G.node[n]['data'][citing_keywords_label] = keywords
        
    
      

  
