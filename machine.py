"""Defines a machine on the local net."""

from services import *

class Machine(object):


  DEFAULT_ENDPOINT_LIST = [HttpService()]


  def __init__(self, name, ip, endpoint_list=DEFAULT_ENDPOINT_LIST):
    self._name = name
    self._ip = ip
    self._endpoint_list = endpoint_list
      

  def get_endpoints(self):
    return self._endpoint_list

  def get_name(self):
    return self._name

  def get_ip(self):
    return self._ip

