import copy

from services import *

class Machine(object):

  def __init__(self, name, domain, endpoints=None, check_up=True):
    self._name = name
    if endpoints:
      self._endpoints = endpoints
    else:
      self._endpoints = [HttpService()]
    self._check_up = check_up

    # Tell the endpoint what its domain is.  If domain is not set here in machine, it must be
    #  set on all the endpoints individually.
    self._domain = domain
    for endpoint in self._endpoints:
      endpoint.domain = self._domain
      
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
  def check_up(self):
    return self._check_up

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
        if endpoint == other_endpoint:
          continue
        if getattr(endpoint, label) != getattr(other_endpoint, label):
          include_labels.add(label)
          continue

    return endpoint.get_partially_qualified_domain_name(include_labels)

    
