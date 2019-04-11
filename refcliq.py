#!/usr/bin/env python
# encoding: utf-8
"""
RefCliq is a rewrite of Neal Caren's original script.

git: https://github.com/fabioasdias/RefCliq

The idea is the same, but with improved article matching, a more stable
clustering method (the same python-louvain community, but considering the number
of co-citations on the edges), geo-coding support for the authors, and a web
interface for the visualization of the results.


Original: https://github.com/nealcaren/RefCliq Created by Neal Caren on June 26,
2013. neal.caren@gmail.com
"""

from community import best_partition
from optparse import OptionParser

from src.refcliq.citations import CitationNetwork
from src.refcliq.preprocess import import_bibs
from src.refcliq.util import thous

import json
from tqdm import tqdm
import networkx as nx
from networkx.readwrite import json_graph

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--directory_name",
                    action="store", type="string", 
                    help="Output directory, defaults to 'clusters'",
                    dest="directory_name",default='clusters')
    (options, args) = parser.parse_args()

    if len(args)==0:
        print('\nNo input files!\n')
        parser.print_help()
        exit(-1)

    
    citation_network=CitationNetwork(import_bibs(args),geocode=True)    
    print(thous(len(citation_network))+' different references with '+thous(len(citation_network.edges()))+' citations.')
    citation_network.compute_keywords()
    co_citation_network=citation_network.cocitation()

    print('Partitioning')
    partition = best_partition(co_citation_network, weight='count', random_state=7) #stability
    print('Saving results')
    output={}

    parts={}
    for n in partition:
        if partition[n] not in parts:
            parts[partition[n]]=[]
        parts[partition[n]].append(n)

    # graphs={}

    print('Per cluster analysis/data (centrality, keywords)')
    for p in tqdm(parts):
        subgraph = co_citation_network.subgraph(parts[p])
        centrality = nx.degree_centrality(subgraph)

        # topo = nx.Graph()
        # topo.add_nodes_from(subgraph)
        # topo.add_weighted_edges_from(subgraph.edges(data='count'))
        # graphs[p] = json_graph.node_link_data(topo)
        
        for n in centrality:
            citation_network.node[n]['data']['centrality'] = centrality[n]

    output['partitions'] = parts
    # output['graphs'] = graphs

    articles={}
    for n in citation_network:
        articles[n] = citation_network.node[n]['data']
        articles[n]['cites_this']=[p for p in citation_network.predecessors(n)]
        articles[n]['references']=[p for p in citation_network.successors(n)]
        articles[n]['authors']=[{'last':x.last_names, 'first':x.first_names} for x in articles[n]['authors']]    
    output['articles']=articles

    with open('out.json','w') as fout:
        json.dump(output, fout, indent=4, sort_keys=True)
