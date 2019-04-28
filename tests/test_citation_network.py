import pytest
from refcliq.citations import CitationNetwork
from refcliq.preprocess import import_bibs
from os.path import dirname, realpath, join

class TestCN(object):
    def test_build(self):
        cn=CitationNetwork()
        cn.build([join(dirname(realpath(__file__)),'basic.bib'),])
        assert(len(cn)==3)
        assert(len(cn.edges())==6)

    def test_add(self):
        pass
