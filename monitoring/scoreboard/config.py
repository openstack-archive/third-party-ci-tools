
import ConfigParser

CONFIG_FILE = '/etc/ci-scoreboard/ci-scoreboard.conf'
CONFIG_SECTION = 'scoreboard'


class Config:
    def __init__(self):
        self._cfg = ConfigParser.ConfigParser()
        self._cfg.read(CONFIG_FILE)

    def _value(self, option):
        if self._cfg.has_option(CONFIG_SECTION, option):
            return self._cfg.get(CONFIG_SECTION, option)
        return None

    def _int_value(self, option):
        if self._cfg.has_option(CONFIG_SECTION, option):
            return self._cfg.getint(CONFIG_SECTION, option)
        return None

    def _float_value(self, option):
        if self._cfg.has_option(CONFIG_SECTION, option):
            return self._cfg.getfloat(CONFIG_SECTION, option)
        return None

    def gerrit_user(self):
        return self._value('GERRIT_USER')

    def gerrit_key(self):
        return self._value('GERRIT_KEY')

    def gerrit_hostname(self):
        return self._value('GERRIT_HOSTNAME')

    def gerrit_port(self):
        return self._int_value('GERRIT_PORT')

    def gerrit_keepalive(self):
        return self._int_value('GERRIT_KEEPALIVE')

    def db_uri(self):
        return self._value('DB_URI')

    def log_file(self):
        return self._value('LOG_FILE_LOCATION')
