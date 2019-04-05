import pytest
from src.refcliq.preprocess import import_bibs
from os.path import dirname, realpath, join

class TestBib(object):
    def test_load(self):
        articles=import_bibs([join(dirname(realpath(__file__)),'basic.bib'),])
        assert(len(articles)==3)
        #without the right number of references here, the whole thing crumbles
        for a in articles:
            assert('references' in a)
            assert(len(a['references'])==2)
    
