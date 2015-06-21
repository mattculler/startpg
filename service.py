"""Defines a service, meanig a combination of port and protocol."""

class Service(object):
  """A generic service."""

  def __init__(self, protocol, port, url="/"):
    self._protocol = protocol
    self._port = port
    self._url = url
  
  def get_protocol(self):
    return self._protocol

  def get_port(self):
    return self._port

  def get_url(self):
    return self._url


class HttpService(Service):
  """A generic HTTP service, running on port 80 at the root."""

  def __init__(self, port="80", url="/"):
    Service.__init__(self, protocol="http", port=port, url=url)


class HttpsService(Service):
  """A generic HTTPS service, running on port 443."""

  def __init__(self, port="443", url="/"):
    Service.__init__(self, protocol="https", port=port, url=url)
