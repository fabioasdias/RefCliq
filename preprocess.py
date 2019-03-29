
from tqdm import tqdm
from pybtex.database.input import bibtex
from pybtex.database import Person
from util import thous
import re
from titlecase import titlecase


_citePattern=re.compile(r"{?(?P<author>[\w\s\.]*?)]?, (?P<year>\d{4}), (?P<journal>.*?)(, (?P<vol>V[\d]+))?(, (?P<page>P[\d]+))?(, [DOI ^,]+(?P<doi>10.\d{4,9}/[-._;()/:A-Z0-9]+))?((\. )|(\.})|(\.\Z)|(}\Z))", flags=re.IGNORECASE)
_listPattern=re.compile(r'\{\[\}(.*?)(,.*?)+\]')
def _cleanCurly(s:str)->str:
    """Removes curly braces"""
    return(s.replace('{',''). replace('}',''))

def split_references(references:str)->list:
    """
    Generates a list of dictionaries with the info on the cited references.

    references: raw text from "cited-references" WoS's .bib
    return: [{author, year ,journal, vol, page, doi},]. None for missing values.
    """
    #removes the \_ from DOIs
    refs=references.replace(r"\_","_")
    print('-')
    print(refs)
    refs=re.sub(r"\{\[\}([^,]*?)\]",r"\1",refs)
    #removes inner lists {[} X, Y] with X
    print('.')
    print(refs)
    refs=_listPattern.sub(r'\1',refs) 
    print('..')
    
    # refs=refs.replace("{[}","[") #[Anonymous]
    #[:, /\-\w]+  // [ \w\.]+
    matches=_citePattern.finditer(refs)
    ret=[]
    for entry in matches:
        ret.append({'author':Person(string=titlecase(entry.group('author'))),
        'year':entry.group('year'), 
        'journal':titlecase(entry.group('journal')),
        'vol':entry.group('vol'), 
        'page':entry.group('page'), 
        'doi':entry.group('doi')})
        print(ret[-1])
        input('.')
    return(ret)

def _makeID(article):
    if (article['doi'] is not None):
        return(article['doi'])
    ret=', '.join([x.last_names for x in article['authors']])+'. '+article['year']+'. '+article['title']

def extract_article_info(fields, people)->dict:
        #grabs article info from a bibtex cite and returns some of the fields in a dictionary

        abstract = _cleanCurly(fields.get('abstract',''))
        if ' (C) ' in abstract:
            abstract = abstract.split(' (C) ')[0]

        # print(people["author"])
        # for p in people['author']:
        #     print(p.last_names,p.first_names,p.middle_names)
        #     print(' '.join([x[0].upper()+'.' for x in p.first_names+p.middle_names]))
            

        # authors_raw = people["author"]
        # author = '%s, %s' % ( authors_raw[0].last_names[0], authors_raw[0].first_names[0] )
        # if len(authors_raw)>2:
        #     for a in authors_raw[1:-1]:
        #         author = '%s, %s %s' % (author,a.first_names[0],a.last_names[0])
        # if len(authors_raw)>1:
        #     author = '%s & %s %s' % (author,authors_raw[-1].first_names[0],authors_raw[-1].last_names[0])

        # print(author)
        # exit()

        # cite = '%s. %s. "%s." %s. %s:%s %s.' % (author, year, title, journal, volume, number, pages)
        refs=split_references(fields.get("cited-references",[]))
        print(refs)
        return {#'cite' : cite,
                'Affiliation': fields.get('Affiliation',''),
                'authors': people,
                'year': _cleanCurly(fields.get('year','')),
                'doi' : _cleanCurly(fields.get('doi','')).lower(),
                'title' : _cleanCurly(fields.get("title",'No title')),
                'journal' : _cleanCurly(fields.get('series', fields.get('journal','') )),
                'volume' : _cleanCurly(fields.get('volume','')),
                'pages' : _cleanCurly(fields.get('pages','')),
                'references' : refs,
                'number' : _cleanCurly(fields.get('number','1')),
                'abstract' : abstract }

def import_bibs(filelist:list) -> list:
    #Takes a list of bibtex files and returns entries as a list of dictionaries
    parser = bibtex.Parser()
    #take a list of files in bibtex format and returns a list of articles
    articles = {}
    for filename in tqdm(filelist):
        try:
            bibdata = parser.parse_file(filename)
        except:
            print('Error with the file ' + filename)
            raise
        else:
            for bib_id in bibdata.entries:
                article=extract_article_info(bibdata.entries[bib_id].fields,
                                             bibdata.entries[bib_id].persons)
                aid=_makeID(article)
                articles[aid]=article
                if (not aid.startswith('10.')):
                    print(article)
                    print(aid)
                    input('.')
                # if article['cite'] not in entered and len(article['references']) > 2:
                #     articles.append(article)
                #     entered[article['cite']]=True

    print('Imported %s articles.' % thous(len(articles)))
    return(articles)
