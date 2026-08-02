from enum import Enum


class ChannelAction(str, Enum):
    ADD = "add"
    REMOVE = "remove"