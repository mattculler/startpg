"""Defines a service, meanig a combination of port and protocol."""

class Service(object):


  def __init__(self, protocol="http", port="80", url="/"):
    self._protocol = protocol
    self._port = port
    self._url = url

  
  def get_protocol(self):
    return self._protocol

  def get_port(self):
    return self._port

  def get_url(self):
    return self._url
