from nltk import stem

#Stemmer for cleaning abstracts
stemmer = stem.snowball.EnglishStemmer()
def stem_word(word):
    return stemmer.stem(word)

def word_proper(word):
    #Title case, using small word list from that Daring Fireball guy.
    if word.lower() not in ['a','an','and','as','at','but','by','en','for','if','in','of','on','or','the','to']:
        return word[0].upper()+word[1:].lower()
    else:
        return word.lower()

def sentence_proper(text_string):
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
    if author_last_name == "Granovet.ms":
        author_last_name = "Granovetter"
        author_first_initial = "M"
    return '%s %s' % (author_last_name, author_first_initial)

def r_year(reference):
    #Extra year from references. Returns nothing when year is not an interger, I think.
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
def r_cite(reference):
    #Create a relatively unique name based on author, year and title.
    try:
        author = r_author(reference)
        year = r_year(reference)
        title = r_title(reference)
        return '%s (%s) %s'.replace('.','') % (author,year,title)
    except:
        return ''


def r_doi(reference):
    #extracts DOI from reference. I don't think I do anything with it though.
    if 'DOI ' in reference[-1]:
        return reference[-1].strip('DOI ')
    else:
        return ''

def r_title(reference):
    #cleans up title in reference
    #reliex on the fact that the first year splits author from title
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
    references=references.replace('{','').replace('}','').split('. ')
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

def extract_article_info(b,bp):
        #grabs article info from a bibtex cite and returns some of the fields in a dictionary

        article_title    = sentence_proper(b.get("title",'No title').replace('{','').replace('}',''))
        article_journal  = b.get('series',b.get('journal','') )
        article_journal  = sentence_proper(article_journal.replace('{','').replace('}',''))
        article_year     = b.get('year','').replace('{','').replace('}','')
        article_volume   = b.get('volume','').replace('{','').replace('}','')
        article_number   = b.get('number','1').replace('{','').replace('}','')
        article_pages    = b.get('pages','').replace('{','').replace('}','')
        article_abstract = b.get('abstract','').replace('{','').replace('}','')
        article_doi      = b.get('doi','').replace('{','').replace('}','')
        if ' (C) ' in article_abstract:
            article_abstract = article_abstract.split(' (C) ')[0]

        try:
            references = [r_cite(r) for r in split_references(b["cited-references"])]
        except:
            references = []

        try:
            authors_raw = bp["author"]
            article_author = '%s, %s' % ( authors_raw[0].last_names()[0], authors_raw[0].first_names()[0] )
            if len(authors_raw)>2:
                for a in authors_raw[1:-1]:
                    article_author = '%s, %s %s' % (article_author,a.first_names()[0],a.last_names()[0])
            if len(authors_raw)>1:
                article_author = '%s & %s %s' % (article_author,authors_raw[-1].first_names()[0],authors_raw[-1].last_names()[0])
        except:
            article_author = "None"

        article_cite = '%s. %s. "%s." %s. %s:%s %s.' % (article_author,
                                       article_year,
                                       article_title,
                                       article_journal,
                                       article_volume,
                                       article_number,
                                       article_pages)
        return {'cite' : article_cite,
                'year': article_year,
                'doi' : article_doi,
                'title' : article_title,
                'journal' : article_journal,
                'volume' : article_volume,
                'pages' : article_pages,
                'references' : references,
                'number' : article_number,
                'abstract' : article_abstract }
