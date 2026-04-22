import asyncio
from pylablib.devices import Thorlabs
from unitelabs.cdk import sila


class MotorController(sila.Feature):
    """
    SiLA Feature for controlling a Thorlabs KDC101 motor stage.
    """

    def __init__(self, device: Thorlabs.KinesisMotor):
        super().__init__(
            originator="org.lab",
            category="motion",
            version="1.0",
            maturity_level="Draft",
        )
        self._device = device

    @sila.ObservableProperty(name="Current Position")
    async def subscribe_position(self) -> sila.Stream[float]:
        """Subscribe to the current stage position in mm."""
        while True:
            yield self._device.get_position() * 1000.0
            await asyncio.sleep(0.5)

    @sila.ObservableCommand()
    async def move_to_position(self, target_position: float, *, status: sila.Status) -> None:
        """
        Move the stage to an absolute position.

        Args:
          TargetPosition: Target position in mm.
        """
        self._device.move_to(target_position / 1000.0)
        while self._device.is_moving():
            await asyncio.sleep(0.2)

    @sila.ObservableCommand()
    async def move_by_distance(self, distance: float, *, status: sila.Status) -> None:
        """
        Move the stage by a relative distance.

        Args:
          Distance: Distance to move in mm.
        """
        self._device.move_by(distance / 1000.0)
        while self._device.is_moving():
            await asyncio.sleep(0.2)

    @sila.ObservableCommand()
    async def home(self, *, status: sila.Status) -> None:
        """Run the homing sequence to find the zero position."""
        self._device.home(force=True)
        while self._device.is_moving():
            await asyncio.sleep(0.5)

    @sila.UnobservableCommand()
    async def stop(self) -> None:
        """Emergency stop - immediately halt all motor movement."""
        self._device.stop(immediate=True)
