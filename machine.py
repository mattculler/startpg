import copy

from services import *
from auths import *

class Machine(object):

  def __init__(self, name, domain, endpoints=None, check=None, auth=None):
    self._name = name
    self._domain = domain
    
    if endpoints:
      self._endpoints = endpoints
    else:
      self._endpoints = [HttpService()]

    if check is None:
      self._check = True
    else:
      self._check = check

    for endpoint in self._endpoints:
      # Tell the endpoint what its domain is.  If domain is not set here in machine, it must be
      #  set on all the endpoints individually.
      endpoint.domain = self._domain

      # If the auth was specified at this level, try to set each endpoint's preferred auth type
      if auth:
        if type(auth) == tuple and endpoint.auth_type:
          # Got a tuple and know the type we need, instantiate
          endpoint.auth = endpoint.auth_type(*auth)
        elif issubclass(type(auth), UNP):
          # Got an auth class, just pass her in
          endpoint.auth = auth
        # else we probably don't want an auth for this endpoint, it's cool

      # If the check was specified at this level, tell the individual endpoints
      endpoint.check = check
      
  @property
  def name(self):
    return self._name

  @property
  def domain(self):
    return self._domain

  @property
  def endpoints(self):
    return self._endpoints
  
  @property
  def check(self):
    return self._check

  def get_display_url(self, endpoint):
    """For a given endpoint, returns the simplest unique URL over all endpoints."""
    if endpoint not in self._endpoints:
      raise Exception("Passed in endpoint from a different machine, jackass")
    if len(self._endpoints) == 1:
      # Simplest case
      return endpoint.domain

    # If a label is different than any other in the list, show it.  Always include domain
    include_labels = {"domain"}
    for label in ["protocol", "auth", "host", "port", "path"]:
      for other_endpoint in self._endpoints:
        if endpoint == other_endpoint or not endpoint.show_url or not other_endpoint.show_url:
          # Don't compare with self or those we aren't showing URLs for
          continue
        if getattr(endpoint, label) != getattr(other_endpoint, label):
          include_labels.add(label)
          continue

    return endpoint.get_partially_qualified_domain_name(include_labels)

