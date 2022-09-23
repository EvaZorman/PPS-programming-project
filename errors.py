"""
BGP Error classes and functionality.

This part will handle the BGP Error structures.
Check https://www.iana.org/assignments/bgp-parameters/bgp-parameters.xhtml#bgp-parameters-3
"""


class BGPError:
    pass


class MessageHeaderError(BGPError):
    pass


class OpenMessageError(BGPError):
    pass


class UpdateMessageError(BGPError):
    pass


class HoldTimerExpiredError(BGPError):
    pass


class FiniteStateMachineError(BGPError):
    pass


class CeaseError(BGPError):
    pass


class RefreshMessageError(BGPError):
    pass
