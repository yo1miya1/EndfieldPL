"""把原生EXR mip链压成RGBAHalf数据；保留源行序和所有预滤波mip。"""
from pathlib import Path
import hashlib, json
import numpy as np
from read_exr import read

root = Path(__file__).resolve().parents[3]
base = root / 'pro/Authoring/Extracted/SI1/TexturesNative'
index = []
for folder in sorted(base.iterdir()):
    if not folder.is_dir() or not (folder / 'export.json').is_file(): continue
    manifest = json.loads((folder / 'export.json').read_text(encoding='utf-8'))
    chunks = []; offset = 0
    for mip in manifest['mips']:
        pixels = read(folder / mip['path'])
        if pixels.shape != (mip['height'], mip['width'], 4): raise ValueError(str(folder))
        data = pixels.astype('<f2').tobytes()
        chunks.append(data); mip['byteOffset'] = offset; mip['byteSize'] = len(data); offset += len(data)
    blob = b''.join(chunks); (folder / 'rgba-half.bin').write_bytes(blob)
    manifest.update(data='rgba-half.bin', format='RGBAHalf', componentType='little-endian float16',
                    byteSize=len(blob), sha256=hashlib.sha256(blob).hexdigest(),
                    mipOrder='mip0..N; within each mip D3D top-down rows, then x, RGBA; no row flip',
                    unityTextureLinear=True, regenerateMips=False)
    (folder / 'import.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    index.append(dict(resourceId=manifest['resourceId'], importPath=folder.relative_to(base).as_posix()+'/import.json',
                      sha256=manifest['sha256'], width=manifest['width'], height=manifest['height'], mipCount=manifest['mipCount']))
(base / 'index.json').write_text(json.dumps(dict(textures=index), indent=2), encoding='utf-8')
print('Published', len(index), 'native linear RGBAHalf mip chains')
