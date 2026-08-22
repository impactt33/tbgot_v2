from enum import Enum


class ChannelAction(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"