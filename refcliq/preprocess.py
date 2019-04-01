
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
    if not s:
        return(s)
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


def split_reference(reference:str)->dict:
    """
    Generates a dictionary with the info present on the _single_ reference line.

    references: raw text from "cited-references" WoS's .bib (with \n!)
    return: {author, year ,journal, vol, page, doi}. None for missing values.
    """
    #removes the \_ from DOIs
    ref=reference.replace(r"\_","_")
    #removes the non-list {[} ]
    ref=re.sub(r"\{\[\}([^,\]]*?)\]",r"\1",ref)
    #replaces inner lists {[} X, Y] with X
    ref=_listPattern.sub(r'\1',ref) 
    
    match=_citePattern.search(ref)
    
    if match:
        article={'authors' : [Person(string=_properName(match.group('author'))),],
            'year' : match.group('year'), 
            'journal' : titlecase(match.group('journal')),
            'vol' : match.group('vol'), 
            'inPress' : False,
            'page' : match.group('page'), 
            'doi' : match.group('doi')}
    # we know this is a reference. It might be only the name of the publication
    else:
        article={'authors':[],
                 'journal': titlecase(reference),
                 'year':None,
                 'vol': None,
                 'inPress': False,
                 'page':None,
                 'doi':None
                 }
    return(article)

def extract_article_info(fields, people, references:list)->dict:
    """
    Creates a dict with the information from the bibtex fields.
    "references" is the raw Cited-References field from WoS' with \n s
    """

    abstract = _cleanCurly(fields.get('abstract',''))
    if ' (C) ' in abstract:
        abstract = abstract.split(' (C) ')[0]

    refs=[]
    for r in references:
        if ('in press' in r.lower()):
            better_ref=re.sub('in press','',r,flags=re.IGNORECASE)
            refs.append(split_reference(better_ref))
            refs[-1]['inPress']=True
        else:
            refs.append(split_reference(r))

    doi=fields.get('doi',None)
    if doi:
        doi=_cleanCurly(doi.lower())

    return {'Affiliation': fields.get('Affiliation',''),
            'authors': people.get("author",[]),
            'year': _cleanCurly(fields.get('year',None)),
            'doi' : doi,
            'title' : _cleanCurly(fields.get("title",None)),
            'journal' : _cleanCurly(fields.get('series', fields.get('journal',None) )),
            'volume' : _cleanCurly(fields.get('volume',None)),
            'pages' : _cleanCurly(fields.get('pages',None)),
            'references' : refs,
            'number' : _cleanCurly(fields.get('number',None)),
            'abstract' : abstract }

def import_bibs(filelist:list) -> list:
    """
    Takes a list of bibtex files and returns entries as a list of dictionaries
    representing the info on each work
    """
    articles = []
    references_field="Cited-References"
    for filename in tqdm(filelist):
        try:
            #since pybtex removes the \n from this field, we do it ourselves
            references=parse(filename,keepOnly=[references_field,])
            for k in references:
                if (references_field not in references[k]):
                    references[k][references_field]=[]
                else:
                    references[k][references_field]=[x.strip() for x in references[k][references_field].split('\n')]

            bibdata = {}
            parser = bibtex.Parser()
            bibdata = parser.parse_file(filename)

            for bib_id in bibdata.entries:
                # print(filename,bib_id)
                articles.append(extract_article_info(bibdata.entries[bib_id].fields,
                                                bibdata.entries[bib_id].persons,
                                                references[bib_id][references_field]))

        except:
            print('Error with the file ' + filename)
            print(bib_id,filename)
            raise

    print('Imported %s articles.' % thous(len(articles)))
    return(articles)
