"""Defines a service, meanig a combination of port and protocol."""


class Service(object):
  """A generic service."""

  def __init__(self, protocol, port, url="/", auth=None):

    self._protocol = protocol
    self._port = port
    self._url = url
    self._auth = auth
  
  def get_protocol(self):
    return self._protocol

  def get_port(self):
    return self._port

  def get_url(self):
    return self._url

  def get_auth(self):
    return self._auth

  def requires_auth(self):
    return (self._auth != None)

  def __str__(self):
    return self.__repr__()

  def __repr__(self):
    return "{0}://[IP]{1}:{2} {3}".format(
        self._protocol, 
        self._url, 
        self._port, 
        self._auth)


class HttpService(Service):
  """A generic HTTP service, running on port 80 at the root."""

  def __init__(self, port="80", url="/", auth=None):
    Service.__init__(self, protocol="http", port=port, url=url, auth=auth)


class HttpsService(Service):
  """A generic HTTPS service, running on port 443."""

  def __init__(self, port="443", url="/", auth=None):
    Service.__init__(self, protocol="https", port=port, url=url, auth=auth)

