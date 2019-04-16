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
    parser.add_option("-o", "--output_file",
                    action="store", type="string", 
                    help="Output file to save, defaults to 'clusters.json'.",
                    dest="output_file",default='clusters.json')
    parser.add_option("-g", "--geocode",
                    action="store_true",
                    help="Geocode the citing papers using Nominatim public servers, limited to 1 request/second.",
                    dest="geocode", default=False)
    (options, args) = parser.parse_args()

    if len(args)==0:
        print('\nNo input files!\n')
        parser.print_help()
        exit(-1)

    if options.geocode==False:
        print("\n\nNOT computing geographic coordinates for citing papers!\nPass -g/--geocode to enable geocoding.\n")
    
    citation_network=CitationNetwork(import_bibs(args), geocode=options.geocode)    
    print(thous(len(citation_network))+' different references with '+thous(len(citation_network.edges()))+' citations.')
    citation_network.compute_keywords()
    co_citation_network=citation_network.cocitation()
    for n in citation_network:
        citation_network.node[n]['data']['original_cc']=-1

    for i,gg in enumerate(nx.connected_components(co_citation_network)):
        for n in gg:
            citation_network.node[n]['data']['original_cc']=i

    print('Partitioning')
    partition = best_partition(co_citation_network, weight='count', random_state=7) #deterministic
    print('Saving results')
    output={'geocoded':options.geocode}

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
        articles[n]['cited_count']=len(articles[n]['cites_this'])
        articles[n]['references']=[p for p in citation_network.successors(n)]
        articles[n]['reference_count']=len(articles[n]['references'])
        articles[n]['authors']=[{'last':x.last_names, 'first':x.first_names} for x in articles[n]['authors']]    
    output['articles']=articles

    outName=options.output_file
    if not outName.endswith('.json'):
        outName=outName+'.json'

    with open(outName,'w') as fout:
        json.dump(output, fout)#, indent=4, sort_keys=True)
