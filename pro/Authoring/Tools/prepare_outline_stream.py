"""恢复617/635共享顶点的切线空间平滑法线XY，不改变原网格或捕获姿态。"""
from pathlib import Path
import hashlib, json, struct
import numpy as np

root=Path(__file__).resolve().parents[3]
base=root/'pro/Authoring/Extracted/SI1'
folder=base/'Outline/617'
raw=(folder/'source-vb1.bin').read_bytes()
mesh=(base/'Source/world2/eid-617.world2').read_bytes()
count,index_count,uv_count,flags=struct.unpack('<4I',mesh[:16])
# 原TEXCOORD0(float2)与TEXCOORD4(SNORM8x4)共用slot1、stride12。
uv=np.ndarray((count,2),dtype='<f4',buffer=raw,offset=0,strides=(12,4))
world_uv=np.frombuffer(mesh,dtype='<f4',count=count*2,offset=16+count*40).reshape(count,2)
if not np.array_equal(uv,world_uv):raise ValueError('Source vertex order differs from world2')
packed=np.ndarray((count,2),dtype='i1',buffer=raw,offset=8,strides=(12,1))
normal=np.maximum(packed.astype(np.float32)/127,-1).astype('<f4')
# flags&2已携带同一语义流，位于UV后、IB前；运行导入直接复用，无需再加载辅助binary。
ts_offset=16+count*(40+uv_count*8)+(count*12 if flags&1 else 0)
existing=np.frombuffer(mesh,dtype='<f4',count=count*2,offset=ts_offset).reshape(count,2)
if not flags&2 or not np.array_equal(existing,normal):raise ValueError('Existing world2 tangent-space stream differs')
path=folder/'outline-normal-ts.float2';path.write_bytes(normal.tobytes())
result=dict(sourceEvent=635,geometryEvent=617,vertexCount=count,indexCount=index_count,
    outlineNormalPath=path.relative_to(base).as_posix(),format='little-endian float32 [vertex][xy]',
    target='Mesh UV2 / TEXCOORD2; no axis conversion of tangent-space coefficients',
    sourceAttribute='TEXCOORD4.xy, slot1 offset8 stride12 R8G8B8A8_SNORM',
    sourceDecoding='max(signedByte / 127, -1)',vertexOrderCheck='all UV0 float32 components bit-exact with world2',
    existingWorld2Stream=dict(flag=2,byteOffset=ts_offset,byteSize=count*8,maximumFloat32Error=0,
                             location='after UV arrays and optional alt positions, before uint32 IB',runtimeUse='Read world2 flags&2 directly into Mesh UV2'),
    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),sourceBufferSha256=hashlib.sha256(raw).hexdigest(),
    reconstruction='normalize(T*xy.x + cross(N,T)*tangent.w*xy.y + N*sqrt(1-min(1,dot(xy,xy))))',
    sourceWidth=.5,sourceSmoothNormalEnabled=True,sourceDepthExtrusion=0,
    mask=dict(resourceId=1727219,widthChannel='R',depthChannel='G',lod=0),
    alphaClip=dict(resourceId=62,channel='R',threshold=.5,constantWhite=True))
(folder/'import.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
(base/'Outline/import.json').write_text(json.dumps(dict(parts=[dict(sourceEvent=617,outlineNormalPath=result['outlineNormalPath'])]),indent=2),encoding='utf-8')
print('Published',count,'outline smooth-normal XY values; UV vertex order matches exactly')
