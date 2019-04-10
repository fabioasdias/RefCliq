from string import punctuation
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords 
from nltk import download
from nltk.stem import snowball
import networkx as nx
from tqdm import tqdm

download('stopwords')
download('punkt')


stemmer = snowball.EnglishStemmer()

def tokens_from_sentence(sentence:str, remove_duplicates:bool=True)->list:
    """
      Returns a list of "important" words in a sentence.
      Only works in English but returned tokens may not be proper English.
    """
    stop_words = stopwords.words('english')
    remove_punct=str.maketrans('', '', punctuation)
    words=[word.translate(remove_punct).lower() for word in word_tokenize(sentence)]
    words=[stemmer.stem(word) for word in words if (word not in stop_words) and (word!='')]
    if remove_duplicates:
      return(list(set(words)))
    else:
      return(words)