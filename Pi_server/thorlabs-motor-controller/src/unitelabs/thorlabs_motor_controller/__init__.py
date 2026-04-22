import ctypes
import dataclasses
import collections.abc
from importlib.metadata import version

from unitelabs.cdk import Connector, ConnectorBaseConfig, SiLAServerConfig
from pylablib.devices import Thorlabs

from .features import MotorController, VelocityControl

__version__ = version("unitelabs-thorlabs-motor-controller")


@dataclasses.dataclass
class ThorlabsMotorControllerConfig(ConnectorBaseConfig):
    sila_server: SiLAServerConfig = dataclasses.field(
        default_factory=lambda: SiLAServerConfig(
            name="Thorlabs Motor Controller",
            type="Device",
            description="SiLA connector for Thorlabs KDC101 motor stage.",
            version=str(__version__),
            vendor_url="https://www.thorlabs.com/",
        )
    )
    serial_number: str = "27001592"
    stage_model: str = "MTS50-Z8"


async def create_app(config: ThorlabsMotorControllerConfig) -> collections.abc.AsyncGenerator[Connector, None]:
    lib = ctypes.CDLL("/usr/local/lib/libftd2xx.so")
    lib.FT_SetVIDPID(0x0403, 0xfaf0)

    device = Thorlabs.KinesisMotor(config.serial_number, scale=config.stage_model)

    app = Connector(config)
    app.register(MotorController(device))
    app.register(VelocityControl(device))

    yield app
