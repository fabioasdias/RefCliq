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
from argparse import ArgumentParser

from src.refcliq.citations import CitationNetwork
from src.refcliq.util import thous

import json
from tqdm import tqdm
import networkx as nx
from networkx.readwrite import json_graph
from os.path import exists
import pickle

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-o", type=str, 
                    help="Output file to save, defaults to 'clusters.json'.",
                    dest="output_file",default='clusters.json')
    parser.add_argument("-k", type=str,
                    help="Google maps API key. Necessary for precise geocoding.",
                    dest="google_key",default='')
    parser.add_argument("--checkpoint",  action="store_true",
                    help="Saves checkpoint files of the processing -> read the documentation!",
                    dest="checkpoint",default=False)
    parser.add_argument("--graphs",  action="store_true",
                    help="Saves graph drawing information for the cluster.",
                    dest="graphs",default=False)
    parser.add_argument("files", nargs='+',
                    help="List of .bib files to process")

    options = parser.parse_args()


    #options.google_key=""

    checkpoint_cn=options.output_file+'_cn.hdf5'
    if options.checkpoint and exists(checkpoint_cn):
        citation_network=CitationNetwork()
        citation_network.load(checkpoint_cn)
    else:
        citation_network=CitationNetwork(options.files, checkpoint_prefix=options.output_file, google_key=options.google_key, checkpoint=options.checkpoint)    
        if options.checkpoint:
            print('done citation - saving')
            citation_network.save(checkpoint_cn)

    print('keywords')
    citation_network.compute_keywords()

    print(thous(len(citation_network))+' different references with '+thous(len(citation_network.edges()))+' citations.')



    checkpoint_cocn=options.output_file+'_cocn.p'
    if options.checkpoint and  exists(checkpoint_cocn):
        co_citation_network=nx.read_gpickle(checkpoint_cocn)
    else:
        co_citation_network=citation_network.cocitation(count_label="count", copy_data=False)
        print('pickle')
        if options.checkpoint:
            nx.write_gpickle(co_citation_network, checkpoint_cocn)

    # exit()

    for n in citation_network:
        citation_network.node[n]['data']['original_cc']=-1

    for i,gg in enumerate(nx.connected_components(co_citation_network)):
        for n in gg:
            citation_network.node[n]['data']['original_cc']=i



    checkpoint_part = options.output_file+'_part.p'
    if options.checkpoint and exists(checkpoint_part):
        with open(checkpoint_part,'rb') as f:
            partition = pickle.load(f)
    else:
        print('Partitioning')
        partition = best_partition(co_citation_network, weight='count', random_state=7) #deterministic
        if options.checkpoint:
            with open(checkpoint_part,'wb') as f:
                pickle.dump(partition,f)


    print('Saving results')
    output={'geocoded':options.google_key!=''}

    parts={}
    for n in partition:
        if partition[n] not in parts:
            parts[partition[n]]=[]
        parts[partition[n]].append(n)

    graphs={}

    print('Per cluster analysis/data (centrality)')
    for p in tqdm(parts):
        subgraph = co_citation_network.subgraph(parts[p])
        centrality = nx.degree_centrality(subgraph)
        if options.graphs:
            topo = nx.Graph()
            topo.add_nodes_from(subgraph)
            topo.add_weighted_edges_from(subgraph.edges(data='count'))
            graphs[p] = json_graph.node_link_data(topo)
        
        for n in centrality:
            citation_network.node[n]['data']['centrality'] = centrality[n]

    output['partitions'] = parts
    output['graphs'] = graphs

    articles={}
    done={}
    for n in citation_network.nodes():
        assert(n not in done)
        done[n]=True
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
