"""Read uncompressed scanline EXR evidence as float32 RGBA, without color conversion."""

# 按未压缩 scanline EXR 布局读取 float32 RGBA，保持原线性值，不做颜色转换。
import struct
from pathlib import Path
import numpy as np


# 按 EXR 通道表和 scanline offset 解析，输出保持原浮点值及通道含义。
def read(path):
    data = Path(path).read_bytes()
    if data[:4] != b'\x76\x2f\x31\x01':
        raise ValueError('Not EXR')
    pos = 8
    attrs = {}

    def string(p):
        end = data.index(0, p)
        return data[p:end].decode('ascii'), end + 1

    while data[pos]:
        name, pos = string(pos)
        kind, pos = string(pos)
        size = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        attrs[name] = (kind, data[pos : pos + size])
        pos += size
    pos += 1
    if attrs['compression'][1] != b'\0':
        raise ValueError('Only uncompressed EXR evidence supported')
    x0, y0, x1, y1 = struct.unpack('<4i', attrs['dataWindow'][1])
    w = x1 - x0 + 1
    h = y1 - y0 + 1
    channel_data = attrs['channels'][1]
    channels = []
    p = 0
    while channel_data[p]:
        end = channel_data.index(0, p)
        name = channel_data[p:end].decode()
        p = end + 1
        pixeltype, linear, xs, ys = struct.unpack_from('<iB3xii', channel_data, p)
        p += 16
        if xs != 1 or ys != 1:
            raise ValueError('Subsampled EXR not supported')
        channels.append((name, {0: '<u4', 1: '<f2', 2: '<f4'}[pixeltype]))
    offsets = np.frombuffer(data, dtype='<u8', count=h, offset=pos)
    result = np.zeros((h, w, 4), np.float32)
    result[:, :, 3] = 1
    for offset in offsets:
        offset = int(offset)
        y, size = struct.unpack_from('<iI', data, offset)
        p = offset + 8
        for name, dtype in channels:
            values = np.frombuffer(data, dtype=dtype, count=w, offset=p)
            p += w * np.dtype(dtype).itemsize
            if name in 'RGBA':
                result[y - y0, :, 'RGBA'.index(name)] = values
    return result


if __name__ == '__main__':
    import argparse
    from PIL import Image

    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    a = read(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(a * 255, 0, 255).astype('uint8')).save(args.output)
    print(a.shape, 'min', a.min((0, 1)), 'max', a.max((0, 1)), 'corner', a[0, 0])
