import geocoder
from os.path import exists
from src.refcliq.util import cleanCurlyAround
import re
import networkx as nx
from fuzzywuzzy.process import extractOne
from time import sleep, monotonic
from tqdm import tqdm
import json

CACHE='cache.json'

_addressPattern=re.compile(r"(?P<last>[\w]+),(?P<first>(([\w]+)| |([A-Z](\.)?))*)(\(.*?\))?,(?P<rest>[^.]+)", re.IGNORECASE)

def _computeFV(s:str)->list:
    """
        Computes a normalized histogram of the (common) letters in s.
    """
    trans = {}
    for i,c in enumerate('abcdefghiklmnopqrstuvwxyz'):
        trans[c]=i

    ret=[0,]*len(trans)
    for c in s.lower():
        if (c in trans):
            ret[trans[c]]+=1
    return([x/sum(ret) for x in ret])

def _distanceFV(v1:list, v2:list)->float:
    """
        Computes the distance between two feature vectors
    """
    ret=0
    for i in range(len(v1)):
        ret+=abs(v1[i]-v2[i])
    return(ret/2.0)

class ArticleGeoCoder:
    def __init__(self):
        self._cache={}
        self._cacheFV={}
        self._country_cache={}#otherwise "xxxx USA" returns "USA"'s entry from the cache...
        self._parts_by_country={}
        self._last_request=monotonic() #keeps track of the last time we used nominatim
        self._nominatim_calls=0
        self._fails={} #Used to avoid repeatedly asking the same thing (leics, england). 
                        #this state is not saved (it might get updated).
        if exists(CACHE):
            with open(CACHE,'r') as fin:
                data=json.load(fin)
                self._cache=data['cache']
                if ('fv' not in data): #calculate the FV
                    for c in self._cache:
                        self._cacheFV[c]={}
                        for ad in self._cache[c]:
                            self._cacheFV[c][ad]=_computeFV(ad)
                else:
                    self._cacheFV=data['fv']

                self._parts_by_country=data['parts']
                self._country_cache=data['country']
    
    def _save_state(self):
        to_save={'cache':self._cache,'country':self._country_cache,'parts':self._parts_by_country, 'fv':self._cacheFV}
        with open('cache.json','w') as fout:
            json.dump(to_save, fout)
    # @profile
    def _cache_search(self, full_address:str, country:bool=False, ratio:float=90)->list:
        """
            Performs a cache search for the address. 
            if country=True, ratio is ignored, only string matches count.
        """
        if len(self._cache)>0:
            address=full_address.lower()
            if country:
                return(address, self._country_cache.get(address))

            #hash checking is faster, so let's try accurate before fuzzy
            c=address.split(',')[-1]
            if (c in self._cache):
                maybe_country=c
                how_well=100
            else:
                maybe_country, how_well = extractOne(c, self._cache.keys())

            if (how_well>=ratio):
                if (address in self._cache[maybe_country]):
                    return(address, self._cache[maybe_country][address])

                fv = _computeFV(address)
                to_look= [ad for ad in self._cacheFV[maybe_country] if _distanceFV(fv,self._cacheFV[maybe_country][ad])<0.25]

                if to_look:
                    maybe, how_well = extractOne(address, to_look)
                    if how_well >= ratio:
                        return(maybe, self._cache[maybe_country][maybe])
        return(None,None)

    def _add(self, address:str, coords:list, country:bool=False):
        """
            Adds (address, coords) to the appropriate cache.
        """
        low_address=address.lower()
        if country:
            self._country_cache[low_address]=coords[:]
        else:
            c=low_address.split(',')[-1]
            if c not in self._cache:
                self._cache[c]={}
                self._cacheFV[c]={}
            self._cache[c][low_address]=coords[:]
            self._cacheFV[c][low_address]=_computeFV(low_address)

    def add_authors_location_inplace(self, G:nx.Graph):
        """
            For every node of G (a reference in the network), finds the
            coordinates based from the 'Affiliation' bibtex field, if present.
            _Alters the data of G_.
        """
        print('Getting coordinates for each author affiliation')
        for n in tqdm(G):
            if ('data' in G.node[n]) and ('Affiliation' in G.node[n]['data']) and (G.node[n]['data']['Affiliation'] is not None) and (len(G.node[n]['data']['Affiliation'])>0):
                G.node[n]['data']['geo'] = self._get_coordinates(G.node[n]['data']['Affiliation'])
        return(G)

    def _nominatim(self, address:str)->list:
        """
            Queries nominatim's public server for the address.
            Forcibly limited to 1 query per second.
            Returns (x,y) or None if not found.
        """
        #we can only do one query per second on public nominatim
        delta = monotonic() - self._last_request
        if delta <= 1:
            sleep(1-delta)
        #if we tried that in this run and it failed, don't try again
        if (address not in self._fails):
            res=geocoder.osm(address)#, url='http://192.168.2.47/nominatim/')
            # print('osm req', address, self._nominatim_calls)
            self._nominatim_calls += 1
            self._last_request = monotonic()
        else:
            return(None)

        if res and res.ok:
            return([res.osm['x'], res.osm['y']])
        else:
            self._fails[address]=True #dict is faster than list
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
        #some US address don't bother saying "USA" at the end:
        last = full_address.split(' ')[-1]
        if (len(last)==5) and (all([x.isdigit() for x in last])):
            full_address=full_address+', USA'

        #OSM doesn't understand PRC; USA addresses are usually ", CA 95000 USA" ; Rep of Georgia doesn't work either
        address_to_use=full_address.replace('Peoples R','').replace(' USA',', USA').replace('Rep of','')
        
        #removes all words with digits on them - without removing commas - "11215," 
        all_vals=[' '.join([word for word in x.split() if not any([c.isdigit() for c in word])]) for x in address_to_use.split(',')]
        country=all_vals[-1]

        #keeps track of how many address parts works for this country to avoid unnecessary calls - Minimum 2.
        if country.lower() not in self._parts_by_country:
            self._parts_by_country[country.lower()]=max([2,len(all_vals)])

        i=min([len(all_vals),self._parts_by_country[country.lower()]])
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
                    if coords:        
                        self._add(address,coords,country=True)                           
                    if (cacheChanged):
                        self._save_state()
                    return(accurate,coords,country)
                else:
                    for add in tried_addresses:
                        # print('added', add)
                        self._add(add,coords)
                    accurate=coords[:]
                    self._parts_by_country[country.lower()]=min([i,self._parts_by_country[country.lower()]])
                    i=1


    def _get_coordinates(self, affiliation:str):
        aff=affiliation.replace('&','')
        # print('+++ Affiliation',aff)
        matches=_addressPattern.finditer(aff)
        addresses=[entry.group('rest') for entry in matches]
        if not addresses:
            return([])

        res=[]
        for address in addresses:
            accurate,country,name=self._lookup(address)
            res.append({'accurate':accurate, 'generic':country, 'country':name})
        return(res)
