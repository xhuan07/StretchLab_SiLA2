import dataclasses
import collections.abc
from importlib.metadata import version

from unitelabs.cdk import Connector, ConnectorBaseConfig, SiLAServerConfig
from .features import DMMController

__version__ = version("unitelabs-keysight-34465a")

VISA_RESOURCE = "USB0::0x2A8D::0x0101::MY54504800::INSTR"


@dataclasses.dataclass
class Keysight34465aConfig(ConnectorBaseConfig):
    sila_server: SiLAServerConfig = dataclasses.field(
        default_factory=lambda: SiLAServerConfig(
            name="Keysight 34465A",
            type="Device",
            description="SiLA connector for Keysight 34465A DMM.",
            version=str(__version__),
            vendor_url="https://www.keysight.com/",
        )
    )
    visa_resource: str = VISA_RESOURCE


async def create_app(config: Keysight34465aConfig) -> collections.abc.AsyncGenerator[Connector, None]:
    app = Connector(config)
    app.register(DMMController(config.visa_resource))
    yield app
