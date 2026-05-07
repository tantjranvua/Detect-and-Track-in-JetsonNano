from typing import Dict, List, Any, Tuple


def _clamp_box(box: Tuple[int, int, int, int], frame_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    w, h = frame_size
    x1 = max(0, min(w - 1, x1))
    y1 = max(0, min(h - 1, y1))
    x2 = max(0, min(w, x2))
    y2 = max(0, min(h, y2))
    return x1, y1, x2, y2


def _box_iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    union_area = area_a + area_b - inter_area
    if union_area <= 0:
        return 0.0
    return float(inter_area) / float(union_area)


def _smooth_box(prev_box: Tuple[int, int, int, int], new_box: Tuple[int, int, int, int], alpha: float) -> Tuple[int, int, int, int]:
    a = max(0.0, min(1.0, float(alpha)))
    x1 = int(round((1.0 - a) * prev_box[0] + a * new_box[0]))
    y1 = int(round((1.0 - a) * prev_box[1] + a * new_box[1]))
    x2 = int(round((1.0 - a) * prev_box[2] + a * new_box[2]))
    y2 = int(round((1.0 - a) * prev_box[3] + a * new_box[3]))
    return x1, y1, x2, y2


class TargetTracker:
    def __init__(
        self,
        max_missing_frames: int = 15,
        iou_match_threshold: float = 0.35,
        smooth_alpha: float = 0.55,
    ) -> None:
        self.max_missing_frames = int(max_missing_frames)
        self.iou_match_threshold = float(iou_match_threshold)
        self.smooth_alpha = float(smooth_alpha)
        self.selected_target_id = None
        self._next_track_id = 1
        self._tracks: Dict[int, Dict[str, Any]] = {}

    def _new_track(self, detection: Dict[str, Any], frame_size: Tuple[int, int]) -> Dict[str, Any]:
        raw_box = tuple(detection["box"])
        box = _clamp_box(raw_box, frame_size)
        track = {
            "track_id": self._next_track_id,
            "box": box,
            "confidence": float(detection.get("confidence", 0.0)),
            "missing_frames": 0,
            "age": 1,
            "detected": True,
        }
        self._next_track_id += 1
        return track

    def _to_output(self, track: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "track_id": track["track_id"],
            "box": track["box"],
            "confidence": track["confidence"],
            "missing_frames": track["missing_frames"],
            "age": track["age"],
            "detected": track["detected"],
        }

    def active_track_ids(self) -> List[int]:
        return sorted(list(self._tracks.keys()))

    def update(self, detections: List[Dict[str, Any]], frame_size: Tuple[int, int]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for det in detections:
            box = tuple(det.get("box", (0, 0, 0, 0)))
            x1, y1, x2, y2 = _clamp_box(box, frame_size)
            if x2 <= x1 or y2 <= y1:
                continue
            candidates.append(
                {
                    "box": (x1, y1, x2, y2),
                    "confidence": float(det.get("confidence", 0.0)),
                }
            )

        track_ids = sorted(list(self._tracks.keys()))
        scored_pairs: List[Tuple[float, int, int]] = []
        for t_idx, track_id in enumerate(track_ids):
            t_box = self._tracks[track_id]["box"]
            for d_idx, det in enumerate(candidates):
                iou = _box_iou(t_box, det["box"])
                if iou >= self.iou_match_threshold:
                    scored_pairs.append((iou, t_idx, d_idx))

        scored_pairs.sort(key=lambda item: item[0], reverse=True)

        matched_track_ids = set()
        matched_det_ids = set()
        matches: List[Tuple[int, int]] = []
        for _, t_idx, d_idx in scored_pairs:
            track_id = track_ids[t_idx]
            if track_id in matched_track_ids or d_idx in matched_det_ids:
                continue
            matched_track_ids.add(track_id)
            matched_det_ids.add(d_idx)
            matches.append((track_id, d_idx))

        for track_id, det_idx in matches:
            track = self._tracks[track_id]
            det = candidates[det_idx]
            track["box"] = _smooth_box(track["box"], det["box"], self.smooth_alpha)
            track["confidence"] = det["confidence"]
            track["missing_frames"] = 0
            track["age"] += 1
            track["detected"] = True

        unmatched_track_ids = [track_id for track_id in track_ids if track_id not in matched_track_ids]
        for track_id in unmatched_track_ids:
            track = self._tracks[track_id]
            track["missing_frames"] += 1
            track["age"] += 1
            track["detected"] = False

        for d_idx, det in enumerate(candidates):
            if d_idx in matched_det_ids:
                continue
            new_track = self._new_track(det, frame_size)
            self._tracks[new_track["track_id"]] = new_track

        stale_track_ids = [
            track_id
            for track_id, track in self._tracks.items()
            if int(track["missing_frames"]) > self.max_missing_frames
        ]
        for track_id in stale_track_ids:
            del self._tracks[track_id]

        outputs = [self._to_output(track) for _, track in sorted(self._tracks.items(), key=lambda item: item[0])]
        return outputs
