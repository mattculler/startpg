class UNP(object):
  """Just a base class that holds a username and password."""
  def __init__(self, username, password, icon=" "):
    self._username = username
    self._password = password
    self._icon = icon
  
  @property
  def username(self):
    return self._username

  @property
  def password(self):
    return self._password

  @property
  def icon(self):
    return self._icon

  def get_tuple(self):
    return (self._username, self._password)

  def __str__(self):
    return self.username + " / " + self.password


class HttpBasicAuth(UNP):
  """HTTP Basic Authentication.
  https://en.wikipedia.org/wiki/Basic_access_authentication
  """
  def __init__(self, *args, icon="&#x1F5DD;&#xFE0F; ", **kwargs):
    UNP.__init__(self, *args, icon=icon, **kwargs)

  def get_url_userinfo(self):
    return "{}:{}@".format(self._username, self._password)

  def __str__(self):
    return self.get_url_userinfo()


class HttpWebAuth(UNP):
  """Placeholder until I figure this out."""
  def __init__(self, *args, icon="🔒", **kwargs):
    UNP.__init__(self, *args, **kwargs)


class SshAuth(UNP):
  def __init__(self, *args, **kwargs):
    UNP.__init__(self, *args, **kwargs)
