from __future__ import absolute_import
from os.path import exists, join
from os import makedirs
import json
from xml.etree import ElementTree as et
from xml.etree.ElementTree import Element, SubElement, tostring
from collections import Counter
import networkx as nx
from string import punctuation
from refcliq.util import thous
from refcliq.textprocessing import stopwords, get_stopwords, keywords, cite_keywords

def make_filename(string):
    punctuation = '''!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~'''

    for item in punctuation:
        string = string.replace(item,'')
    string = string.replace(' ','_')
    string = string.lower()
    return string


def get_clique_words(articles,cliques,stopword_list=[]):
    """
    This extracts the most common words in a clique based on articles that cite
    references in the clique. Note that this is the most frequent, not the
    distinquishing words (i.e. not uniquely occuring in the clique.)
    """
    stopwords= get_stopwords()
    stopword_list = stopword_list + stopwords
    
    clique_abstracts = {}
    for article in articles:
        ac = article_clique(article, cliques)
        if len(article['abstract'])>2:
            words = article['abstract']
        else:
            words = article['title']
        try:
            clique_abstracts[ac].append(words)
        except Exception:
            clique_abstracts[ac] = [words]
            
    clique_words = {clique: keywords(clique_abstracts[clique],stopword_list) for clique in clique_abstracts}
    return clique_words



def article_clique(article, cliques, min=2):
    #Look up the clique of each of the reference
    #Note that most reference won't be found.
    clique_list = {}
    for ref in article['references']:
        if cliques.get(ref,'-1') != '-1':
            clique_list[cliques[ref]] = clique_list.get(cliques[ref],0) + 1

    #Assign the clique to the most
    try:
        top_clique = sorted(clique_list, key=clique_list.get, reverse=True)[0]
    except:
        top_clique = '-1'

    #Set minimum threshold for number of cites to define clique membership
    if clique_list.get(top_clique,0) < min :
        top_clique = '-1'
    return top_clique


def journal_cliques(articles, cliques):
    #finds the journals that commonly cite a reference clique.
    journals = [article['journal'] for article in articles]
    journal_counts = Counter(journals)
    clique_journals = {}
    for article in articles:
        journal = article['journal']
        ac = article_clique(article, cliques)
        if ac in clique_journals:
            clique_journals[ac][journal] = clique_journals[ac].get(journal,0) + (1 / float(journal_counts[journal]) )
        else:
            clique_journals[ac]={article['journal'] : (1 / float(journal_counts[journal]) )}
    clique_best_journal = { c: sorted(clique_journals[c], key=clique_journals[c].get, reverse=True)[:4] for c in clique_journals }
    return clique_best_journal


def journal_report(articles):
    #Could I have a string with all the journals and how many items from each?
    journals = Counter([article['journal'] for article in articles if article['journal'] is not None])

    try:
        journals = ['%s (%s)' % (j.replace('\\&','&'), journals[j]) for j in sorted(journals,key=journals.get, reverse=True) if journals[j] >= 10 ]
    except:
        journals = []
    return ', '.join(journals)


def _check_create_dir(d):
    if not exists(d):
        makedirs(d)


#suite for making an html table
def html_table_row(row):
    row = [str(item) for item in row]
    return '<tr> <td>' + '</td> <td>'.join(row) + '</td> <tr>'

def html_table(list_of_rows):
    table_preface = r'<table>'
    table_body = '\n'.join( [html_table_row(row) for row in list_of_rows] )
    table_suffix = r'</table>'
    return table_preface + table_body + table_suffix


def make_reverse_directory(articles):
    #creates reverse directory for all articles that cite a specific article:
    reverse_directory = {}
    for article in articles:
        cite = article['cite']
        for reference in article['references']:
            try:
                reverse_directory[reference].append(article)
            except:
                 reverse_directory[reference] = [article]
    return reverse_directory


def write_reverse_directory(cite,cited_bys,output_directory,stopword_list, articles):
    html_preface = '''<html><head><meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
		<style type="text/css">
		body {
			background-color:#D9D9D9;
			text-rendering:optimizeLegibility;
			color:#222;
			margin-left:10%;
			font-family: Verdana, sans-serif;
                       font-size:12px;
			text-align:left;
                       width:600px;
			}
		h1 {
			font-weight:normal;
			font-size:18px;
			margin-left:0px;
			}
                h2 {
			font-weight: normal;
			font-size: 18px;
			margin-left: 0px;
			}
		p {
			font-weight:normal;
			font-size:12px;
			line-height:1.5;
			}
                 table {
    font-size:12px;
}
		</style> <body>'''
    html_suffix = '<p>Powered by <href="https://github.com/nealcaren/RefCliq" rarget="_blank">Refcliq</body></html>'
    filename = make_filename(cite)
    with open('%s/refs/%s.html' % (output_directory,filename), 'w') as output:
        output.write(html_preface)
        output.write('<h1>Contemporary articles citing %s</h1>' % cite)
        output.write('<h2>%s</h2>' % ', '.join(cite_keywords(cite, stopword_list, articles, n = 10)) )
        output.write('<dl>')
        for item in cited_bys:
            output.write('<dt>%s \n' % item['cite'])
            if len(item.get('doi','')) > 2:
                link = 'http://dx.doi.org/%s' % item.get('doi','')
                output.write('''<a href='%s' target="_blank">Link</a>''' % link)
            #output.write('\n\n')
            output.write('<dd>%s\n' % item.get('abstract',''))
            output.write('<p>\t</p>\n')
        output.write(html_suffix)

def cite_link(cite):
    link_name = 'refs/%s' % make_filename(cite)
    link = '''<a href='%s.html' target="_blank">%s</a>''' % (link_name,cite)
    return link
def clique_report(G, articles, cliques, no_of_cites=20, output_directory='./out/'):
    #This functions does too much.
    node_count = len(G.nodes())
    #gather node, clique and edge information
    nodes = list(G.nodes(data=True))
    node_dict = {node[0]:{'freq':node[1]['freq'], 'clique':node[1]['group'], 'abstract':node[1]['abstract']} for node in nodes}
    node_min = sorted([node_dict[node]['freq'] for node in node_dict])[0]
    #Build a dictionary of cliques listing articles with frequencies
    clique_references = {}
    for node in node_dict:
        clique = node_dict[node]['clique']
        freq = node_dict[node]['freq']
        try:
            clique_references[clique][node] = freq
        except:
            clique_references[clique] = {node : freq }
    clique_journals = journal_cliques(articles, cliques)

    #set up HTML
    html_preface = '''<html><head><meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1">
		<style type="text/css">
		body {
			background-color:#D9D9D9;
			text-rendering:optimizeLegibility;
			color:#222;
			margin-left:10%;
			font-family: Verdana, sans-serif;
                       font-size:12px;
			text-align:left;
                       width:800px;
			}
		h1 {
			font-weight:normal;
			font-size:18px;
			margin-left:0px;
			}
                h2 {
			font-weight: normal;
			font-size: 14px;
			margin-left: 0px;
			}
		p {
			font-size:12px;
			font-weight:normal;
			line-height:1.5;
			}
                 table {
    font-size:12px;
}
		</style> <body>'''
    html_suffix = r'''<p>Powered by <href='https://github.com/nealcaren/RefCliq' target="_blank">Refcliq</a></body></html>'''
    table_header = [['<b>Name</b>','','<b>Centrality</b>','<b>Count</b>','<b>Keywords</b>']]


    reference_location = join(output_directory,'refs')
    for dir_name in [output_directory,reference_location]:
        _check_create_dir(dir_name)

    years = sorted([article['year'] for article in articles])

    outfile_name = join('%s' % output_directory,'index.html')
    outfile = open(outfile_name,'w')
    outfile.write (html_preface)
    journals = journal_report(articles)
    outfile.write('<h1>Cluster analysis of %s articles ' % thous(len(articles)) )
    outfile.write('based on %s references cited at least %s times.' % (thous(len(G.nodes())) , node_min ) )
    outfile.write('<h1>Major Journals: %s\n ' % journals)
    outfile.write('<h1>Years: %s-%s\n ' % (years[0],years[-1]))
    outfile.write('<h1>Clusters:' )
    stopword_list = stopwords(articles)    
    clique_words = get_clique_words(articles,cliques ,stopword_list)
    reverse_directory = make_reverse_directory(articles)

    #Quick hack to figure out which are the biggest cliques and print(in reverse order)
    clique_size = {}
    for clique in clique_references:
        for ref in clique_references[clique]:
            clique_size[clique] = clique_size.get(clique,0) + clique_references[clique][ref]
    
    #Hack to put unsorted hack last:
    clique_size['-1'] = 0
    
    clique_counter = 0
    for clique in  sorted(clique_size, key=clique_size.get, reverse=True):
        clique_members= [node for node in node_dict if node_dict[node]['clique']==clique]
        c=G.subgraph(clique_members)
        bc = nx.betweenness_centrality(c, normalized=True, weight='freq')
        vocab = ', '.join(clique_words.get(clique,''))
        table_text = []
        try:
            journals = ', '.join(clique_journals[clique])
        except:
            journals = 'None'

        if int(clique) >= -2:
            if int(clique) == -1:
                vocab = "Cites that didn't cluster well."

            clique_counter = clique_counter +1

            outfile.write('<h2> %s   \n\n' % vocab)
            outfile.write('<br><b>Journals:</b> %s \n </h2>' % journals.replace(r'\&','&') )

            sorted_clique = sorted(clique_references[clique], key=clique_references[clique].get, reverse=True)
            if int(clique)> - 1:
                sorted_clique = sorted(bc, key=bc.get, reverse=True)

            output_cites = [cite for cite in sorted_clique[:no_of_cites] if node_dict[cite]['freq'] > 4]
            output_cites.sort()
            
            for cite in sorted(output_cites):
                write_reverse_directory(cite,reverse_directory[cite],output_directory,stopword_list,articles)

            table_text = table_header + [[str(cite_link(cite)+' '*40)[:130],'','%.2f' % bc[cite], node_dict[cite]['freq'],', '.join(cite_keywords(cite, stopword_list, articles, n = 5))] for cite in sorted_clique[:no_of_cites]]
            table_text= html_table(table_text)
            outfile.write(table_text)
            outfile.write('<p>')
    print('Report printed on %s nodes, %s edges and %s cliques to %s.' % (thous(len(G.nodes())), thous(len(G.edges())), clique_counter, output_directory))
    outfile.write (html_suffix)
    outfile.close()

def d3_export(most_cited, most_paired, cliques, cited_works, output_directory):
    #Exports network data in a JSON file format that d3js likes.
    #includes nodes with frequences and cliques; and edges with frequencies.
    _check_create_dir(output_directory)
    
    outfile_name = join('%s' % output_directory,'cites.json')

    node_key ={node:counter for counter,node in enumerate(sorted(most_cited))}
    nodes = [{'group': cliques[node]  ,
              'name' : node ,
              'nodeSize': int(cited_works[node]['count']) } for node in sorted(most_cited)]
    links  = [{'source': node_key[p[0]],
              'target' : node_key[p[1]],
              'value': int(p[2]['weight']) } for p in most_paired]
    d3_data = {'nodes': nodes, 'links' : links}
    with open(outfile_name,'w') as jsonout:
        json.dump(d3_data,jsonout)

def gexf_export(most_cited, most_paired, cliques, cited_works, output_directory):
	#Exports network data in .gexf format (readable by Gephi)
	#John Mulligan -- not the prettiest, but it gets the job done and translates all the information exported in the d3_export module.
    _check_create_dir(output_directory)

    outfile_name = join('%s' % output_directory,'cites.gexf')
    node_key ={node:counter for counter,node in enumerate(sorted(most_cited))}

    ##Create the tree
    et.register_namespace('',"http://www.gexf.net/1.2draft")
    et.register_namespace('viz','http://www.gexf.net/1.2draft/viz')
    tree = et.ElementTree()
    gexf = et.Element("gexf",{"xmlns":"http://www.gexf.net/1.2draft","version":"1.2"})
    tree._setroot(gexf)
    
    graph = SubElement(gexf,"graph",{'defaultedgetype':'undirected','mode':'static'})
    #more (graph) header information
    graph_attributes = SubElement(graph,"attributes",{'class':'node','mode':'static'})
    graph_mod_att = SubElement(graph_attributes,"attribute",{'id':'modularity_class','title':'Modularity Class','type':'integer'})
    graph_mod_att_content = SubElement(graph_mod_att,'default')
    graph_mod_att_content.text = "0"
    
    nodes = SubElement(graph,"nodes")
    edges = SubElement(graph,"edges")

    
    #write nodes
    for n in sorted(most_cited):
    	#create node in xml tree
    	node = SubElement(nodes, "node")
    	node.attrib["id"] = str(node_key[n])
    	node.attrib["label"] = n
    	#add attributes: clique, name
    	attributes_wrapper = SubElement(node, "attvalues")
    	clique_id = str(cliques[n])
    	clique = SubElement(attributes_wrapper,"attvalue",{"for":"modularity_class","value":clique_id})
    	clique.text = ' '
    	#add attribute: visualization size
    	size = str(cited_works[n]['count'])
    	viz = SubElement(node,"{http://www.gexf.net/1.2draft/viz}size",{"value":size})
    
    #write edges
    
    c = 1
    
    for p in most_paired:
    	id = str(c)
    	source = str(node_key[p[0]])
    	target = str(node_key[p[1]])
    	value = str(p[2]['weight'])
    	edge = SubElement(edges,"edge",{'id':id,'source':source,'target':target,'value':value})
    
    	c+=1   
    
    
    tree.write(outfile_name, xml_declaration = True, encoding = 'utf-8', method = 'xml')
