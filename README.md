# RefCliq


This package is a **full rewrite** of [Neal Caren's
RefCliq](https://github.com/nealcaren/RefCliq). The objective is the same, to
analyse clustering of co-cited publications using graph clustering. Note that
this package also operates over the **co-citation network, not the citation
network**.

The main differences are:

* More robust article matching, based on all available information (so two articles from the same author/year in the same journal don't get clumped together if they also have the DOI or title)
* Robust string matching, to catch spelling errors ([using fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy))
* Degree centrality instead of betweeness centrality.
* The clustering algorithm is the same ([louvain](https://github.com/taynaud/python-louvain)), but the co-citation count is not ignored 
* Geocoding support, where the affiliation field is used to map the location of the citing authors. **This requires a Google maps API key, which may require payment**. [More information about Google geocoding API](https://developers.google.com/maps/documentation/geocoding/start). The guide on how to get a key [is available here](https://developers.google.com/maps/documentation/geocoding/get-api-key).

**Important**: The input bibliography files *must be from Web of Science / Web of Knowledge*, including the *Cited references* field. Otherwise the references section might be missing or with a different format and this will not work.

**Really Important**: Most .bib files include information that was manually inputed by different people using different ideas/notations/conventions. This package will work for most cases, but not all. Some manual editing of the .bib file might be required.

If you run into an error that should be fixed in the code, please [open a new issue here](https://github.com/fabioasdias/RefCliq/issues/new). Be sure to [check the existing issues first](https://github.com/fabioasdias/RefCliq/issues), be as descriptive as possible and include examples of the error and detailed instructions on how to replicate it.

## Installation:


*Only python 3 is supported.*

```
pip install refcliq
```
All the dependencies will be automatically installed.


## Usage:


This package contains two scripts: 
* refcliq.py: Computes the clustering and saves the result in a json file.
* refcliqvis.py: Starts the visualization interface for a pre-computed file.

### Generating the results
Running refcliq.py with a '-h' argument will display the help:

```
$ refcliq.py -h
usage: refcliq.py [-h] [-o OUTPUT_FILE] [--cites CITES] [-k GOOGLE_KEY]
                  [--graphs]
                  files [files ...]

positional arguments:
  files           List of .bib files to process

optional arguments:
  -h, --help      show this help message and exit
  -o OUTPUT_FILE  Output file to save, defaults to 'clusters.json'.
  --cites CITES   Minimum number of citations for an article to be included,
                  defaults to 2.
  -k GOOGLE_KEY   Google maps API key. Necessary for precise geocoding.
  --graphs        Saves graph drawing information for the cluster.
```

* *files*: The .bib files to be used. It can be one file (`a.bib`), a list of files (`a.bib b.bib`), or wildcards (`*.bib`).
* *-o* (output_file): The name to be used for the results file. The 'json' extension is automatically added. If not provided, defaults to `clusters.json`.
* *--cites*: Minimum number of citations for an article be included. While this can be changed in the interactive interface, increasing this number speeds up the processing time and reduces the memory requirements. *Increase this parameter if the processing crashes / runs out of memory*. Further, with an argument of `1`, all the works cited by only one article will present as a densely connected cluster, which may hinder a bit the interpretation, so it defaults to `2`.
* *--graphs*: Enables the visualization of citation graphs in the interface. **Greatly increases the size of the results file*. Only clusters with less than 50 articles will be displayed in the interface.
* *-k*: The Google API key. This key is **necessary** for geocoding and **may require payment**. Please check [Google's billing calculator](https://mapsplatformtransition.withgoogle.com/calculator). While this package tries to be smart and reduce the geocoding calls, it is reasonably safe to assume one call for each author of each publication as an approximation of an upper bound on the number of calls. **Monitor your usage carefully**, this package is provided as is and the authors cannot be help responsible for any billing issues with Google.

Without the geocoding key the countries are still identified and present in the exported .tsv files, but the map will not be displayed in the interface.

### Visualizing the results
Assuming that the results file is named `clusters.json`:

```
$ refcliqvis.py clusters.json
```

A new tab will be open on the default browser that will look like this (with geocoding enabled):

![Basic interface with the map on the top right and the cluster listing on the left](doc/base.png "")

The interface is divided in two panels, the cluster visualisation on the left and the citation details on the right.

**Clusters**: Each box on the left represents one cluster found by the louvain method. In its "collapsed" visualisation, it displays the number of articles in this cluster, the *Content keywords* directly computed from the available abstracts of the articles in this cluster, and the *Keyworkds of citing papers*, representing they keywords computed from the papers that cite the papers in this cluster. The keywords are computed using [sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfTransformer.html), with only tf enabled.

The two sliders on the top left control what is displayed, hiding works with fewer citations than the value of the first slider and clusters with fewer works than the value of the second. This is done without reprocessing the clustering.

Clicking on the chevron on the top right part of the cluster box will "expand" that cluster, looking like this (after clicking also on the first citation):

![one cluster on the left side is expanded, showing a node-link plot](doc/graph.png "")

The expanded version lists all articles in that cluster, with clickable links
that activate the panel on the right of the interface that displays the citing
details for that citation, along with the network centrality measure
([degree_centrality](https://en.wikipedia.org/wiki/Centrality#Degree_centrality)
implemented using
[networkx](https://networkx.github.io/documentation/networkx-1.9/reference/generated/networkx.algorithms.centrality.degree_centrality.html)),
citation count, article keywords (when the abstract is available), and the
keywords of the citing works.

**Centrality**: This image is also showing the network plot, with the first work in the list highlighted. This plot is not included by default (and only available for clusters with fewer than 50 works), but it is helpful to understand the centrality measure. Since we adopted degree centrality, this number is the ratio between the number of existing connections of this work and the number of possible connections, it represents the fraction of the cluster that is cited when this work is cited. A centrality of `1` means that every time any article in this cluster is cited, that work is also cited. In this case, the work "Durandlasserve, A. 2002. Holding Their Ground." has only three citations, but has a centrality measure of `0.81` meaning that it is connected (was cited concomitantly) to `81%` of the works in this cluster. The connections are highlight in red in the network plot.

**Citation details**: This panel is divided in two parts: the map on the top (if geocoding is enabled by providing a Google geocoding key) and the list of citing works. This list can be exported as a tab separated values file by clicking on the *Export tsv file* button. The DOI link for each work is also provided, if that information is available.

The geocoded information can be displayed as markers or as a heatmap. To reduce the impact of papers with several authors on the heatmap, the log of the number of authors is used. The information on the map can be filtered to include only a single year or all years up to the selected year (using the *cummulative* checkbox). Unchecking the *Fit to markers* box will keep the map from changing the viewport (useful to do comparisons).


## FAQ

* Why not use nominatim for geocoding? 

    We actually used it at the start of the project, but it missed several addresses (like `Leics, England`) and it geocoded `Toronto, Ontario, Canada` as a point in the middle of the forest about 50km north of Victoria, BC.

* Why tab separated values (.tsv) instead of comma separated values (.csv) for the exported citations?

    While the specification of the csv format is rather robust, there are some atrocious implementations of it in the wild. By using a character that is *not* present in the values, the parsing is easier and less error-prone.

* Why degree centrality instead of betweeness_centrality as the original RefCliq?

    Consider the following graph:

    ![Node link plot of a graph with 9 nodes, two cliques of four in each side connected by a node in the center](doc/centrality.png "")

    Betweeness centrality measures how many shortest paths of the graph pass through a given node. In this case, all paths connecting nodes from the left side of the red node to nodes on the right side will pass through the red node, so the betweeness centrality of the red node will be rather high (`~0.57`), which is not exactly what we want to measure. The degree centrality for this node is `2/8`, because it is connected to two of the possible eight nodes in the network.

    Further, degree centrality is *much* faster to compute.

* The time estimates for the *citation network - Cited-References* part of the processing are wrong/consistently increasing.

    That is the trickiest part of the code, where given a very incomplete reference (parts of the name of the first author, year, and something related to the title/journal, maybe a DOI), the code has to decide if that work is already on the citation graph or not. Since the graph keeps growing, this search will get progressively slower. Robust string comparison is slow, but it is a somewhat reliable way of properly matching the works, even when DOIs are present, because the same work can be associated with multiple DOIs, or someone might have written the name of the company in the DOI field. *Manually filled fields*. And typos.

* How do I save a map displayed on the interface to use in my blog/paper/etc ?

    Print screen. Yes, a rather archaic way, but it works and it doesn't require any complicated implementation on my part. It helps if you "zoom in" / increase the resolution on the browser (Ctrl and + on Chrome) to make the map bigger. Pull requests on that feature are welcome.