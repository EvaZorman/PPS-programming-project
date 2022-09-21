"""
BGP Message classes and functionality.

This part will handle the BGP Messages structure, etc.
See https://www.iana.org/assignments/bgp-parameters/bgp-parameters.xhtml#bgp-parameters-3
"""


class BGPMessage:
    pass


class KeepAliveMessage(BGPMessage):
    pass


class NotificationMessage(BGPMessage):
    pass


class OpenMessage(BGPMessage):
    pass


class UpdateMessage(BGPMessage):
    pass


