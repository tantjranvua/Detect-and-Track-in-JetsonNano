import time


class ServoController:
    def __init__(self, log_interval_sec: float = 0.2) -> None:
        self.enabled = False
        self._last_pan_deg = 0.0
        self._last_tilt_deg = 0.0
        self._last_command = ""
        self._last_log_ts = 0.0
        self._log_interval_sec = max(0.05, float(log_interval_sec))

    def set_angle(self, pan_deg: float, tilt_deg: float) -> None:
        pan_delta = float(pan_deg) - self._last_pan_deg
        tilt_delta = float(tilt_deg) - self._last_tilt_deg

        commands = []
        if pan_delta > 1e-6:
            commands.append("RIGHT")
        elif pan_delta < -1e-6:
            commands.append("LEFT")

        if tilt_delta > 1e-6:
            commands.append("DOWN")
        elif tilt_delta < -1e-6:
            commands.append("UP")

        command_text = " ".join(commands) if commands else "HOLD"
        now = time.perf_counter()
        should_log = (
            command_text != self._last_command
            or now - self._last_log_ts >= self._log_interval_sec
        )
        if should_log:
            print(
                f"[SERVO-DEMO] cmd={command_text} "
                f"pan={pan_deg:.2f} tilt={tilt_deg:.2f}"
            )
            self._last_log_ts = now
            self._last_command = command_text

        self._last_pan_deg = float(pan_deg)
        self._last_tilt_deg = float(tilt_deg)
