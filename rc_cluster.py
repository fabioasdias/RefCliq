#!/usr/bin/env python
# encoding: utf-8
"""
RefCliq is a (full) rewrite of Neal Caren's original script.

git: https://github.com/fabioasdias/RefCliq

The idea is the same, but with improved article matching, a more stable
clustering method (the same python-louvain community, but considering the number
of co-citations on the edges), geo-coding support for the authors, and a web
interface for the visualization of the results.


Original: https://github.com/nealcaren/RefCliq 
Created by Neal Caren on June 26, 2013. 
neal.caren@gmail.com
"""

from community import best_partition
from argparse import ArgumentParser

from refcliq.citations import CitationNetwork
from refcliq.util import thous

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
                        dest="output_file", default='clusters.json')
    parser.add_argument("--cites", type=int,
                        help="Minimum number of citations for an article to be included, defaults to 2.",
                        dest="cites", default=2)
    parser.add_argument("-k", type=str,
                        help="Google maps API key. Necessary for precise geocoding.",
                        dest="google_key", default='')
    parser.add_argument("--graphs",  action="store_true",
                        help="Saves graph drawing information for the cluster.",
                        dest="graphs", default=False)
    parser.add_argument("files", nargs='+',
                        help="List of .bib files to process")

    options = parser.parse_args()

    citation_network = CitationNetwork()
    citation_network.build(
        options.files, google_key=options.google_key, min_citations=options.cites)

    citation_network.compute_keywords()

    print(thous(len(citation_network))+' different references with ' +
          thous(len(citation_network.edges()))+' citations.')

    co_citation_network = citation_network.cocitation(
        count_label="count", copy_data=False, min_cocitations=options.cites)

    for n in citation_network:
        citation_network.node[n]['data']['original_cc'] = -1

    for i, gg in enumerate(nx.connected_components(co_citation_network)):
        for n in gg:
            citation_network.node[n]['data']['original_cc'] = i

    print('\nPartitioning (no progress bar for this - sorry!)\n')
    partition = best_partition(
        co_citation_network, weight='count', random_state=7)  # deterministic

    output = {'geocoded': options.google_key != ''}

    parts = {}
    for n in partition:
        if partition[n] not in parts:
            parts[partition[n]] = []
        parts[partition[n]].append(n)

    graphs = {}

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

    print('Saving')
    articles = {}
    for n in tqdm(citation_network.nodes()):
        # if the work isn't cited or doesn't cite anything useful (aka is never going to show up in the interface)
        if (n not in co_citation_network) and (all([p not in co_citation_network for p in citation_network.successors(n)])):
            continue
        articles[n] = citation_network.node[n]['data']
        articles[n]['cites_this'] = [
            p for p in citation_network.predecessors(n)]
        articles[n]['cited_count'] = len(articles[n]['cites_this'])
        articles[n]['references'] = [p for p in citation_network.successors(n)]
        articles[n]['reference_count'] = len(articles[n]['references'])
        articles[n]['authors'] = [
            {'last': x.last_names, 'first': x.first_names} for x in articles[n]['authors']]

    output['articles'] = articles

    outName = options.output_file
    if not outName.endswith('.json'):
        outName = outName+'.json'

    with open(outName, 'w') as fout:
        json.dump(output, fout)  # , indent=4, sort_keys=True)

    print('Run "rc_vis.py {0}" to view the results.'.format(outName))
