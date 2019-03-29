
from tqdm import tqdm
from pybtex.database.input import bibtex
from util import thous
import re

def _cleanCurly(s:str)->str:
    """Removes curly braces """
    return(s.replace('{',''). replace('}',''))


def word_proper(word:str)->str:
    #Title case, using small word list from that Daring Fireball guy.
    if word.lower() not in ['a','an','and','as','at','but','by','en','for','if','in','of','on','or','the','to']:
        return word[0].upper()+word[1:].lower()
    else:
        return word.lower()

def sentence_proper(text_string:str)->str:
    #title case a a whole sentence
    proper_string = ' '.join([word_proper(word) for word in text_string.split()])
    try:
        return proper_string[0].upper()+proper_string[1:]
    except:
        return
def r_author(reference):
    #Extra author information from reference. Doesn't work when author isn't straighforward (like Census)
    #Includes last name and  first initital of the author.
    author = reference[0].strip('.')
    author_split = author.split()
    author_last_name = author_split[0]
    author_last_name = word_proper(author_last_name)
    try:
        author_first_initial = author_split[1][0].upper()
    except:
        author_first_initial = ''
    # if author_last_name == "Granovet.ms":
    #     author_last_name = "Granovetter"
    #     author_first_initial = "M"
    return '%s %s' % (author_last_name, author_first_initial)

def r_year(reference):
    #Extra year from references. Returns nothing when year is not an integer, I think.
    for item in reference:
        try:
            year = int(item)
            return year
        except:
            pass
        if 'IN PRESS' in item:
            return 'In Press'
    return 'nd'
    #print(reference)

    return ''

def r_doi(reference):
    #extracts DOI from reference. I don't think I do anything with it though.
    if 'DOI ' in reference[-1]:
        return reference[-1].strip('DOI ')
    else:
        return ''

def r_title(reference):
    #cleans up title in reference
    #relies on the fact that the first year splits author from title
    for order,item in enumerate(reference):
        try:
            year = int(item)
            title = reference[order+1]
            return sentence_proper(title)
        except:
            pass
    return sentence_proper(reference[1])
    #return title

def split_references(references):
    #split references, correcting for the fact that '. ' is sometimes found within citations. Bastards.

    #removes the \_ from DOIs
    refs=references.replace(r"\_","_")
    #removes inner lists {[} X, Y] with X
    refs=re.sub('\{\[\}(.*?)(,.*?)+\]',r'\1',refs) 
    
    refs=refs.replace("{[}","[") #[Anonymous]
    #[:, /\-\w]+  // [ \w\.]+
    matches=re.finditer(r"{?(?P<author>.*?)]?, (?P<year>\d{4}), (?P<journal>.*?)(, (?P<vol>V[\d]+))?(, (?P<page>P[\d]+))?(,[DOI ]+(?P<doi>10.\d{4,9}/[-._;()/:A-Z0-9]+))?((\. )|(\.})|(\.\Z)|(}\Z))", refs, flags=re.IGNORECASE)
    for entry in matches:
        print('----------')
        print(entry.group('author'))
        print(entry.group('year'))
        print(entry.group('journal'))
        print(entry.group('vol'))
        print(entry.group('page'))
        print(entry.group('doi'))

        # input('.')
    # exit()



    references = references.split('. ')
    split_references = [r.split(', ') for r in references]
    cut = False
    new_references = []
    old_reference = []
    for reference in split_references[:]:
        original = reference
        if cut == True:
#            reference = [' '.join(old_reference) + '' + reference[0].replace('.','')] + reference[1:]
            reference = [' '.join(old_reference)] + reference[1:]
            #print(reference)

        if len(reference)<2:
            old_reference = old_reference + reference
            cut = True
        else:
            new_references.append(reference)
            old_reference = []
            cut = False

            if '()' in r_cite(reference):
                print(reference)
                print(r_cite(reference))
                print(references)
                print('\n'*5)


    return new_references


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

        title    = sentence_proper(_cleanCurly(fields.get("title",'No title')))
        journal  = sentence_proper(_cleanCurly(fields.get('series', fields.get('journal','') )))
        year     = _cleanCurly(fields.get('year',''))
        volume   = _cleanCurly(fields.get('volume',''))
        number   = _cleanCurly(fields.get('number','1'))
        pages    = _cleanCurly(fields.get('pages',''))
        abstract = _cleanCurly(fields.get('abstract',''))
        doi      = _cleanCurly(fields.get('doi',''))
        if ' (C) ' in abstract:
            abstract = abstract.split(' (C) ')[0]

        # try:
        references = [r_cite(r) for r in split_references(fields["cited-references"])]
        # except:
            # references = []
        # exit()

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

        cite = '%s. %s. "%s." %s. %s:%s %s.' % (author,
                                       year,
                                       title,
                                       journal,
                                       volume,
                                       number,
                                       pages)
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
