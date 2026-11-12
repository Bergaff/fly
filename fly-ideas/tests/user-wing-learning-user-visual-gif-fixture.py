"""Verify user-supplied GIF timing and visual consistency, not hidden model inputs."""
from pathlib import Path
import hashlib
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / 'experiments' / 'reports'


def decode(name, digest):
    path = REPORTS / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    image = Image.open(path)
    assert image.size == (384, 128) and image.n_frames == 49
    frames = []
    long_frames = []
    for i in range(image.n_frames):
        image.seek(i)
        duration = image.info['duration']
        assert duration in (40, 80)
        if duration == 80:
            long_frames.append(len(frames))
        frames.extend([np.asarray(image.convert('RGB')).copy()] * (duration // 40))
    assert len(frames) == 51 and long_frames == [12, 37]
    return np.asarray(frames)


def main():
    vision = decode('user-wing-learning-user-observer-vision.gif', 'af87df3b60c77dd02e16056fba17bd8e55477bbf6fe916c6d5ba42c997b2b11f')
    blocks = decode('user-wing-learning-user-model-input.gif', '8e9b6131433d21d646cb717a00e41fa571a376ff7648af0451c681d8de6a840a')
    raw = vision[:, ::4, ::4].astype(float)
    assert np.array_equal(vision, raw.astype(np.uint8).repeat(4, axis=1).repeat(4, axis=2))
    coarse = blocks[:, ::16, ::16].astype(float)
    assert np.array_equal(blocks, coarse.astype(np.uint8).repeat(16, axis=1).repeat(16, axis=2))
    assert np.array_equal(coarse[..., 0], coarse[..., 1]) and np.array_equal(coarse[..., 1], coarse[..., 2])
    approx = np.rint(raw.mean(axis=-1).reshape(51, 8, 4, 24, 4).mean(axis=(2, 4)))
    observed = coarse[..., 0]
    delta = np.abs(approx - observed)
    assert delta.size == 9792 and np.count_nonzero(delta) == 8 and np.max(delta) == 1
    assert np.max(delta[:4]) == 0
    change = np.abs(np.diff(observed, axis=0)).mean(axis=(1, 2))
    assert np.argmax(change) == 3  # 0.12 -> 0.16 s
    assert abs(change[3] - 5.197916666666667) < 1e-10
    assert abs(change[5:].mean() - 1.814351851851852) < 1e-10
    for v in (vision, blocks):
        assert np.any(v[:, :, :192] != v[:, :, 192:])
    print('GIF sources, timing, RGB to displayed blocks and temporal differences verified')


if __name__ == '__main__':
    main()
