from decimal import Decimal

def thous(x:float)-> str:
    return('{0:n}'.format(Decimal(x)))

def cleanCurlyAround(s:str)->str:
    """Removes curly braces"""
    if s and (s[0]=='{') and (s[-1]=='}'):
        return(s[1:-1])
    return(s)

