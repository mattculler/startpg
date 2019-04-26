"""Defines a service, meaning a use for a machine."""

from auths import *

class AbstractService(object):
  """A generic service."""

  def __init__(
      self, 
      port, 
      service_name, 
      description="", 
      protocol=None, 
      url="/", 
      auth=None):
    self._port = port
    self._service_name = service_name
    self._description = description
    self._protocol = protocol
    self._url = url
    self._auth = auth

    self._ip = None

  @property
  def ip(self):
    return self._ip

  @ip.setter
  def ip(self, ip):
    """Called from the owning Machine to set the IP after instantiation."""
    self._ip = ip

  @property
  def description(self):
    return self._description

  @property
  def protocol(self):
    return self._protocol

  @property
  def port(self):
    return self._port

  @property
  def url(self):
    return self._url

  @property
  def auth(self):
    return self._auth

  def get_full_url(self, with_auth=True):
    return "{}://{}{}:{}{}".format(
        self._protocol, 
        (self._auth.get_url_prefix()
          if type(self._auth) == HttpBasicAuth and with_auth 
          else ""),
        self._ip,
        self._port,
        self._url)

  def requires_auth(self):
    return (self._auth != None)

  def __str__(self):
    return self.__repr__()

  def __repr__(self):
    return self.get_full_url()


class HttpService(AbstractService):
  """A generic HTTP service, running on port 80 at the root."""

  def __init__(self, port="80", description="", url="/", auth=None):
    AbstractService.__init__(
        self, 
        port, 
        "http", 
        description=description,
        protocol="http", 
        url=url, 
        auth=auth)


class HttpsService(AbstractService):
  """A generic HTTPS service, running on port 443."""

  def __init__(self, port="443", description="", url="/", auth=None):
    AbstractService.__init__(
        self, 
        port, 
        "https", 
        description=description,
        protocol="https", 
        url=url, 
        auth=auth)

class DelugeService(AbstractService):
  """A Deluge torrent daemon service."""

  def __init__(self, port="58846"):
    AbstractService.__init__(self, port, "deluge", url=None)
