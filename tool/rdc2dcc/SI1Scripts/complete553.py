import pathlib,numpy as np,struct,json,shutil
root=pathlib.Path('F:/Project/_Game/EndfieldRebuild')
raw=root/'tmp/capture/fix553/read/raw/eid-553'
post=np.fromfile(raw/'postvs.bin',dtype='<f4').reshape(-1,23)
# Actual VS signature: SV_POSITION4, TEXCOORD0.xy, worldPosition3,
# normal3, tangent4, currentClip3, previousClip3, instanceId1.
frame=np.array([[1,0,0],[0,0,-1],[0,1,0]],dtype=np.float32)
pos=post[:,6:9]@frame.T
normal=post[:,9:12]@frame.T
tangent=np.column_stack([post[:,12:15]@frame.T,post[:,15]])
uv=post[:,4:6]
idx=np.fromfile(raw/'ib.bin',dtype='<u2').astype('<u4')
work=root/'tmp/capture/fix553';(work/'world2').mkdir(exist_ok=True)
out=work/'world2/eid-553.world2'
out.write_bytes(struct.pack('<4I',len(post),len(idx),1,0)+b''.join(x.astype('<f4').tobytes() for x in [pos,normal,tangent,uv])+idx.tobytes())
entry={'path':'eid-553.world2','n':len(post),'nidx':len(idx),'nuv':1,'flags':0,'rms':0,'mode':'postvs-full-attributes','kind':'skinned','baked':True,'screen_space':False,'uv':1}
(work/'world2/manifest.json').write_text(json.dumps({'553':entry}))
dest=root/'pro/Assets/Endfield/Content/SI1/Source'
shutil.copy2(out,dest/'world2/eid-553.world2')
manifest=json.loads((dest/'world2/manifest.json').read_text());manifest['553']=entry;(dest/'world2/manifest.json').write_text(json.dumps(manifest,indent=2))
scene=json.loads((dest/'scene.rdc2scene').read_text());scene['parts']=[p for p in scene['parts'] if p['eid']!=553];scene['parts'].append({'eid':553,'kind':'skinned','geometry':'fbx/eid-553.fbx','n':len(post),'nidx':len(idx),'nuv':1,'mode':entry['mode'],'rms':0,'screen_space':False,'placed':False,'matrix_scene':np.eye(4).tolist()});scene['parts'].sort(key=lambda x:x['eid']);(dest/'scene.rdc2scene').write_text(json.dumps(scene,indent=2))
print('Recovered full PostVS attributes:',len(post),'vertices;',len(idx)//3,'triangles')
