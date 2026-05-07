from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


class FaceRecognizer:
    def __init__(
        self,
        gallery_dir: Path,
        similarity_threshold: float = 0.82,
        score_margin: float = 0.04,
        min_face_size: int = 40,
        reload_interval_sec: float = 2.0,
    ) -> None:
        self.gallery_dir = gallery_dir
        self.similarity_threshold = float(similarity_threshold)
        self.score_margin = float(score_margin)
        self.min_face_size = int(min_face_size)
        self.reload_interval_sec = float(reload_interval_sec)

        self._known_embeddings: List[np.ndarray] = []
        self._known_gray_vectors: List[np.ndarray] = []
        self._known_labels: List[str] = []
        self._last_load_ts = 0.0

    def _extract_features(self, face_bgr: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        h, w = face_bgr.shape[:2]
        if h < self.min_face_size or w < self.min_face_size:
            return None

        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (48, 48), interpolation=cv2.INTER_AREA)
        gray = cv2.equalizeHist(gray)

        gray_f = gray.astype(np.float32) / 255.0
        gray_vec = gray_f.flatten().astype(np.float32)
        gray_norm = np.linalg.norm(gray_vec)
        if gray_norm <= 1e-9:
            return None
        gray_vec = gray_vec / gray_norm

        edge = cv2.Laplacian(gray_f, cv2.CV_32F)

        embedding = np.concatenate([gray_f.flatten(), edge.flatten()]).astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm <= 1e-9:
            return None
        return embedding / norm, gray_vec

    def _list_gallery_images(self) -> List[Tuple[str, Path]]:
        images: List[Tuple[str, Path]] = []
        if not self.gallery_dir.exists():
            return images

        for person_dir in sorted(self.gallery_dir.iterdir()):
            if not person_dir.is_dir():
                continue
            label = person_dir.name
            for image_path in sorted(person_dir.iterdir()):
                if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
                    continue
                images.append((label, image_path))
        return images

    def _load_gallery(self) -> None:
        labels: List[str] = []
        embeddings: List[np.ndarray] = []
        gray_vectors: List[np.ndarray] = []

        for label, image_path in self._list_gallery_images():
            img = cv2.imread(str(image_path))
            if img is None:
                continue

            features = self._extract_features(img)
            if features is None:
                continue
            emb, gray_vec = features

            labels.append(label)
            embeddings.append(emb)
            gray_vectors.append(gray_vec)

        self._known_labels = labels
        self._known_embeddings = embeddings
        self._known_gray_vectors = gray_vectors

    def _ensure_gallery_loaded(self) -> None:
        now = cv2.getTickCount() / cv2.getTickFrequency()
        if now - self._last_load_ts < self.reload_interval_sec:
            return

        self._load_gallery()
        self._last_load_ts = now

    def recognize(self, frame: np.ndarray, box: Tuple[int, int, int, int]) -> Dict[str, object]:
        self._ensure_gallery_loaded()

        x1, y1, x2, y2 = box
        h, w = frame.shape[:2]
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(0, min(w, x2))
        y2 = max(0, min(h, y2))

        if x2 <= x1 or y2 <= y1:
            return {"label": "unknown", "score": 0.0, "known": False, "pixel_similarity": 0.0, "rival_score": 0.0}

        face_crop = frame[y1:y2, x1:x2]
        features = self._extract_features(face_crop)
        if features is None:
            return {"label": "unknown", "score": 0.0, "known": False, "pixel_similarity": 0.0, "rival_score": 0.0}
        emb, gray_vec = features

        if not self._known_embeddings:
            return {"label": "unknown", "score": 0.0, "known": False, "pixel_similarity": 0.0, "rival_score": 0.0}

        gallery_matrix = np.vstack(self._known_embeddings)
        scores = gallery_matrix.dot(emb)
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        best_label = self._known_labels[best_idx]
        best_pixel_similarity = 0.0
        if self._known_gray_vectors and best_idx < len(self._known_gray_vectors):
            best_pixel_similarity = float(np.dot(gray_vec, self._known_gray_vectors[best_idx]))

        per_label_best: Dict[str, float] = {}
        for label, score in zip(self._known_labels, scores):
            score_f = float(score)
            if label not in per_label_best or score_f > per_label_best[label]:
                per_label_best[label] = score_f

        rival_scores = [score for label, score in per_label_best.items() if label != best_label]
        best_rival_score = -1.0
        if rival_scores:
            best_rival_score = float(max(rival_scores))
            margin_ok = (best_score - best_rival_score) >= self.score_margin
        else:
            # Nếu gallery chỉ có 1 nhãn thì không áp margin để tránh unknown oan.
            margin_ok = True

        if best_score < self.similarity_threshold or not margin_ok:
            return {
                "label": "unknown",
                "score": best_score,
                "known": False,
                "pixel_similarity": best_pixel_similarity,
                "rival_score": best_rival_score,
            }

        return {
            "label": best_label,
            "score": best_score,
            "known": True,
            "pixel_similarity": best_pixel_similarity,
            "rival_score": best_rival_score,
        }


def build_face_recognizer(cfg: Dict[str, object]) -> Optional[FaceRecognizer]:
    detection_cfg = cfg.get("detection", {})
    face_rec_cfg = detection_cfg.get("face_recognize", {})
    if not face_rec_cfg.get("enabled", False):
        return None

    gallery_dir = Path(face_rec_cfg.get("gallery_dir", "data/face_gallery"))
    if not gallery_dir.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        gallery_dir = project_root / gallery_dir

    return FaceRecognizer(
        gallery_dir=gallery_dir,
        similarity_threshold=float(face_rec_cfg.get("similarity_threshold", 0.82)),
        score_margin=float(face_rec_cfg.get("score_margin", 0.04)),
        min_face_size=int(face_rec_cfg.get("min_face_size", 40)),
        reload_interval_sec=float(face_rec_cfg.get("reload_interval_sec", 2.0)),
    )
