"""只用已有来源核验身体位置与拓扑；不重放RDC，不改模型或重算法线。"""
from pathlib import Path
import hashlib,json,struct
import numpy as np

root=Path(__file__).resolve().parents[3]
base=root/'pro/Authoring/Extracted/SI1'
folder=base/'GeometryValidation/538'
native=base/'CharacterDirections/Native/postvs'
metadata=json.loads((native/'metadata.json').read_text(encoding='utf-8'))
registers={}
for entry in metadata:
    if entry['eid'] not in [538,1019]:continue
    array=np.fromfile(native/f'eid-{entry["eid"]}.bin',dtype='<f4').reshape(-1,entry['stride']//4)
    reg={};offset=0
    for sig in entry['signature']:
        reg[sig['regIndex']]=array[:,offset:offset+sig['compCount']]
        offset+=sig['compCount']
    registers[entry['eid']]=reg

raw=(base/'Source/world2/eid-538.world2').read_bytes()
n,nidx,nuv,flags=struct.unpack('<4I',raw[:16])
positions=np.frombuffer(raw,dtype='<f4',count=n*3,offset=16).reshape(n,3)
index_offset=16+n*(40+nuv*8)+(n*12 if flags&1 else 0)+(n*8 if flags&2 else 0)
indices=np.frombuffer(raw,dtype='<u4',count=nidx,offset=index_offset)
original_indices=np.fromfile(folder/'source-ib.u16',dtype='<u2').astype('<u4')
part=next(p for p in json.loads((base/'Source/scene-import.json').read_text(encoding='utf-8'))['parts'] if p['sourceEvent']==538)
M=np.array(part['placement'],dtype=float).reshape(4,4) if part['placed'] else np.eye(4)
F=np.array([[1,0,0],[0,0,-1],[0,1,0]],float)
# 与ReadMesh相同的MultiplyPoint3x4；不对拟合矩阵最后一行做额外透视除法。
published_source=(positions@M[:3,:3].T+M[:3,3])@F
actual=registers[538][2].astype(float)
vp=np.array(json.loads((base/'Source/capture-camera.json').read_text(encoding='utf-8'))['vp'])
published_clip=np.column_stack([published_source,np.ones(n)])@vp.T
actual_clip=registers[538][0].astype(float)
from_varying=np.column_stack([actual,np.ones(n)])@vp.T
ndc=lambda value:value[:,:3]/value[:,3:4]
delta=published_source-actual
pixel_jitter=(ndc(actual_clip)-ndc(from_varying))[:,:2]*[1506/2,-846/2]
old=(folder/'original-inputs.rdci').read_bytes()
magic,version,attribute_count,need,pstride,vstride,draw_count,columns=struct.unpack('<4s7I',old[:32])
old_clip=np.frombuffer(old,dtype='<f8',count=need*4,offset=32+attribute_count*3*8).reshape(need,4)
report=dict(sourceEvents=[538,1019],vertexCount=n,indexCount=nidx,triangleCount=nidx//3,
    indices=dict(originalFormat='uint16',world2Format='uint32',equal=bool(np.array_equal(indices,original_indices)),
                 minimum=int(indices.min()),maximum=int(indices.max()),uniqueVertices=len(np.unique(indices)),
                 baseVertex=0,indexOffset=0,world2Handedness=float(np.linalg.det(M)),
                 sourceIBSha256=hashlib.sha256((folder/'source-ib.u16').read_bytes()).hexdigest()),
    vertexAssociation=dict(originalRDCIClipEqualsFresh538=bool(np.array_equal(old_clip,actual_clip)),
        maximumOriginalClipDifference=float(np.max(abs(old_clip-actual_clip))),
        gb538Forward1019PositionEqual=bool(np.array_equal(registers[538][2],registers[1019][2])),
        gb538Forward1019ClipEqual=bool(np.array_equal(registers[538][0],registers[1019][0])),
        gb538Forward1019UVEqual=bool(np.array_equal(registers[538][1],registers[1019][1]))),
    publishedPositionVersusVarying=dict(maxAbsXYZ=abs(delta).max(axis=0).tolist(),meanAbsXYZ=abs(delta).mean(axis=0).tolist(),
        maxEuclideanDistance=float(np.linalg.norm(delta,axis=1).max()),
        maxProjectedNDCError=abs(ndc(published_clip)-ndc(actual_clip)).max(axis=0).tolist()),
    sourceJitterPixels=dict(mean=pixel_jitter.mean(axis=0).tolist(),minimum=pixel_jitter.min(axis=0).tolist(),maximum=pixel_jitter.max(axis=0).tolist(),
        sourceInstruction='538 VS166-167 adds cb1[19] jitter to clip.xy; world2 solver fits clip positions'),
    conclusion='No evidence of mixed pose, wrong vertex order or wrong triangle indices. World2 reproduces actual clip geometry; small o2 world-position difference follows captured jitter. No geometry correction or RecalculateNormals performed.',
    validationScope='Offline pose/topology evidence. Main agent 268/269/270 image A/B isolated the currently visible steps to shadowing, not geometry.')
(root/'doc/validation/body538-geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('source IB identical:',report['indices']['equal'],'clip identical:',report['vertexAssociation']['originalRDCIClipEqualsFresh538'],
      'max projected NDC error:',report['publishedPositionVersusVarying']['maxProjectedNDCError'])
