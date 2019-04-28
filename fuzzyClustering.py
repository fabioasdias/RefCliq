
import networkx as nx
import matplotlib.pylab as plt
import numpy as np
import community
import skfuzzy as fuzz
from sklearn.manifold import MDS

def fuzzyClustering(G,weight='weight'):

    to_remove=[]
    for n in G.nodes():
        if len(list(G.neighbors(n)))==0:
            to_remove.append(n)
    G.remove_nodes_from(to_remove)

    partition = community.best_partition(G)
    C=len(set(partition.values()))

    nodes=list(G.nodes())
    i2n={i:n for i,n in enumerate(nodes)}
    A=nx.adjacency_matrix(G,nodelist=nodes,weight=weight)
    A=(A/np.sum(A,axis=0))
    A=(A+A.T)/2
    X=MDS(n_components=3).fit_transform(A).T
    res=fuzz.cmeans(X,C,2,0.1,200)
    D=res[1]
    pick=np.argmax(D,axis=0)
    
    # partition={i:[] for i in range(len(pick))}
    # for i in range(len(pick)):
    #     partition[pick[i]].append(i2n[i])
    # partition[-1]=to_remove[:]

    partition={}
    for n in to_remove:
        partition[n]=-1
    for i in range(len(pick)):
        partition[i2n[i]]=pick[i]

    return(partition)
    