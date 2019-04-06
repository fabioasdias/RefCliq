import pytest
from src.refcliq.preprocess import import_bibs
from os.path import dirname, realpath, join

class TestBib(object):
    def test_load(self):
        articles=import_bibs([join(dirname(realpath(__file__)),'basic.bib'),])
        assert(len(articles)==3)
        reference_years=[['2012', '2013'], ['2011', '2013'], ['2011', '2012']]
        reference_names=[['Second', 'Third'], ['First','Third'], ['First', 'Second']]
        #without the right number of references here, the whole thing crumbles
        for i,a in enumerate(articles):
            assert('references' in a)
            assert(len(a['references'])==2)
            for j,ref in enumerate(a['references']):
                assert(ref['authors'][0].last_names[0]==reference_names[i][j])
                assert(ref['year']==reference_years[i][j])
    
