import pytest
from src.refcliq.citations import CitationNetwork
from src.refcliq.preprocess import import_bibs
from os.path import dirname, realpath, join

class TestCN(object):
    def test_build(self):
        articles=import_bibs([join(dirname(realpath(__file__)),'basic.bib'),])
        cn=CitationNetwork()
        cn.build(articles)
        assert(len(cn._G)==3)
        assert(len(cn._G.edges())==6)
    def test_add(self):
        pass
