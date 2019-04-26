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
      description="",
      auth_type=None,
      show_url=True,
      check=True):
    self._protocol = protocol
    self._auth = auth
    self._host = host
    self._domain = domain
    self._port = port
    self._path = path

    self._description = description
    self._auth_type = auth_type
    self._show_url = show_url
    self._check = check
  
  @property
  def protocol(self):
    return self._protocol
  
  @property
  def auth(self):
    return self._auth

  @auth.setter
  def auth(self, auth):
    if not self._auth:
      self._auth = auth

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

  @property
  def auth_type(self):
    return self._auth_type

  @auth_type.setter
  def auth_type(self, auth_type):
    if not self._auth_type:
      self._auth_type = auth_type

  @property
  def show_url(self):
    return self._show_url

  @property
  def check(self):
    return self._check

  @check.setter
  def check(self, check):
    self._check = check


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

  def __str__(self):
    return self._description + ": " + self.__repr__()

  def __repr__(self):
    return self.get_fqdn()


class HttpService(AbstractService):
  """A generic HTTP service, by default running on port 80 at the root."""
  def __init__(self, port="80", auth_type=HttpBasicAuth, **kwargs):
    AbstractService.__init__(
        self, 
        protocol="http", 
        port=port,
        auth_type=auth_type,
        **kwargs)

class HttpsService(AbstractService):
  """A generic HTTPS service, running on port 443."""
  def __init__(self, port="443", auth_type=HttpBasicAuth, **kwargs):
    AbstractService.__init__(
        self, 
        protocol="https",
        port=port,
        auth_type=auth_type,
        **kwargs)

class SshService(AbstractService):
  """It's SSH, dawg."""
  def __init__(self, port="22", auth_type=SshAuth, **kwargs):
    AbstractService.__init__(
        self,
        protocol="ssh",
        port=port,
        auth_type=auth_type,
        show_url=False,
        **kwargs)
  
