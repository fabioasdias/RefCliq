from tqdm import tqdm
from pybtex.database.input import bibtex
from pybtex.database import Person
import re
from titlecase import titlecase
from refcliq.bibtex import parse
from refcliq.util import thous, cleanCurlyAround

# _citePattern=re.compile(r"{?(?P<author>[\w\s\.\(\)-]*?)]?(, (?P<year>\d{4}))?, (?P<journal>.*?)(, (?P<vol>V(, )?[^,]+))?(, (?P<page>P(, )?[^,]+))?(, [DOI ^,]+(?P<doi>10.( )*\d{4,9}/[ ,._;()/<>:#\\A-Z0-9\-\+]*))?((\. )|(\.})|(\.\Z)|(}\Z))", flags=re.IGNORECASE)
_citePattern=re.compile(r"{?(?P<author>[\w\s\.\(\)-]*?)?(, )?(?P<year>\d{4})?(, (?P<journal>.*?))(, (?P<vol>V[, ]*[^,]+))?(, (?P<page>P[, ]*[^,]+))?(, [DOIRG/ ^,]+(?P<doi>.*))?((\. )|(\.})|(\.\Z)|(}\Z))", flags=re.IGNORECASE)
_listPattern=re.compile(r'\{\[\}(.*?)(,.*?)+\]')

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

def dict_update_notNone_inplace(D:dict,k:any,val:any):
    """
        Adds the pair (k,val) to the dictionary D if val is not None.
        This helps keep the resulting json smaller (by not adding a bunch of null keys).
    """
    if val is not None:
        D[k]=val

def split_reference(reference:str)->dict:
    """
    Generates a dictionary with the info present on the _single_ reference line.

    references: raw text from "cited-references" WoS's .bib (with \n!)
    return: {author, year ,journal, vol, page, doi}, if they are not null.
    """
    #removes the \_ from DOIs
    ref=reference.replace(r"\_","_")
    #removes the non-list {[} ]
    ref=re.sub(r"\{\[\}([^,\]]*?)\]",r"\1",ref)
    #replaces inner lists {[} X, Y] with X
    ref=_listPattern.sub(r'\2',ref)  #the first part is usually the same but in chinese/etc
    
    match=_citePattern.search(ref)
    if match:
        doi = match.group('doi')
        if doi:#removes whitespaces in the DOI, yes, we have them
            doi=doi.translate(str.maketrans('','',' '))

        article={'authors' : [Person(string=_properName(match.group('author'))),]}
        dict_update_notNone_inplace(article, 'year', match.group('year'))
        dict_update_notNone_inplace(article, 'journal',titlecase(match.group('journal')))
        dict_update_notNone_inplace(article, 'vol', match.group('vol'))
        dict_update_notNone_inplace(article, 'page', match.group('page'))
        dict_update_notNone_inplace(article, 'doi', doi)
    # we know this is a reference. It might be only the name of the publication
    else:
        article={'authors':[],
                 'journal': titlecase(reference),
                 }
    return(article)

def extract_article_info(fields, people, references:list)->dict:
    """
    Creates a dict with the information from the bibtex fields.
    "references" is the raw Cited-References field from WoS' with \n s
    """

    abstract = cleanCurlyAround(fields.get('abstract',''))
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

    doi=fields.get('doi', None)
    if doi:
        doi=cleanCurlyAround(doi.lower())
        
    affiliation = fields.get('Affiliation',None)
    if affiliation:
        affiliation=cleanCurlyAround(affiliation).replace(r'\&','&')
    
    ret={'authors': people.get("author",[])}
    dict_update_notNone_inplace(ret, 'Affiliation', affiliation)
    dict_update_notNone_inplace(ret, 'year', cleanCurlyAround(fields.get('year', None)))
    dict_update_notNone_inplace(ret, 'doi', doi)
    dict_update_notNone_inplace(ret, 'title', titlecase(cleanCurlyAround(fields.get("title", None))))
    dict_update_notNone_inplace(ret, 'journal', titlecase(cleanCurlyAround(fields.get('series', fields.get('journal', None) ))))
    dict_update_notNone_inplace(ret, 'volume', cleanCurlyAround(fields.get('volume', None)))
    dict_update_notNone_inplace(ret, 'pages', cleanCurlyAround(fields.get('pages', None)))
    dict_update_notNone_inplace(ret, 'references', refs)
    dict_update_notNone_inplace(ret, 'number', cleanCurlyAround(fields.get('number', None)))
    dict_update_notNone_inplace(ret, 'abstract', abstract )
    return(ret)

def import_bibs(filelist:list) -> list:
    """
    Takes a list of bibtex files and returns entries as a list of dictionaries
    representing the info on each work
    """
    articles = []
    references_field="Cited-References"
    print('Reading .bibs')
    for filename in tqdm(filelist):
        try:
            #since pybtex removes the \n from this field, we do it ourselves
            #(but we are not fully replacing pybtex because of the extra consistency checks it has)
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
                articles.append(extract_article_info(bibdata.entries[bib_id].fields,
                                                bibdata.entries[bib_id].persons,
                                                references[bib_id][references_field]))

        except:
            print('Error with the file ', filename)
            raise

    print('Imported {0} articles.'.format(thous(len(articles))))
    return(articles)
