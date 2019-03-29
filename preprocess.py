
from tqdm import tqdm
from pybtex.database.input import bibtex
from util import thous
import re
import titlecase


_citePattern=re.compile(r"{?(?P<author>.*?)]?, (?P<year>\d{4}), (?P<journal>.*?)(, (?P<vol>V[\d]+))?(, (?P<page>P[\d]+))?(,[DOI ]+(?P<doi>10.\d{4,9}/[-._;()/:A-Z0-9]+))?((\. )|(\.})|(\.\Z)|(}\Z))", flags=re.IGNORECASE)

def _cleanCurly(s:str)->str:
    """Removes curly braces """
    return(s.replace('{',''). replace('}',''))

def split_references(references):
    #split references, correcting for the fact that '. ' is sometimes found within citations. Bastards.
    print('split')
    #removes the \_ from DOIs
    refs=references.replace(r"\_","_")
    #removes inner lists {[} X, Y] with X
    refs=re.sub('\{\[\}(.*?)(,.*?)+\]',r'\1',refs) 
    
    refs=refs.replace("{[}","[") #[Anonymous]
    #[:, /\-\w]+  // [ \w\.]+
    matches=_citePattern.finditer(refs)

    return([{'author':entry.group('author'),
        'year':entry.group('year'),
        'journal':entry.group('journal'),
        'vol':entry.group('vol'),
        'page':entry.group('page'),
        'doi':entry.group('doi')} for entry in matches])        

def r_cite(reference):
    #Create a relatively unique name based on author, year and title.
    try:
        author = r_author(reference)
        year = r_year(reference)
        title = r_title(reference)
        return ('%{0} (%{1}) %{1}'.format(author,year,title)).replace('.','')
    except:
        return ''


def extract_article_info(fields, people):
        #grabs article info from a bibtex cite and returns some of the fields in a dictionary

        title    = titlecase(_cleanCurly(fields.get("title",'No title')))
        journal  = titlecase(_cleanCurly(fields.get('series', fields.get('journal','') )))
        year     = _cleanCurly(fields.get('year',''))
        volume   = _cleanCurly(fields.get('volume',''))
        number   = _cleanCurly(fields.get('number','1'))
        pages    = _cleanCurly(fields.get('pages',''))
        abstract = _cleanCurly(fields.get('abstract',''))
        doi      = _cleanCurly(fields.get('doi',''))
        if ' (C) ' in abstract:
            abstract = abstract.split(' (C) ')[0]

        references = split_references(fields.get("cited-references",[]))
        print(references)

        try:
            authors_raw = people["author"]
            author = '%s, %s' % ( authors_raw[0].last_names()[0], authors_raw[0].first_names()[0] )
            if len(authors_raw)>2:
                for a in authors_raw[1:-1]:
                    author = '%s, %s %s' % (author,a.first_names()[0],a.last_names()[0])
            if len(authors_raw)>1:
                author = '%s & %s %s' % (author,authors_raw[-1].first_names()[0],authors_raw[-1].last_names()[0])
        except:
            author = "None"

        cite = '%s. %s. "%s." %s. %s:%s %s.' % (author, year, title, journal, volume, number, pages)
        return {'cite' : cite,
                'Affiliation': fields.get('Affiliation',''),
                'year': year,
                'doi' : doi,
                'title' : title,
                'journal' : journal,
                'volume' : volume,
                'pages' : pages,
                'references' : references,
                'number' : number,
                'abstract' : abstract }

def import_bibs(filelist:list) -> list:
    #Takes a list of bibtex files and returns entries as a list of dictionaries
    parser = bibtex.Parser()
    entered = {}
    #take a list of files in bibtex format and returns a list of articles
    articles = []
    refs=[]
    for filename in tqdm(filelist):
        # print('Importing from ' + filename)
        try:
            bibdata = parser.parse_file(filename)
        except:
            print('Error with the file ' + filename)
        else:
            for bib_id in bibdata.entries:
                article=extract_article_info(bibdata.entries[bib_id].fields,
                                             bibdata.entries[bib_id].persons)
                if article['cite'] not in entered and len(article['references']) > 2:
                    articles.append(article)
                    entered[article['cite']]=True

    print('Imported %s articles.' % thous(len(articles)))
    return(articles)
