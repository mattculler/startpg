"""Defines a service, meaning a use for a machine."""


class AbstractService(object):
  """A generic service."""

  def __init__(self, port, service_name, protocol=None, url="/", auth=None):
    self._port = port
    self._service_name = service_name
    self._protocol = protocol
    self._url = url
    self._auth = auth

  def set_ip(self, ip):
    """Called from the owning Machine to set the IP after instantiation."""
    self._ip = ip

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
    return "{0}://{1}{2}:{3} {4}".format(
        self._protocol, 
        self._ip,
        self._url, 
        self._port, 
        self._auth)


class HttpService(AbstractService):
  """A generic HTTP service, running on port 80 at the root."""

  def __init__(self, port="80", url="/", auth=None):
    AbstractService.__init__(self, port, "http", protocol="http", url=url, auth=auth)


class HttpsService(AbstractService):
  """A generic HTTPS service, running on port 443."""

  def __init__(self, port="443", url="/", auth=None):
    AbstractService.__init__(self, port, "https", protocol="https", url=url, auth=auth)

class DelugeService(AbstractService):
  """A Deluge torrent daemon service."""

  def __init__(self, port="58846"):
    # Most of this does not apply to DelugeService
    AbstractService.__init__(self, port, "deluge", protocol=None, url=None, auth=None)
