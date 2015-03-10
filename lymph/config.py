import collections

import abc
import six
import yaml

from lymph.utils import import_object, Undefined


@six.add_metaclass(abc.ABCMeta)
class ConfigObject(collections.Mapping):
    @abc.abstractmethod
    def get(self, key, default=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_raw(self, key, default=None):
        raise NotImplementedError()

    @abc.abstractmethod
    def set(self, key, value):
        raise NotImplementedError()

    def __getitem__(self, key):
        return self.get(key)

    def setdefault(self, key, default):
        value = self.get(key)
        if value is None:
            self.set(key, default)
            return default
        return value

    def create_instance(self, key, default_class=None, **kwargs):
        config = self.get(key, {})
        path = config.get('class', default_class)
        cls = import_object(path)
        return cls.from_config(config, **kwargs)


class ConfigView(ConfigObject):
    def __init__(self, config, path):
        self.root = config
        self.path = path

    def __len__(self):
        return len(self.root.get_raw(self.path))

    def get_raw(self, key, default=None):
        return self.root.get_raw('%s.%s' % (self.path, key), default)

    def get(self, key, default=None):
        return self.root.get('%s.%s' % (self.path, key), default)

    def set(self, key, value):
        return self.root.set('%s.%s' % (self.path, key), value)

    def __iter__(self):
        return iter(self.root.get_raw(self.path))


class Configuration(ConfigObject):
    def __init__(self, values=None):
        self.values = values or {}
        self._instances_cache = {}

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)

    @property
    def root(self):
        return self

    def load_file(self, filename, sections=None):
        with open(filename, 'r') as f:
            self.load(f, sections=sections)

    def load(self, f, sections=None):
        for section, values in six.iteritems(yaml.load(f)):
            if sections is None or section in sections:
                self.values[section] = values

    def update(self, data):
        self.values.update(data)

    def set(self, key, data):
        path = key.split('.')
        values = self.values
        for bit in path[:-1]:
            new_values = values.setdefault(bit, {})
            if new_values is None:
                values[bit] = {}
                values = values[bit]
            else:
                values = new_values
        values[path[-1]] = data

    def get_instance(self, key, default_class=None, **kwargs):
        instance = self._instances_cache.get(key)
        if not instance:
            instance = self.create_instance(
                key, default_class=default_class, **kwargs)
            self._instances_cache[key] = instance
        return instance

    def get_raw(self, key, default=Undefined):
        path = key.split('.')
        values = self.values
        for bit in path[:-1]:
            values = values[bit]
            if values is None:
                if default is not Undefined:
                    return default
                raise KeyError(key)
        try:
            return values[path[-1]]
        except KeyError:
            if default is not Undefined:
                return default
            raise KeyError(key)

    def get(self, key, default=None):
        try:
            value = self.get_raw(key)
        except KeyError:
            return default
        if isinstance(value, dict):
            value = ConfigView(self, key)
        return value

    def __repr__(self):
        return "lymph.config.Configuration(values={values})".format(
            values=self.values)
