import re
from refcliq.util import cleanCurlyAround

_firstLinePattern=re.compile(r"@(?P<kind>.*?){([\s]*(?P<id>[^,\s]+),)")
_fieldPattern=re.compile(r"(?P<name>[\w-]+?)[\s]*=[\s]*({(?P<content>.*)})",    flags=re.IGNORECASE|re.DOTALL) 
def parse(bibfile:str, keepOnly:list=None)->dict:
    """
    bibfile: path to a .bib file.
    
    Returns: a dictionary where the keys are the entry IDs and the content are
    the entries, using the same fields.

    If keepOnly is not None, only returns those fields.
    """
    ret={}
    with open(bibfile,'r') as fin:
        currentEntry=None
        for line in fin:
            match=_firstLinePattern.search(line)    
            if (match):
                currentEntry=match.group("id")
                ret[currentEntry]={}
                currentField=''
                openBraces=0
                continue
            #blank spaces/lines, preambles, etc
            if (currentEntry is None): 
                continue
            openBraces+=(line.count('{')-line.count('}'))
            currentField=currentField+line
            if openBraces > 0:
                continue
            else:
                match=_fieldPattern.search(currentField)
                if (match):
                    name=match.group("name")
                    if (name is not None) and ((keepOnly is None) or (name in keepOnly)):
                        content=cleanCurlyAround(match.group("content")).strip()
                        ret[currentEntry][match.group("name")]=content
                currentField=''
            
    return(ret)

