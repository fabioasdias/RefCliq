
from tqdm import tqdm
from pybtex.database.input import bibtex
from pybtex.database import Person
from util import thous
import re
from titlecase import titlecase
from bibtex import parse

_citePattern=re.compile(r"{?(?P<author>[\w\s\.\(\)-]*?)]?(, (?P<year>\d{4}))?, (?P<journal>.*?)(, (?P<vol>V[\d]+))?(, (?P<page>P[\d]+))?(, [DOI ^,]+(?P<doi>10.\d{4,9}/[-._;()/:A-Z0-9]+))?((\. )|(\.})|(\.\Z)|(}\Z))", flags=re.IGNORECASE)
_listPattern=re.compile(r'\{\[\}(.*?)(,.*?)+\]')
def _cleanCurly(s:str)->str:
    """Removes curly braces"""
    return(s.replace('{',''). replace('}',''))

def _properName(name:str)->str:
    """
    Properly formats the reference name. While it understands van/der, it breaks
    for institution names, because we can't tell them apart from people's names.
    """        
    vals=name.split(' ')
    lasts=[vals[0].lower(),]
    i=1
    while (lasts[-1].lower() in ['de','der','von','van']):
        lasts.append(vals[i].lower())
        i+=1
    lasts[-1]=titlecase(lasts[-1])
    last=' '.join([w for w in lasts])
    rest=[]
    for v in vals[i:]:
        if all([c.isupper() for c in v]): #Initials - JE
            rest.extend([c for c in v])
        else:
            rest.append(titlecase(v.lower()))
    return(last+", "+' '.join(rest).replace(".",""))


def split_references(references:str)->list:
    """
    Generates a list of dictionaries with the info on the cited references.

    references: raw text from "cited-references" WoS's .bib
    return: [{author, year ,journal, vol, page, doi},]. None for missing values.
    """
    #removes the \_ from DOIs
    refs=references.replace(r"\_","_")
    #removes the non-list {[} ]
    refs=re.sub(r"\{\[\}([^,\]]*?)\]",r"\1",refs)
    #replaces inner lists {[} X, Y] with X
    refs=_listPattern.sub(r'\1',refs) 
    
    matches=_citePattern.finditer(refs)
    ret=[]
    for entry in matches:
        article={'authors' : [Person(string=_properName(entry.group('author'))),],
            'year' : entry.group('year'), 
            'journal' : titlecase(entry.group('journal')),
            'vol' : entry.group('vol'), 
            'inPress' : False,
            'page' : entry.group('page'), 
            'doi' : entry.group('doi')}
        ret.append(article)
    return(ret)

def extract_article_info(fields, people, references:list=None)->dict:
    """
    Creates a dict with the information from the bibtex fields.
    If "references" is passed, uses that to compute the references
    """

    abstract = _cleanCurly(fields.get('abstract',''))
    if ' (C) ' in abstract:
        abstract = abstract.split(' (C) ')[0]

    if (references is None):
        refs=split_references(fields.get("cited-references",[]))
    else:
        refs=[]
        for r in references:
            if ('in press' in r.lower()):
                better_ref=re.sub('in press','',r,flags=re.IGNORECASE)
                refs.append(split_references(better_ref)[0])
                refs[-1]['inPress']=True
            else:
                refs.append(split_references(r)[0])

    return {'Affiliation': fields.get('Affiliation',''),
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
    """
    Takes a list of bibtex files and returns entries as a list of dictionaries
    representing the info on each work
    """
    parser = bibtex.Parser()
    articles = []
    refName="Cited-References"
    for filename in tqdm(filelist):
        try:
            #since pybtex removes the \n from this field, we do it ourselves
            references=parse(filename,keepOnly=[refName,])
            for k in references:
                references[k][refName]=[x.strip() for x in references[k][refName].split('\n')]
            bibdata = parser.parse_file(filename)
        except:
            print('Error with the file ' + filename)
            raise
        else:
            for bib_id in bibdata.entries:
                articles.append(extract_article_info(bibdata.entries[bib_id].fields,
                                                bibdata.entries[bib_id].persons,
                                                references[bib_id][refName]))

    print('Imported %s articles.' % thous(len(articles)))
    return(articles)
