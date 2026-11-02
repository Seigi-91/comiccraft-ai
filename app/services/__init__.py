"""Load services on demand, so standalone tools do not import the whole graph."""
from importlib import import_module

__all__ = ['ProjectService', 'GenerateService']


def __getattr__(name):
    modules = {'ProjectService': 'project_service', 'GenerateService': 'generate_service'}
    if name not in modules:
        raise AttributeError(name)
    return getattr(import_module('app.services.' + modules[name]), name)
