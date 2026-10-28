"""按已复现侧胸相机ROI量化几何面法线与源着色法线；不改模型或shader。"""
from pathlib import Path
import json,struct,numpy as np

root=Path(__file__).resolve().parents[3]
base=root/'pro/Authoring/Extracted/SI1'
raw=(base/'Source/world2/eid-538.world2').read_bytes()
n,nidx,nuv,flags=struct.unpack('<4I',raw[:16])
position=np.frombuffer(raw,dtype='<f4',count=n*3,offset=16).reshape(n,3)
offset=16+n*(40+nuv*8)+(n*12 if flags&1 else 0)+(n*8 if flags&2 else 0)
indices=np.frombuffer(raw,dtype='<u4',count=nidx,offset=offset).reshape(-1,3)
plan=json.loads((base/'Source/scene-import.json').read_text(encoding='utf-8'))
part=next(p for p in plan['parts'] if p['sourceEvent']==538)
matrix=np.array(part['placement']).reshape(4,4)
B=np.array([[-1,0,0],[0,0,1],[0,1,0]],float)
position=(position@matrix[:3,:3].T+matrix[:3,3])@B.T-B@np.array(plan['origin'])
direction=np.fromfile(base/part['normalTangentPath'],dtype='<f4').reshape(n,7)
normal=direction[:,:3]@np.diag([-1,1,-1]);normal/=np.linalg.norm(normal,axis=1,keepdims=True)
evidence=json.loads((base/'GeometryValidation/538/side-chest-camera.json').read_text(encoding='utf-8'))
V=np.array([[evidence['view'][f'e{i}{j}'] for j in range(4)] for i in range(4)])
P=np.array([[evidence['projection'][f'e{i}{j}'] for j in range(4)] for i in range(4)])
clip=np.column_stack([position,np.ones(n)])@(P@V).T
pixels=(clip[:,:2]/clip[:,3:4]*[.5,-.5]+.5)*[1200,900]
centroid=position[indices].mean(axis=1)
geometric=np.cross(position[indices[:,1]]-position[indices[:,0]],position[indices[:,2]]-position[indices[:,0]])
area=np.linalg.norm(geometric,axis=1)
geometric/=np.maximum(area[:,None],1e-15)
mean_normal=normal[indices].mean(axis=1)
mean_normal/=np.maximum(np.linalg.norm(mean_normal,axis=1,keepdims=True),1e-15)
dot=np.sum(geometric*mean_normal,axis=1)
screen_center=pixels[indices].mean(axis=1)
roi=(screen_center[:,0]>350)&(screen_center[:,0]<800)&(screen_center[:,1]>380)&(screen_center[:,1]<800)&(clip[indices,3].min(axis=1)>0)&(area>1e-10)
camera=np.array([evidence['cameraPosition'][a] for a in ['x','y','z']])
facing=np.sum(geometric*(camera-centroid),axis=1)>0
light=np.array(json.loads((base/'Source/semantic-scene-settings.json').read_text(encoding='utf-8'))['directionTowardLight'])*[-1,1,-1]
percentiles=lambda values:np.percentile(values,[0,10,50,90,100]).tolist()
regions={}
for name,selected in [('wholeMesh',area>1e-10),('sideChestROIBothSides',roi),('sideChestROIFrontFacing',roi&facing)]:
    corner_dot=np.sum(normal[indices[selected]]*geometric[selected,None,:],axis=2)
    regions[name]=dict(triangles=int(selected.sum()),faceMeanNormalDotPercentiles=percentiles(dot[selected]),
        faceMeanNormalAngleDegreesPercentiles=percentiles(np.rad2deg(np.arccos(np.clip(dot[selected],-1,1)))),
        cornerNormalAngleDegreesPercentiles=percentiles(np.rad2deg(np.arccos(np.clip(corner_dot,-1,1)))),
        reversedMeanNormalFraction=float(np.mean(dot[selected]<0)),geometricNdotLightPercentiles=percentiles(geometric[selected]@light))
vertices=np.unique(indices[roi&facing])
factor=1-np.clip(normal[vertices]@light,0,1)
report=dict(cameraEvidence='GeometryValidation/538/side-chest-camera.json',sourceGeometry=538,
    roiPixels=[350,380,800,800],roiCaveat='Projected triangle-centroid selection; front-facing subset uses geometric N toward camera. Other meshes and exact raster occlusion are not reconstructed.',
    percentilesOrder=[0,10,50,90,100],regions=regions,frontFacingROIVertices=len(vertices),normalBiasFactorPercentiles=percentiles(factor),
    tangentWInCasterPosition=False,
    sourceShadow372=dict(normalComputed=True,normalUsedForPosition=False,cull='Off',depthBias=-8,slopeScaledDepthBias=0,
        shader='ShadowReceiverNative/programs/372-Vertex.hlsl',positionPath='posed position + origin, then cb2 shadow matrix; N only exported to o2',
        noGeometryHullDomainStage=True),
    conclusion='Side-chest N follows geometric winding with ordinary smooth-normal deviation, not gross inversion. Most selected visible faces are backlit/near the terminator and receive maximum normal offset in the current URP-style caster. Source372 does not apply a shader vertex-normal bias. Do not recalculate source normals or flip Tw to hide shadow artifacts.')
(root/'doc/validation/body538-shadow-normals.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Front ROI faces',regions['sideChestROIFrontFacing']['triangles'],'dot percentiles',regions['sideChestROIFrontFacing']['faceMeanNormalDotPercentiles'])
