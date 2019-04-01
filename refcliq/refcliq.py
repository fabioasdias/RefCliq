#!/usr/bin/env python
# encoding: utf-8
"""
refcliq..py

Created by Neal Caren on June 26, 2013.
neal.caren@gmail.com

Dependencies:
pybtex
networkx
community

Note: community is available from:
http://perso.crans.org/aynaud/communities/

##note: seems to be screwing up where the person has lots of intials.###
"""


import itertools
import glob
import networkx as nx
import community
from citations import CitationNetwork
from optparse import OptionParser
from preprocess import import_bibs
from reporting import d3_export, gexf_export, clique_report
from util import thous

from os.path import exists

def ref_cite_count(articles):
    """take a list of article and return a dictionary of 
    works cited and their count Later add journal counts"""
    cited_works = {}
    for article in articles:
        references = set(article.get('references',[]) )
        for reference in references:
            if (reference in cited_works):
                cited_works[reference]['count'] += 1
            else:
                cited_works[reference] = {'count':1 , 'abstract': article['abstract']}
    return(cited_works)

def top_cites(cited_works, threshold = 2):
    """returns sorted list of the top cites. Would probably 
    be better if handled ties in a more sophisticated way."""
    most_cited = [r for r in cited_works if cited_works[r]['count'] >= threshold ]
    print('Minimum node weight: %s' % threshold)
    print('Nodes: %s' % thous(len(most_cited)))
    return most_cited


    
def make_journal_list(cited_works):
    """    Is it a journal or a book?
    A journal is somethign with more than three 
    years of publication Returns a
    dictionary that just lists the journals""" 
    cited_journals = {}
    for item in cited_works:
        title = item.split(') ')[-1]
        year = item.split(' (')[1].split(')')[0]
        try:
            if year not in cited_journals[title]:
                cited_journals[title].append(year)
        except:
            cited_journals[title] = [year]
    cited_journals = {j:True for j in cited_journals if len(set(cited_journals[j])) > 3 or 'J ' in j}
    return cited_journals




def create_edge_list(articles, most_cited):
    #What things get cited together?
    pairs = {}
    for article in articles:
        references = article.get('references',[])
        references = list(set([r for r in references if r in most_cited]))
        refs = itertools.combinations(references,2)
        for pair in refs:
            pair = sorted(pair)
            pair = (pair[0],pair[1])
            pairs[pair] = pairs.get(pair,0) + 1
    return pairs

def top_edges(pairs, threshold = 2):
    """note that it doesn't just return n top edges, but actually returns all the edges that have
    an edge weight equal to or greater than the nth edge"""
    #most_paired = sorted(pairs, key=pairs.get, reverse=True)[:n]
    #threshold =  pairs[most_paired[-1]]
    
    #if threshold < 2:
    #    threshold = 2

    most_paired = [p for p in pairs if pairs[p] >= threshold]
    most_paired = [ (p[0],p[1],{'weight':pairs[p]} ) for p in most_paired]
    print('Minimum edge weight: %s' % threshold)
    print('Edges: %s' % thous(len(most_paired)))
    return most_paired
	
def make_partition(G,min=5):
    #clustering but removes small clusters.
    partition = community.best_partition(G)
    cliques = {}
    for node in partition:
        clique = partition[node]
        cliques[clique] = cliques.get(clique,0) + 1

    revised_partition = {}
    for node in partition:
        clique = partition[node]
        if cliques[clique]>=min:
            revised_partition[node] = str(partition[node])
        else:
            revised_partition[node] = '-1'
    return revised_partition




if __name__ == '__main__':

    parser = OptionParser()
    # parser.add_option("-n", "--node_minimum",
    #                 action="store", type="int", 
    #                 help="Minimum number times a work needs to be cited to be used",
    #                 dest="node_minimum", default=0)
    parser.add_option("-e", "--edge_minimum",
                    action="store", type="int", 
                    help="Minimum number of co-citations to consider the pair of works",
                    dest="edge_minimum", default=2)
    parser.add_option("-d", "--directory_name",
                    action="store", type="string", 
                    help="Output directory, defaults to 'clusters'",
                    dest="directory_name",default='clusters')
    (options, args) = parser.parse_args()

    #Import files
    if len(args)==0:
        print('\nNo input files!\n')
        parser.print_help()
        exit(-1)

    # cn_cache='gn_cache.gp'
    # cn_cache='urban1.gp'

    # if exists(cn_cache):
    #     citation_network=nx.read_gpickle(cn_cache)
    # else:
    citation_network=CitationNetwork()
    citation_network.build(import_bibs(args))
    # nx.write_gpickle(citation_network,cn_cache)
    
    print(thous(len(citation_network._G))+' different references with '+thous(len(citation_network._G.edges()))+' edges')

    # co_citation_network=citation2cocitation(citation_network, threshold=options.edge_minimum)
    # print(len(co_citation_network))

    exit()

    cited_works = ref_cite_count(articles)
    if options.node_minimum == 0:
        node_minimum = int(2 + len(articles)/1000)
    else:
        node_minimum = options.node_minimum
        
    most_cited = top_cites(cited_works, threshold = node_minimum)
    pairs = create_edge_list(articles, most_cited)
    most_paired = top_edges(pairs, threshold = options.edge_minimum)

    G=nx.Graph()
    G.add_edges_from(most_paired)
    for node in most_cited:
        G.add_node(node,freq= cited_works[node]['count'])

    cliques = make_partition(G, min=10)

    for node in most_cited:
        G.add_node(node,freq= cited_works[node]['count'], group = cliques[node], abstract = cited_works[node]['abstract'])

    d3_export(most_cited, most_paired, cliques, cited_works, output_directory=options.directory_name)
    gexf_export(most_cited, most_paired, cliques, cited_works,output_directory=options.directory_name)
    clique_report(G, articles, cliques, no_of_cites=25)
