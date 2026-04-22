import asyncio
import pyvisa
from unitelabs.cdk import sila


class DMMController(sila.Feature):
    """
    SiLA Feature for Keysight 34465A Digital Multimeter.
    """

    def __init__(self, resource_name: str):
        super().__init__(
            originator="org.lab",
            category="measurement",
            version="1.0",
            maturity_level="Draft",
        )
        self._resource_name = resource_name
        self._rm = pyvisa.ResourceManager('@py')
        self._dmm = None
        self._connect()

    def _connect(self):
        self._dmm = self._rm.open_resource(self._resource_name)
        self._dmm.timeout = 5000
        self._dmm.write("*RST")
        self._dmm.write("*CLS")
        self._dmm.write("CONF:RES")

    @sila.ObservableProperty(name="Resistance")
    async def subscribe_resistance(self) -> sila.Stream[float]:
        """Subscribe to live resistance readings in Ohms."""
        while True:
            try:
                raw = self._dmm.query("READ?")
                yield float(raw)
            except Exception:
                yield 0.0
            await asyncio.sleep(0.2)

    @sila.UnobservableCommand()
    async def set_mode_resistance(self) -> None:
        """Configure DMM to measure resistance."""
        self._dmm.write("CONF:RES")

    @sila.UnobservableCommand()
    async def set_mode_dc_voltage(self) -> None:
        """Configure DMM to measure DC voltage."""
        self._dmm.write("CONF:VOLT:DC")

    @sila.UnobservableCommand()
    async def set_mode_dc_current(self) -> None:
        """Configure DMM to measure DC current."""
        self._dmm.write("CONF:CURR:DC")

    @sila.UnobservableProperty()
    async def get_reading(self) -> float:
        """Get a single measurement reading."""
        try:
            return float(self._dmm.query("READ?"))
        except Exception:
            return 0.0
