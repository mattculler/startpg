class HttpBasicAuth(object):

  def __init__(self, username, password):
    self._username = username
    self._password = password

  @property
  def username(self):
    return self._username

  @property
  def password(self):
    return self._password

  def get_tuple(self):
    return (self._username, self._password)

  def get_url_userinfo(self):
    return "{}:{}@".format(self._username, self._password)

  def __str__(self):
    return self.get_url_userinfo()
