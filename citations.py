import networkx as nx
from fuzzywuzzy.fuzz import ratio
from tqdm import tqdm
from itertools import combinations

# import matplotlib.pylab as plt

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
    if ('year' in a1) and ('year' in a2) and (a1['year'] is not None) and (a2['year'] is not None):
        if (a1['year']!=a2['year']):
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
    for n in G: 
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

            #the work is there, but it was not represented by its doi.
            #  We know the doi now, so let's replace it
            if (n is not None):
                #new data might be a citation only
                if (len(G.node[doi]['data']['authors'])==1) and (len(G.node[n]['data']['authors'])>1):
                    print('happened')
                    G.node[doi]['data']['authors']=G.node[n]['data']['authors']
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


def build_citation_network(articles:list)->nx.DiGraph:
    """
    Builds a directed graph to represent the citation network in the list of
    articles.
    """
    G=nx.DiGraph()
    print('citation network')
    for article in tqdm(articles):
        citing=_findArticle(G,article)
        for cited_article in article['references']:
            cited=_findArticle(G,cited_article)
            G.add_edge(citing,cited)
    return(G)

def citation2cocitation(C:nx.DiGraph, threshold:int)->nx.Graph:
    """
    Builds a co-citation network from the citation network C.
    Only pairs with more than 'threshold' citations are considered.
    """
    G=nx.Graph()
    G.add_nodes_from(C)
    print('Building co-citation')
    for citing in tqdm(C):
        cited=C.successors(citing)
        for w1,w2 in combinations(cited,2):
            G.add_edge(w1,w2)
            G[w1][w2]['count']=G[w1][w2].setdefault('count',0)+1

    #removing pairs that do not meet the count threshold
    to_remove=[]
    for e in G.edges():
        if G[e[0]][e[1]]['count'] < threshold :
            to_remove.append(e)
    G.remove_edges_from(to_remove)

    #removing isolated nodes
    G.remove_nodes_from([n for n in G if len(list(G.neighbors(n)))==0])

    # for n in G:
    #     l=''
    #     if C.node[n]['data']['authors']:
    #         l=l+','.join([str(x) for x in C.node[n]['data']['authors']])
    #     if C.node[n]['data']['year'] is not None:
    #         l=l+'. '+C.node[n]['data']['year']
    #     if ('title' in C.node[n]['data']) and (C.node[n]['data']['title'] is not None):
    #         l=l+'. '+C.node[n]['data']['title']
    #     if C.node[n]['data']['journal'] is not None:
    #         l=l+'. '+C.node[n]['data']['journal']
    #     G.node[n]['label']=l

    # pos=nx.spring_layout(G)
    # nx.draw_networkx_nodes(G,pos=pos,node_size=5)
    # nx.draw_networkx_edges(G,pos=pos,width=[G[e[0]][e[1]]['count'] for e in G.edges()])
    # nx.draw_networkx_labels(G,pos=pos,labels={n:G.node[n]['label'] for n in G.nodes()},font_size=8)
    # plt.show()

    return(G)
