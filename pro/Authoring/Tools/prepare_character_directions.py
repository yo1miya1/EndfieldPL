"""按真实PostVS导出已pose模型方向；保留逐顶点顺序，不在运行时固定观察方向。"""
from pathlib import Path
import hashlib,json,struct
import numpy as np

root=Path(__file__).resolve().parents[3]
base=root/'pro/Authoring/Extracted/SI1'
native=base/'CharacterDirections/Native/postvs'
out=base/'CharacterDirections'
metadata=json.loads((native/'metadata.json').read_text(encoding='utf-8'))
registers={}
for m in metadata:
    values=np.fromfile(native/f'eid-{m["eid"]}.bin',dtype='<f4',offset=m['byteOffset']).reshape(-1,m['stride']//4)
    reg={};offset=0
    for signature in m['signature']:
        count=signature['compCount'];index=signature['regIndex']
        block=values[:,offset:offset+count];offset+=count
        reg[index]=np.concatenate([reg[index],block],axis=1) if index in reg else block
    registers[m['eid']]=reg

scene=json.loads((base/'Source/scene.rdc2scene').read_text(encoding='utf-8'))
parts={p['eid']:p for p in scene['parts']}
B=np.array([[-1,0,0],[0,0,1],[0,1,0]],float)
C=np.diag([-1,1,-1]) # B*F: source D3D world -> Unity world
rows=[];comparisons=[]
for eid in [488,502,520,538,553,568,585,599,617,655]:
    path=base/f'Source/world2/eid-{eid}.world2';raw=path.read_bytes()
    n,nidx,nuv,flags=struct.unpack('<4I',raw[:16])
    uv=np.frombuffer(raw,dtype='<f4',count=n*2,offset=16+n*40).reshape(n,2)
    old_n=np.frombuffer(raw,dtype='<f4',count=n*3,offset=16+n*12).reshape(n,3)
    old_t=np.frombuffer(raw,dtype='<f4',count=n*4,offset=16+n*24).reshape(n,4)
    source=parts[eid];M=np.array(source['matrix_scene']) if source['placed'] else np.eye(4)
    # 与SceneBuilder.ReadMesh同链：normal inverse-transpose、tangent placement、最后BlenderToUnity。
    old_n_unity=old_n@np.linalg.inv(M)[:3,:3]@B.T
    old_t_unity=old_t[:,:3]@M[:3,:3].T@B.T
    old_n_unity/=np.linalg.norm(old_n_unity,axis=1,keepdims=True)
    old_t_unity/=np.linalg.norm(old_t_unity,axis=1,keepdims=True)
    old_w=old_t[:,3]*(-1 if np.linalg.det(M)<0 else 1)
    post_event=1061 if eid==502 else eid
    reg=registers[post_event]
    if len(reg[0])!=n or not np.array_equal(reg[1][:,:2],uv):raise ValueError('Vertex/UV mismatch '+str(eid))
    normal=reg[2] if eid==655 else reg[3]
    if eid==488:
        # FaceDetail源VS只输出N，不输出T，且该材质无T依赖；保留原导入T，明确不冒称为源PostVS T。
        tangent=np.column_stack([old_t_unity@C,old_w]).astype('<f4')
        tangent_source='existing world2 tangent transformed by the importer chain; source FaceDetail VS has no tangent varying and current material does not consume it'
    else:
        tangent=reg[3] if eid==655 else reg[4]
        tangent_source='actual PostVS o3 float4' if eid==655 else 'actual PostVS o4 float4'
    values=np.column_stack([normal,tangent]).astype('<f4')
    if values.shape!=(n,7) or not np.isfinite(values).all():raise ValueError(str(eid))
    folder=out/str(eid);folder.mkdir(exist_ok=True)
    destination=folder/'normal-tangent.float7';destination.write_bytes(values.tobytes())
    normal_unity=normal@C;tangent_unity=tangent[:,:3]@C
    error_n=abs(old_n_unity-normal_unity);error_t=abs(old_t_unity-tangent_unity)
    comparison=dict(sourceEvent=eid,postVSEvent=post_event,vertexCount=n,
        normalMeanAbsError=float(error_n.mean()),normalMaxAbsError=float(error_n.max()),
        tangentMeanAbsError=float(error_t.mean()),tangentMaxAbsError=float(error_t.max()),
        tangentWChangedVertices=int(np.count_nonzero(old_w!=tangent[:,3])),
        sourceNormalLengthRange=[float(np.linalg.norm(normal,axis=1).min()),float(np.linalg.norm(normal,axis=1).max())],
        sourceTangentLengthRange=[float(np.linalg.norm(tangent[:,:3],axis=1).min()),float(np.linalg.norm(tangent[:,:3],axis=1).max())],
        sourceMaximumAbsNdotT=float(np.max(abs((normal*tangent[:,:3]).sum(axis=1)))))
    row=dict(sourceEvent=eid,postVSEvent=post_event,vertexCount=n,normalTangentPath=destination.relative_to(base).as_posix(),
             format='little-endian float32 [vertex][Nx,Ny,Nz,Tx,Ty,Tz,Tw]',space='source D3D world directions; already posed',
             importTransform='(-x,y,-z) for xyz; preserve Tw; do not apply placement again',
             vertexPairing='same vertex count and all UV0 components bit-exact with world2',
             normalSource='actual PostVS o2.xyz' if eid==655 else 'actual PostVS o3.xyz',tangentSource=tangent_source,
             sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    (folder/'import.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
    rows.append(row);comparisons.append(comparison)
manifest=dict(parts=rows,excluded=[dict(sourceEvent=1190,reason='unlit environment-effect VS has no geometric N/T varying; color/motion registers must not be misread as directions')])
(out/'import.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(root/'doc/capture/character-directions-validation.json').write_text(json.dumps(dict(importerChain='placement inverse-transpose for normal, placement for tangent, then B(-x,z,y); source expected C(-x,y,-z)',comparisons=comparisons),indent=2),encoding='utf-8')
print('Published',len(rows),'pose direction streams; 1190 correctly excluded as unlit')
