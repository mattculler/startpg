"""Defines a machine on the local net."""


class Machine(object):


  DEFAULT_ENDPOINT_LIST = ["/"]


  def __init__(self, name, ip, endpoint_list=DEFAULT_ENDPOINT_LIST):
    self._name = name
    self._ip = ip
    if endpoint_list:
      self._endpoint_list = endpoint_list
      


  def get_endpoints(self):
    return self._endpoint_list

  def get_name(self):
    return self._name

  def get_ip(self):
    return self._ip

