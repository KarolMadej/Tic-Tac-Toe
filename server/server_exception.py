class BadHeaderException(Exception):
   """Raised when client send wrong header"""
   pass

class BadDataFormatException(Exception):
   """Raised when the data format is wrong"""
   pass