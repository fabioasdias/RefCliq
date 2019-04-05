#!/usr/bin/env python
# encoding: utf-8
"""
RefCliq is a rewrite of Neal Caren's original script.

git: https://github.com/fabioasdias/RefCliq

The idea is the same, but with improved article matching, a more stable
clustering method (the same python-louvain community, but considering the number
of co-cites), geo-coding support for the authors, and a web interface for the
visualization of the results.


Original: 
https://github.com/nealcaren/RefCliq 
Created by Neal Caren on June 26, 2013. 
neal.caren@gmail.com
"""

from community import best_partition
from optparse import OptionParser

from src.refcliq.citations import CitationNetwork
from src.refcliq.preprocess import import_bibs
from src.refcliq.util import thous
from src.refcliq.geocoding import ArticleGeoCoder

from tqdm import tqdm
    
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

    if len(args)==0:
        print('\nNo input files!\n')
        parser.print_help()
        exit(-1)


    gc=ArticleGeoCoder()
    print('Reading .bibs')
    articles=import_bibs(args)
    print('caching')
    for a in tqdm(articles):
        if ('Affiliation' in a) and (a['Affiliation']):
            try:
                gc._get_coordinates(a['Affiliation'])
            except:
                print(a)
                print(a.keys())
                print(a['Affiliation'])
                raise
    print('Nominatim calls', gc._nominatim_calls)
    exit()
    citation_network=CitationNetwork()    
    citation_network.build(articles)
    print(thous(len(citation_network._G))+' different references with '+thous(len(citation_network._G.edges()))+' edges')
    co_citation_network=citation_network.cocitation()
    co_citation_network=gc.update_network(co_citation_network)
    partition = best_partition(co_citation_network, weight='count') 