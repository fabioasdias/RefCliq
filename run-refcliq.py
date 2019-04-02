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

from __future__ import absolute_import
import itertools
import glob
import networkx as nx
from community import best_partition

from optparse import OptionParser
from refcliq.citations import CitationNetwork
from refcliq.preprocess import import_bibs
from refcliq.util import thous
from refcliq.geocoding import ArticleGeoCoder

from os.path import exists

    
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

    citation_network=CitationNetwork()
    citation_network.build(import_bibs(args))
    
    print(thous(len(citation_network._G))+' different references with '+thous(len(citation_network._G.edges()))+' edges')

    co_citation_network=citation_network.cocitation()
    print(options.edge_minimum,len(co_citation_network),len(co_citation_network.edges()))    

    # #removing pairs that do not meet the count threshold
    # to_remove=[]
    # for e in co_citation_network.edges():
    #     if co_citation_network[e[0]][e[1]]['count'] < options.edge_minimum :
    #         to_remove.append(e)
    # co_citation_network.remove_edges_from(to_remove)
    # co_citation_network.remove_nodes_from([n for n in co_citation_network if len(list(co_citation_network.neighbors(n)))==0])

    gc=ArticleGeoCoder()
    co_citation_network=gc.update_network(co_citation_network)

    partition = best_partition(co_citation_network, weight='count') 

    # clique_report(co_citation_network, citation_network, partition, no_of_cites=25)
