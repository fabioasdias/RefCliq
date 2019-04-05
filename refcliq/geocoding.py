import geocoder
from os.path import exists
from refcliq.util import cleanCurlyAround
import re
import networkx as nx
from fuzzywuzzy.process import extractOne
from time import sleep, monotonic
from tqdm import tqdm

GEOCACHE='geocache.tsv'
COUNTRYCACHE='countries.tsv'
PARTSCACHE='parts.tsv'

_addressPattern=re.compile(r"(?P<last>[\w]+),(?P<first>(([\w]+)| |([A-Z](\.)?))*)(\(.*?\))?,(?P<rest>[^.]+)", re.IGNORECASE)


class ArticleGeoCoder:
    def __init__(self):
        self._cache={}
        self._country_cache={}#otherwise "xxxx USA" returns "USA"'s entry from the cache...
        self._parts_by_country={}
        self._last_request=monotonic()
        self._nominatim_calls=0
        self._deltas=[]
        if exists(GEOCACHE):
            self._cache=self._read_cache(GEOCACHE)
        if exists(PARTSCACHE):
            self._read_parts()
        if exists(COUNTRYCACHE):
            self._country_cache=self._read_cache(COUNTRYCACHE)
    

    def _read_parts(self):
        with open(PARTSCACHE,'r') as fin:
            for line in fin:
                vals=line.split('\t')
                self._parts_by_country[vals[0]]=int(vals[1])


    def _read_cache(self,cachename:str)-> dict:
        """
            Reads a file with 3 keys per line:
            str \t float1 \t float2 \n
            and returns it as a dictionary
        """
        ret={}
        with open(cachename,'r') as fin:
            for line in fin:
                vals=line.split('\t')
                ret[vals[0]]=[float(vals[1]),float(vals[2])]
        return(ret)

    def _write_parts(self):
        with open(PARTSCACHE,'w') as fout:
            for k in self._parts_by_country:
                fout.write('{0}\t{1}\n'.format(k,self._parts_by_country[k]))

    def _write_cache(self, cachename:str, cache:dict):
        with open(cachename,'w') as fout:
            for k in cache:
                fout.write('{0}\t{1}\t{2}\n'.format(k, cache[k][0], cache[k][1]))

    def _save_state(self):
        self._write_cache(GEOCACHE, self._cache)
        self._write_cache(COUNTRYCACHE, self._country_cache)
        self._write_parts()
    
    def _cache_search(self, address:str, country:bool=False, ratio:float=90)->list:
        """
            Performs a cache search for the address. 
            if country=True, ratio is ignored, only string matches count.
        """
        if len(self._cache)>0:
            if country:
                return(address, self._country_cache.get(address))

            maybe, how_well = extractOne(address, self._cache.keys())
            if how_well >= ratio:
                return(maybe,self._cache[maybe])
        return(None,None)

    def _add(self, address:str, coords:list, country:bool=False):
        """
            Adds (address, coords) to the appropriate cache.
        """
        if country:
            self._country_cache[address]=coords[:]
        else:
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

    def _nominatim(self, address:str)->list:
        """
            Queries nominatim's public server for the address.
            Forcibly limited to 1 query per second.
            Returns (x,y) or None if not found.
        """
        #we can only do one query per second on public nominatim
        delta=monotonic()-self._last_request
        self._deltas.append(delta)
        if delta<=1:
            sleep(1-delta)
        res=geocoder.osm(address)#, url='http://192.168.2.47/nominatim/')
        # print('osm req', address, self._nominatim_calls)
        self._nominatim_calls+=1
        self._last_request=monotonic()
        if res and res.ok:
            return([res.osm['x'],res.osm['y']])
        else:
            return(None)

    
    def _lookup(self, full_address:str)->(list,list,str):
        """
            Checks one address against the cache, get from OSM/Nominatim and adds to the cache if necessary.
            Returns:
            - Accurate coordinates, if possible (city/address)
            - Country representative coordinates otherwise,
            - Name of the country.
        """
        # print('---- Doing', full_address)
        #OSM doesn't understand PRC, USA addresses are usually ", CA 95000 USA"
        address_to_use=full_address.replace('Peoples R','').replace(' USA',', USA')
        
        #removes all words with digits on them - without removing commas - "11215," 
        all_vals=[' '.join([word for word in x.split() if not any([c.isdigit() for c in word])]) for x in address_to_use.split(',')]
        country=all_vals[-1]

        #keeps track of how many address parts works for this country to avoid unnecessary calls - Minimum 2.
        if country not in self._parts_by_country:
            self._parts_by_country[country]=max([2,len(all_vals)])

        i=min([len(all_vals),self._parts_by_country[country]])
        tried_addresses=[]
        accurate=None        
        cacheChanged=False
        while True:
            vals=all_vals[-i:]
            address=(', '.join(vals)).strip()
            _,coords=self._cache_search(address,country=(i==1)) 
            if coords is None:
                tried_addresses.append(address)
                coords=self._nominatim(address)
                cacheChanged = cacheChanged or (coords is not None)

            if (coords is None) and (i>1):
                #not found, let's try with fewer parts
                i-=1
            else:
                if i==1:              
                    self._add(address,coords,country=True)                           
                    if (cacheChanged):
                        self._save_state()
                    return(accurate,coords,country)
                else:
                    for add in tried_addresses:
                        # print('added', add)
                        self._add(add,coords)
                    accurate=coords[:]
                    self._parts_by_country[country]=min([i,self._parts_by_country[country]])
                    i=1


    def _get_coordinates(self, affiliation:str):
        aff=cleanCurlyAround(affiliation).replace(r'\&','')
        # print('+++ Affiliation',aff)
        matches=_addressPattern.finditer(aff)
        addresses=[entry.group('rest') for entry in matches]
        if not addresses:
            return(None)

        accurate_coords=[]
        country_coords=[]
        country_names=[]
        for address in addresses:
            accurate,country,name=self._lookup(address)
            if accurate:
                accurate_coords.append(accurate)
            if country:
                country_coords.append(country)
            country_names.append(name)
                

        return(accurate_coords,country_coords,country_names)
