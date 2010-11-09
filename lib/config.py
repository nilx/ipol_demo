"""
config dictionary with file backend
"""
# pylint: disable=C0103


import os.path
import ConfigParser

class file_dict(dict):
    """
    handle a config file as a dictionary
    """
    def __init__(self, location):
        """
        initalize a dictionary from a config file

        @param location: folder containing this config file (index.cfg),
               or full file path
        """
        dict.__init__(self)
        if os.path.isdir(location):
            self.fname = os.path.join(location, "index.cfg")
        else:
            self.fname = os.path.join(location)

        # read the config file as a dictionary
        cfg = ConfigParser.RawConfigParser()
        cfg.read(self.fname)
        for section in cfg.sections():
            self[section] = dict(cfg.items(section))

    def save(self):
        """
        save the (updated) dictionary to the config file
        """
        # TODO: rename commit()?
        cfg = ConfigParser.RawConfigParser()
        for section in self.keys():
            cfg.add_section(section)
            for option in self[section].keys():
                cfg.set(section, option,
                        self[section][option])
        cfg_file = open(self.fname, 'w')
        cfg.write(cfg_file)
        cfg_file.close()
