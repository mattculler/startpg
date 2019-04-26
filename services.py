"""Defines a service, meaning a use for a machine."""

from auths import *

class AbstractService(object):
  """A generic service.
  protocol://auth@host.domain:port/path
  """

  def __init__(
      self, 
      protocol=None, 
      auth=None,
      host=None,
      domain="",
      port="",
      path="/",
      description=""):
    self._protocol = protocol
    self._auth = auth
    self._host = host
    self._domain = domain
    self._port = port
    self._path = path

    self._description = description
  
  @property
  def protocol(self):
    return self._protocol
  
  @property
  def auth(self):
    return self._auth

  @property
  def host(self):
    return self._host

  @property
  def domain(self):
    return self._domain

  @domain.setter
  def domain(self, domain):
    """Called from the owning Machine to set the IP after instantiation."""
    # Ignore if we already set it (via this constructor)
    if not self._domain:
      self._domain = domain

  @property
  def port(self):
    return self._port

  @property
  def path(self):
    return self._path

  @property
  def description(self):
    return self._description

  def get_partially_qualified_domain_name(self, labels):
    """Returns the domain name with the specified labels."""
    pqdn = ""
    check = lambda label: label in labels and getattr(self, label)
    if check("protocol"):
      pqdn += self.protocol + "://"
    if check("auth") and type(self.auth) == HttpBasicAuth:
      pqdn += str(self.auth)
    if check("host"):
      pqdn += self.host + "."
    pqdn += self.domain
    if check("port"):
      pqdn += ":" + self.port
    if check("path"):
      pqdn += self.path
    return pqdn

  def get_fqdn(self, with_auth=True):
    """Returns the fully-qualified domain name."""
    return "{}://{}{}{}:{}{}".format(
        self.protocol, 
        self.auth if type(self.auth) == HttpBasicAuth and with_auth else "",
        self.host + "." if self._host else "",
        self.domain,
        self.port,
        self.path)

  def requires_auth(self):
    return (self._auth != None)

  def __str__(self):
    return self._description + ": " + self.__repr__()

  def __repr__(self):
    return self.get_fqdn()


class HttpService(AbstractService):
  """A generic HTTP service, by default running on port 80 at the root."""

  def __init__(self, port="80", **kwargs):
    AbstractService.__init__(
        self, 
        protocol="http", 
        port=port,
        **kwargs)


class HttpsService(AbstractService):
  """A generic HTTPS service, running on port 443."""

  def __init__(self, port="443", **kwargs):
    AbstractService.__init__(
        self, 
        protocol="https",
        port=port,
        **kwargs)


class DelugeService(AbstractService):
  """A Deluge torrent daemon service."""

  def __init__(
      self, 
      port="58846", 
      protocol="http", 
      description="deluge", 
      **kwargs):
    AbstractService.__init__(
        self, 
        port=port, 
        protocol="http",
        description=description,
        **kwargs)
