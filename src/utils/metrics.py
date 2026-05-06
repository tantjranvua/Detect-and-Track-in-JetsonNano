import time


class FpsCounter:
    def __init__(self, window_sec: float = 1.0) -> None:
        self.window_sec = window_sec
        self.frame_count = 0
        self.window_start = time.perf_counter()
        self.last_fps = 0.0

    def tick(self) -> float:
        self.frame_count += 1
        now = time.perf_counter()
        dt = now - self.window_start
        if dt >= self.window_sec:
            self.last_fps = self.frame_count / dt
            self.frame_count = 0
            self.window_start = now
        return self.last_fps
