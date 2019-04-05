from collections import Counter
from nltk import stem
from string import punctuation
from nltk.tokenize import word_tokenize

# Load library
from nltk.corpus import stopwords as nltk_stopwords

# You will have to download the set of stop words the first time
import nltk

nltk.download('stopwords')
nltk.download('punkt')

stemmer = stem.snowball.EnglishStemmer()

def tokens_from_sentence(sentence:str)->list:
    """
      Returns a list of "important" words in a sentence.
      Only works in english.
    """
    stop_words = nltk_stopwords.words('english')
    words=[word.strip(punctuation).lower() for word in word_tokenize(sentence)]
    words=[stemmer.stem(word) for word in words if (word not in stop_words) and (word!='')]
    return(list(set(words)))


#Stemmer for cleaning abstracts

def stem_word(word):
    return stemmer.stem(word)

def split_and_clean(sentence):
    #turn string into a list of unique, lower-cased words
    # punctuation = '''!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~'''
    words = [str(w.strip(punctuation).lower()) for w in sentence.split()]
    return list(set(words))

def make_word_freq(list_of_texts):
    #returns the % of documents containing each word
    document_count =float(len(list_of_texts))
    #Split and clean each of the texts.
    list_of_texts = [split_and_clean(text) for text in list_of_texts]
    #flatten list
    words = [word for text in list_of_texts for word in text if len(word)>1 ]
    # % of docuemnts that have each word.

    #I've resisted using collections.Counter but it is really fast.
    word_counts = Counter(words)
    word_freq = {word : (word_counts[word]/document_count) for word in word_counts}
    return word_freq

def clean_abstract(abstract):
    #takes a string and returns a list of unique words minus punctation.
    #Stemming should probably be an option, not a requirement
    words = list(set([ stem_word(word.strip(punctuation)) for word in abstract.lower().split()]))
    words = [w for w in words if len(w)>0]
    return words

def stopwords(articles, minfreq =.2):
    #list of commonly occuring words. You need to set the threshold low for most small texts.
    abstracts = [article['abstract'] for article in articles if len(article['abstract']) > 0 ]
    word_freq = make_word_freq(abstracts)
    stop_words = list(set(word for word in word_freq if word_freq[word] > minfreq ))
    return stop_words

def keywords(abstracts,stopword_list,n=10):
    #abstracts = [article['abstract'] for article in articles if len(article['abstract']) > 0 ]
    word_freq = make_word_freq(abstracts)
    word_freq = {w : word_freq[w] for w in word_freq if w not in stopword_list}
    top_words = sorted(word_freq, key=word_freq.get, reverse=True)[:n]
    return top_words

def get_stopwords()->list:
    return(['do','and', 'among', 'findings', 'is', 'in', 'results', 'an', 'as', 'are', 'only', 'number',
              'have', 'using', 'research', 'find', 'from', 'for', 'to', 'with', 'than', 'since','most',
             'also', 'which', 'between', 'has', 'more', 'be', 'we', 'that', 'but', 'it', 'how',
             'they', 'not', 'article', 'on', 'data', 'by', 'a', 'both', 'this', 'of', 'study', 'analysis',
             'their', 'these', 'social', 'the', 'or','may', 'whether', 'them'', only',
             'implication','our','less','who','all','based','less','was',
           'its','new','one','use','these','focus','result','test',
           'finding','relationship','different','their','more','between',
           'article','study','paper','research','sample','effect','case','argue','three',
           'affect','extent','when','implications','been','data','even','examine','toward',
           'effects','analysis','into','support','show','within','what','were',
           'associated','suggest','those','over','however','while','indicate','about',
           'such','other','because','can','both','n','find','using','have','not',
           'some','likely','findings','but','results','among','has','how','which',
           'they','be','i','two','than','how','which','be','across','also','it','through','at'])

def cite_keywords(cite, stopword_list, articles, n = 5):
    words_ab= [article.get('abstract') for article in articles if cite in article['references']]
    words_title= [article.get('title') for article in articles if cite in article['references'] and len(article.get('abstract'))<5 ]
    words = words_title + words_ab
    
    stopwords= get_stopwords()
    stopword_list = stopword_list + stopwords
    cite_words = keywords(words,stopword_list,n=n)
    return cite_words
