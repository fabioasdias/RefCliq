from decimal import Decimal

def thous(x:float)-> str:
    return('{0:n}'.format(Decimal(x)))
