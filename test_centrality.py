import networkx as nx

G = nx.Graph()

G.add_edge('a','b')
G.add_edge('a','c') 
G.add_edge('b','d') 
G.add_edge('d','c') 

G.add_edge('c','e') 
G.add_edge('e','f') 

G.add_edge('f','g') 
G.add_edge('g','h') 
G.add_edge('h','i') 
G.add_edge('f','i') 


print(nx.betweenness_centrality(G)['e'])
print(nx.degree_centrality(G)['e'])





