import geocoder
from os.path import exists
from src.refcliq.util import cleanCurlyAround
import re
import networkx as nx
from fuzzywuzzy.process import extractOne
from time import sleep, monotonic
from tqdm import tqdm
import json
import googlemaps

CACHE='cache.json'

_addressPattern=re.compile(r"(([\w\- ]+,[\w\.\- ']*)(;?))*,(?P<rest>[^;]*?),(?P<country>[^\,]*?)\.", re.IGNORECASE)
_initialsPattern=re.compile(r"(?: (?:[A-Z' ]\.?)+,)")    

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
    def __init__(self,google_key:str=''):
        self._cache = {}
        if (google_key!=''):
            self._gmaps = googlemaps.Client(key = google_key)
        else:
            self._gmaps = None

        self._cacheFV = {}
        self._country_cache = {}#otherwise "xxxx USA" returns "USA"'s entry from the cache...
        self._parts_by_country = {}
        self._last_request = monotonic() #keeps track of the last time we used nominatim
        self._outgoing_calls = 0
        self._fails=set() #Used to avoid repeatedly asking the same thing (leics, england). 
                        #this state is not saved (it might get updated).
        if exists(CACHE):
            with open(CACHE,'r') as fin:
                data=json.load(fin)
                self._cache=data['cache']
                # if ('fv' not in data): #calculate the FV
                for c in self._cache:
                    self._cacheFV[c]={}
                    for ad in self._cache[c]:
                        self._cacheFV[c][ad]=_computeFV(ad)
                # else:
                #     self._cacheFV=data['fv']

                self._parts_by_country=data['parts']
                self._country_cache=data['country']
    
    def _save_state(self):
        #'fv':self._cacheFV
        to_save={'cache':self._cache,'country':self._country_cache,'parts':self._parts_by_country}
        with open('cache.json','w') as fout:
            json.dump(to_save, fout, indent=4, sort_keys=True)
    # @profile
    def _cache_search(self, full_address:str, country:str, ratio:float=90)->list:
        """
            Performs a cache search for the address. 
            full_address = address without country
            country = the country.
            If address=='', ratio is ignored.
        """
        if (full_address==''):
            return(country, self._country_cache.get(country))

        if len(self._cache) > 0:
            address = full_address.lower()
            #hash checking is faster, so let's try accurate before fuzzy
            if (country in self._cache):
                maybe_country = country
                how_well = 100
            else:
                maybe_country, how_well = extractOne(country, self._cache.keys())

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

    def _add(self, address:str, country:str, coords:list):
        """
            Adds (address, coords) to the appropriate cache.
        """
        if address=='':
            self._country_cache[country]=coords[:]
        else:
            if country not in self._cache:
                self._cache[country]={}
                self._cacheFV[country]={}
            low_address=address.lower()
            self._cache[country][low_address]=coords[:]
            self._cacheFV[country][low_address]=_computeFV(low_address)

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
                G.node[n]['data']['countries']=[x['country'] for x in G.node[n]['data']['geo'] ]
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
            # print('osm req', address, self._outgoing_calls)
            self._outgoing_calls += 1
            self._last_request = monotonic()
        else:
            return(None)

        if res and res.ok:
            return([res.osm['x'], res.osm['y']])
        
        self._fails.add(address)
        return(None)
    
    def _google(self, address:str)->list:
        """
            Queries google's geocoding service for the address.
            Limited to 50 queries per second. Keys are necessary.
            Returns (x,y) or None if not found
        """
        delta = monotonic() - self._last_request
        res = None
        if delta <= (1/50):
            sleep((1/50)-delta)
        if (address not in self._fails):
            res = self._gmaps.geocode(address)
            print('google ', address)
            self._outgoing_calls += 1
            self._last_request = monotonic()

        if (res is not None) and len(res)>0:
            return([res[0]['geometry']['location']['lng'],res[0]['geometry']['location']['lat']])
    
        self._fails.add(address) 
        return(None)
    
    def _lookup(self, full_address:list)->list:
        """
            Checks one address against the cache, get from Google maps or
            OSM/Nominatim and adds to the cache if necessary.
            Input ex: ["UofT, Toronto", "Canada"]

            Returns:
            - Accurate coordinates, if possible: 'accurate'
            - Country representative coordinates: 'generic'
            - Name of the country: 'country'.
        """
        # print('---- Doing', full_address)
        
        country = full_address[1].lower()
        if full_address[0].startswith(','):
            full_address[0] = full_address[0][1:].strip()

        #NJ 08240 USA - Why bother with the standard comma before the country...
        if ('usa' in country) and (len(country)>3):
            full_address[0]=full_address[0]+', '+', '.join(country.split()[:-1])
            country='usa'
             
        #some US address don't bother saying "USA" at the end,
        #So it would get the ZIP as country
        if (len(country)==5) and (all([x.isdigit() for x in country])):
            country='usa'
            #puts the zip back
            full_address[0]=full_address[0]+' '+full_address[1]

        #removes all words with digits on them - without removing commas - "11215," 
        if self._gmaps is None:
            all_vals=[' '.join([word for word in x.split() if not any([c.isdigit() for c in word])]) for x in full_address[0].split(',')]
        else: #google plays better with numbers
            all_vals=full_address[0].split(',')


        #keeps track of how many address parts works for this country to avoid unnecessary calls - Minimum 2.
        if country not in self._parts_by_country:
            self._parts_by_country[country]=max([2,len(all_vals)])

        if self._gmaps is None:
            i=min([len(all_vals),self._parts_by_country[country]])
        else:
            i=len(all_vals)

        tried_addresses = []
        accurate = None        
        while i>0:
            vals = all_vals[-i:]
            address=(', '.join(vals)).strip()
            _, accurate=self._cache_search(address, country) 
            if accurate is not None:
                break
            else:
                tried_addresses.append(address)
                # print(address)
                if self._gmaps is not None:
                    accurate=self._google(address+', '+country)
                else:
                    accurate=self._nominatim(address+', '+country)

            if (accurate is not None):
                self._parts_by_country[country]=min([i,self._parts_by_country[country]])                
                for add in tried_addresses:
                    self._add(add, country, accurate)
                self._save_state()                    
                break
            else:
                #not found, let's try with fewer parts
                i-=1

        _, generic = self._cache_search('',country)
        if (generic is None):
            if self._gmaps is not None:
                generic=self._google(country)
            else:
                generic=self._nominatim(country)
            
            if generic is not None:
                self._add('', country, generic)
                self._save_state()

        return(accurate, generic, country)

    def _get_coordinates(self, affiliation:str):
        aff = affiliation.replace('&','').replace("(Reprint Author)","").replace(' Jr.','').replace(' Sr.','')
        aff = _initialsPattern.sub(', ',aff)
        aff = aff.replace(",,",",")
        print(aff)
        matches = _addressPattern.finditer(aff)
        addresses = [[entry.group('rest').strip(), entry.group('country').strip()] for entry in matches]
        print('-')
        if not addresses:
            return([])

        res=[]
        for address in addresses:
            print(address)
            accurate,country,name=self._lookup(address)
            if (name is not None):
                res.append({'accurate':accurate, 'generic':country, 'country':name})
        return(res)
