import networkx as nx
from fuzzywuzzy.fuzz import ratio
from tqdm import tqdm

def _compare_field(a1:dict, a2:dict, field:str,field2:str=None)->int:
    """
    Returns fuzzywuzzy's ratio for the same field in two dicts (or different
    fields optionally)
    """
    if (field2 is None):
        if (field in a1) and (field in a2) and (a1[field] is not None) and (a2[field] is not None):
            return(ratio(a1[field],a2[field]))
    else:
        if (field in a1) and (field2 in a2) and (a1[field] is not None) and (a2[field2] is not None):
            return(ratio(a1[field],a2[field2]))
    
    #if either of the fields is none or doesn't exist, 
    #try the optimistic way
    return(100)

            

def same_article(a1:dict, a2:dict)->bool:
    """
    Tests if two articles are the same based on their info. 

    Uses fuzzy string matching and the Person structure from pybtex.
    """
    if _compare_field(a1,a2,'year')<100:
        return(False)

    #article from references only have one author
    L1=len(a1['authors'])
    L2=len(a2['authors'])
    if (L1>1) and (L2>1) and (L1!=L2):
        return(False)
    #We have same year, same title / journal
    for i in range(min([L1,L2])):
        if ratio(str(a1['authors'][i]),str(a2['authors'][i]))<=80:
            return(False)

    if _compare_field(a1,a2,'doi')<=90:
        return(False)
    if _compare_field(a1,a2,'title')<=80:
        return(False)
    if _compare_field(a1,a2,'journal')<=80:
        return(False)
    if _compare_field(a1,a2,'vol')<=80:
        return(False)
    if _compare_field(a1,a2,'page')<=80:
        return(False)    

    return(True)

def _find_article_no_doi(G:nx.DiGraph, a:dict):
    """
    Finds the article without using the DOI information 
    """
    #we might change the graph!
    to_iterate=list(G.nodes())
    for n in to_iterate: 
        if same_article(G.node[n]['data'],a):
            return(n)
    return(None)


def _findArticle(G:nx.DiGraph, a: dict):
    """
    finds the node corresponding to article a.
    Adds it to the graph if it doesn't exist (in place)
    """
    #find by DOI
    if ('doi' in a) and (a['doi'] is not None):
        doi=a['doi']
        if (doi not in G):
            #article might be there, just not with a DOI
            n=_find_article_no_doi(G,a)
            
            G.add_node(doi)
            G.node[doi]['data']=a

            #the work is there, but not represented by its doi
            #We know the doi now, so let's replace it
            if (n is not None):
                for nn in G.predecessors(n):
                    G.add_edge(nn,doi)
                for nn in G.successors(n):
                    G.add_edge(doi,nn)
                G.remove_node(n)

        return(doi)
    #if we don't have the doi, the work might be there or not, gotta find it.
    #The hard way.
    else:
        n=_find_article_no_doi(G,a)
        if (n is not None):
            return(n)
        n=len(G)
        G.add_node(n)
        G.node[n]['data']=a
        return(n)


def build_citation_network(articles):
    G=nx.DiGraph()
    print('citation network')
    for article in tqdm(articles):
        citing=_findArticle(G,article)
        for cited_article in article['references']:
            cited=_findArticle(G,cited_article)
            G.add_edge(citing,cited)
    return(G)

