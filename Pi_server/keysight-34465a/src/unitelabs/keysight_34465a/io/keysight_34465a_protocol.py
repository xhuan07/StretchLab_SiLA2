from unitelabs.bus import Protocol, create_usb_connection


class Keysight34465aProtocol(Protocol):
    """Underlying communication protocol for keysight 34465A."""

    def __init__(self, **kwargs):
        kwargs["vendor"] = 0xCAFE  # FIXME: set device vendor id
        kwargs["product"] = 0x0001  # FIXME: set device product id
        super().__init__(create_usb_connection, **kwargs)
