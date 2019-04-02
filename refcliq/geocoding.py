import geocoder
from os.path import exists


GEOCACHE='./geocache'

class ArticleGeoCoder:
    def __init__(self):
        pass
        # if not exists(GEOCACHE):
        #     makedirs(GEOCACHE)

    def update_network(self, G):
        """
            For every node of G (a reference in the network), finds the
            coordinates based from the 'Affiliation' bibtex field, if present.
        """
        for n in G:
            if ('Affiliation' in G.node[n]['data']) and (G.node[n]['data']['Affiliation'] is not None):
                affiliation=G.node[n]['data']['Affiliation']
                print(affiliation)

        return(G)


#  res=geocoder.osm(ad+', Regina, SK, Canada',url='http://192.168.2.47/nominatim/')
#                 if (res is None) or (res.osm is None): #not found
#                     geo[ad]={'x':-1,'y':-1}
#                 else:
#                     geo[ad]=res.osm

                
#             # print(a,geo[ad])
#             coords.append([geo[ad]['x'],geo[ad]['y']])
#         else:
#             coords.append([-1,-1])
