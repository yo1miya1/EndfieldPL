from pathlib import Path
import json,hashlib
from read_exr import read
root=Path(__file__).resolve().parents[3]
out=root/'pro/Authoring/Extracted/SI1/EnvironmentReflection/11550'
doc=json.loads((out/'all-mips.json').read_text(encoding='utf-8'))
chunks=[]
for entry in doc['files']:
    pixels=read(out/entry['path'])
    path=(out/entry['path']).with_suffix('.rgba32f')
    path.write_bytes(pixels.astype('<f4').tobytes())
    chunks.append(pixels.astype('<f4').tobytes())
    entry['decodedPath']=path.relative_to(out).as_posix()
    entry['decodedBytes']=path.stat().st_size
    entry['decodedSha256']=hashlib.sha256(path.read_bytes()).hexdigest()
doc['decodedLayout']='little-endian float32 RGBA [y,x,c], y=source EXR dataWindow scanline index 0..height-1 (top row first), x=0..width-1; no flips, no face rotation'
(out/'all-mips.json').write_text(json.dumps(doc,indent=2),encoding='utf-8')
blob=out/'rgba-float4.bin';blob.write_bytes(b''.join(chunks))
(out/'import.json').write_text(json.dumps(dict(size=doc['files'][0]['width'],mipCount=doc['mips'],data=blob.name,
    faceOrder=doc['faceOrder'],layout='face-major, then mip0..7, then top-down y, then x, then float32 RGBA little-endian',
    coordinateConversionApplied=False,sha256=hashlib.sha256(blob.read_bytes()).hexdigest(),sourceFormat=doc['format']),indent=2),encoding='utf-8')
print(doc['mips'],len(doc['files']),doc['format'])
