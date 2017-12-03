"""Defines a machine on the local net."""

from services import *

class Machine(object):


  DEFAULT_ENDPOINT_LIST = [HttpService()]


  def __init__(self, name, ip, endpoint_list=DEFAULT_ENDPOINT_LIST, check_up=True):
    self._name = name
    self._ip = ip
    self._endpoint_list = endpoint_list
    self._check_up = check_up

    # Tell the endpoint what its IP is
    for endpoint in self._endpoint_list:
      endpoint.set_ip(self._ip)
      
  @property
  def endpoint_list(self):
    return self._endpoint_list

  @property
  def name(self):
    return self._name

  @property
  def ip(self):
    return self._ip
  
  @property
  def check_up(self):
    return self._check_up

