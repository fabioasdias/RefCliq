import geocoder
from os.path import exists
from refcliq.util import cleanCurlyAround
import re
import networkx as nx
from fuzzywuzzy.process import extractOne
from time import sleep, monotonic
from tqdm import tqdm

GEOCACHE='geocache.tsv'
PARTSCACHE='parts.tsv'

_addressPattern=re.compile(r"(?P<last>[\w]+),(?P<first>(([\w]+)| |([A-Z](\.)?))*)(\(.*?\))?,(?P<rest>[^.]+)", re.IGNORECASE)


class ArticleGeoCoder:
    def __init__(self):
        self._cache={}
        self._parts_by_country={}
        self._last_request=monotonic()
        self._nominatim_calls=0
        self._deltas=[]
        if exists(GEOCACHE):
            self._read_cache()
        if exists(PARTSCACHE):
            self._read_parts()
    

    def _read_parts(self):
        with open(PARTSCACHE,'r') as fin:
            for line in fin:
                vals=line.split('\t')
                self._parts_by_country[vals[0]]=int(vals[1])

    def _read_cache(self):
        with open(GEOCACHE,'r') as fin:
            for line in fin:
                vals=line.split('\t')
                self._cache[vals[0]]=[float(vals[1]),float(vals[2])]

    def _write_parts(self):
        with open(PARTSCACHE,'w') as fout:
            for k in self._parts_by_country:
                fout.write('{0}\t{1}\n'.format(k,self._parts_by_country[k]))

    def _write_cache(self):
        with open(GEOCACHE,'w') as fout:
            for k in self._cache:
                fout.write('{0}\t{1}\t{2}\n'.format(k, self._cache[k][0], self._cache[k][1]))

    def _save_state(self):
        self._write_cache()
        self._write_parts()
    
    def _find(self, address:str)->list:
        if len(self._cache)>0:
            maybe, how_well = extractOne(address, self._cache.keys())
            if how_well >= 80:
                return(maybe,self._cache[maybe])
        return(None,None)

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
                coords=self._get_coordinates(G.node[n]['data']['Affiliation'])
                G.node[n]['data']['coords']=coords
        return(G)
    
    def _lookup(self, full_address:str):
        print('---- Doing', full_address)
        all_vals=[' '.join([word for word in x.split() if not any([c.isdigit() for c in word])]) for x in full_address.replace('Peoples R','').replace(' USA',', USA').split(',')]
        vals=all_vals[:]
        if vals[-1] not in self._parts_by_country:
            self._parts_by_country[vals[-1]]=3
        i=self._parts_by_country[vals[-1]]
        tried_addresses=[]
        while True:
            if i==0:
                print('Not found!', full_address)
                break
            if len(all_vals)>i:
                vals=all_vals[-i:]
            address=(', '.join(vals)).strip()
            _,coords=self._find(address)
            if coords and all([x!=-1 for x in coords]):
                print('cached')
                for add in tried_addresses:
                    print('added+', add, address)
                    self._add(add,coords)
                self._parts_by_country[vals[-1]]=min([i,self._parts_by_country[vals[-1]]])
                self._save_state()
                return(coords)
            else:
                tried_addresses.append(address)
                #we can only do one query per second on public nominatim
                delta=monotonic()-self._last_request
                self._deltas.append(delta)
                if delta<=1:
                    sleep(1-delta)
                res=geocoder.osm(address)#, url='http://192.168.2.47/nominatim/')
                print('osm req', address, self._nominatim_calls)
                self._nominatim_calls+=1
                self._last_request=monotonic()

                if (res is not None) and (res.ok): 
                    coords=[res.osm['x'],res.osm['y']]
                    for add in tried_addresses:
                        print('added', add)
                        self._add(add,coords)
                    self._parts_by_country[vals[-1]]=min([i,self._parts_by_country[vals[-1]]])
                    self._save_state()
                    return(coords)
                else:
                    i-=1


    def _get_coordinates(self, affiliation:str):
        aff=cleanCurlyAround(affiliation).replace(r'\&','')
        print('+++ Affiliation',aff)
        matches=_addressPattern.finditer(aff)
        addresses=[entry.group('rest') for entry in matches]
        if not addresses:
            return(None)

        coords=[]
        for address in addresses:
            current_coord=self._lookup(address)
            if current_coord:
                coords.append(current_coord)
                

        return(coords)
