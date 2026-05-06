class ServoController:
    def __init__(self) -> None:
        self.enabled = False

    def set_angle(self, pan_deg: float, tilt_deg: float) -> None:
        # Day 1: mo phong, chua xuat lenh phan cung that.
        _ = (pan_deg, tilt_deg)
