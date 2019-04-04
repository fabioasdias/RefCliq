import geocoder
from os.path import exists
from refcliq.util import cleanCurlyAround
import re
import networkx as nx
from fuzzywuzzy.process import extractOne
from time import sleep
from tqdm import tqdm

GEOCACHE='geocache.tsv'

_addressPattern=re.compile(r"(?P<last>[\w]+),(?P<first>(([\w]+)| |([A-Z](\.)?))*)(\(.*?\))?,(?P<rest>[^.]+)", re.IGNORECASE)


class ArticleGeoCoder:
    def __init__(self):
        self._cache={}
        if exists(GEOCACHE):
            self._read_cache()
    
    def _read_cache(self):
        with open(GEOCACHE,'r') as fin:
            for line in fin:
                vals=line.split('\t')
                self._cache[vals[0]]=[float(vals[1]),float(vals[2])]

    def _write_cache(self):
        with open(GEOCACHE,'w') as fout:
            for k in self._cache:
                fout.write('{0}\t{1}\t{2}\n'.format(k, self._cache[k][0], self._cache[k][1]))
    
    def _find(self, address:str)->list:
        if len(self._cache)>0:
            maybe, how_well = extractOne(address, self._cache.keys())
            if how_well > 90:
                return(self._cache[maybe])
        return(None)

    def _add(self, address:str, coords:list):
        self._cache[address]=coords[:]

    def update_network(self, G:nx.Graph):
        """
            For every node of G (a reference in the network), finds the
            coordinates based from the 'Affiliation' bibtex field, if present.
        """
        print('Getting coordinates')
        for n in tqdm(G):
            if ('data' in G.node[n]) and ('Affiliation' in G.node[n]['data']) and (G.node[n]['data']['Affiliation'] is not None):
                affiliation=cleanCurlyAround(G.node[n]['data']['Affiliation'])
                matches=_addressPattern.finditer(affiliation)
                addresses=[entry.group('rest') for entry in matches]
                if addresses:
                    G.node[n]['data']['coords']=self._get_coordinates(addresses)
        return(G)
    
    def _get_coordinates(self, addresses:list):
        coords=[]
        for full_address in addresses:
            all_vals=full_address.split(',')
            i=3
            while True:
                if i==0:
                    print('Not found!', full_address)
                    break
                if len(all_vals)>i:
                    vals=all_vals[-i:]
                address=(', '.join(vals)).strip()
                cached=self._find(address)
                if cached and all([x!=-1 for x in cached]):
                    coords.append(cached)
                    break
                else:
                    res=geocoder.osm(address)#, url='http://192.168.2.47/nominatim/')
                    sleep(1)
                    if (res is not None) and (res.ok): 
                        coords.append([res.osm['x'],res.osm['y']])
                        self._add(address,coords[-1])
                        self._write_cache()
                        break
                    else:
                        i-=1
                

        return(coords)
