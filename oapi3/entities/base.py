''' Module contains base Entity class '''
import abc


class Entity(abc.ABC):
    ''' Base entity class '''

    __slots__ = ['obj']

    def __init__(self, obj: dict):
        self.obj = obj
