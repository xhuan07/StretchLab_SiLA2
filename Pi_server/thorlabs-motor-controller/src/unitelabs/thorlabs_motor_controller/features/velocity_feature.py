import asyncio
from pylablib.devices import Thorlabs
from unitelabs.cdk import sila


class VelocityControl(sila.Feature):
    """
    SiLA Feature for controlling the velocity of a motor stage.
    """

    def __init__(self, device: Thorlabs.KinesisMotor):
        super().__init__(
            originator="org.lab",
            category="motion",
            version="1.0",
            maturity_level="Draft",
        )
        self._device = device

    @sila.ObservableProperty(name="Current Velocity")
    async def subscribe_current_velocity(self) -> sila.Stream[float]:
        """Subscribe to the current max velocity in mm/s."""
        while True:
            vel_params = self._device.get_velocity_parameters()
            yield vel_params[2] * 1000.0
            await asyncio.sleep(1.0)

    @sila.UnobservableCommand()
    async def set_velocity(self, velocity: float) -> None:
        """
        Set the cruising velocity of the stage.

        Args:
          Velocity: Target velocity in mm/s.
        """
        current_params = self._device.get_velocity_parameters()
        self._device.setup_velocity(current_params[0], current_params[1], velocity / 1000.0)
