"""补源台面实际UV并发布可读材质值；只写离线Extracted数据。"""
from pathlib import Path
import json,struct,numpy as np
root=Path(__file__).resolve().parents[3]
base=root/'pro/Authoring/Extracted/SI1'
path=base/'Background/world2/eid-673.world2';data=path.read_bytes();n,nidx,nuv,flags=struct.unpack('<4I',data[:16])
probe=json.loads((base/'BackgroundRead/raw/probe.json').read_text(encoding='utf-8'))['data']['673']
stride=probe['postvs']['vstride']
post=np.fromfile(base/'BackgroundRead/raw/eid-673/postvs.bin',dtype='<f4').reshape(-1,stride//4)
uv=post[:n,4:6].astype('<f4')
path.write_bytes(struct.pack('<4I',n,nidx,1,flags)+data[16:16+n*40]+uv.tobytes()+data[16+n*40+n*nuv*8:])
# 源unlit VS没有使用normal，原导出为零；实时接收器必须从真实台面拓扑恢复几何法线。
data=path.read_bytes()
positions=np.frombuffer(data,dtype='<f4',count=n*3,offset=16).reshape(n,3)
indices=np.frombuffer(data,dtype='<u4',count=nidx,offset=16+n*48).reshape(-1,3)
normals=np.zeros((n,3),dtype=np.float64)
for a,b,c in indices:
    face=np.cross(positions[b]-positions[a],positions[c]-positions[a])
    normals[a]+=face;normals[b]+=face;normals[c]+=face
normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
path.write_bytes(data[:16+n*12]+normals.astype('<f4').tobytes()+data[16+n*24:])
manifest=json.loads((base/'Background/world2/manifest.json').read_text(encoding='utf-8'))
manifest['673'].update(nuv=1,uv=1)
(base/'Background/world2/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
material=json.loads((base/'Source/Constants/1210_ps_cb2.json').read_text(encoding='utf-8'))['variables']
values=[v['floatValues'] for v in material]
result=dict(sourceEvent=673,surfaceEvent=1210,shader='Endfield/SourceBackground',meshPath='Background/world2/eid-673.world2',
            world2=manifest['673'],placed=False,baked=True,origin=[-.05014241172612291,3.4987388362881324,-.9738223233136223],
            textures={'_BaseMap':'Textures/tex_24401.png','_PatternMap':'Textures/tex_25127.png'},
            vectors={'_BaseColor':values[3],'_PatternColor':values[4],'_PatternUV_ST':values[5],'_BaseUV_ST':values[6],'_DistanceFade':values[2]},
            floats={'_BaseGain':values[0][2],'_BaseCoverage':values[1][1],'_SourceMipBias':0,'_Cull':2,'_ReceiveShadows':1},
            uvSource='BackgroundRead/raw/eid-673/postvs.bin, actual output o1.xy',
            sourceBranches={'volumeFogEnabled':False,'heightFogDensities':[0,0],'transmittanceFloor':1},
            runtimeExtensions={'receiveRealtimeMainLightShadow':'Unity EFMainShadow sampled at the actual ground world position; source1210 is unlit composition',
                               'normalSource':'area-weighted real ground triangle geometry; original unused source normal stream was zero',
                               'shadowEnergyRatio':'(Unity SH ambient + main radiance*NdotL*shadow)/(ambient + main radiance*NdotL)'})
(base/'Background/import.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(base/'Background/import.json')
