import pathlib,json,numpy as np,struct,hashlib,shutil
root=pathlib.Path(__file__).resolve().parents[3];base=root/'pro/Authoring/Extracted/SI1';native=base/'EffectsNative';read=base/'EffectsRead';out=base/'Effects';out.mkdir(exist_ok=True)
cam=json.loads((base/'Source/capture-camera.json').read_text());inv=np.linalg.inv(np.array(cam['vp']));frame=np.array(cam['frame']);rows=[]
sourceEvents=[1554,1571,1589,1607,1625,1649,1672,1693,1712,1730]
metadata={x['eid']:x for x in json.loads((native/'postvs/metadata.json').read_text())}
for eid in sourceEvents:
 d=json.loads((read/'raw/mat'/f'eid-{eid}/draw.json').read_text());meta=metadata[eid];f=out/str(eid);f.mkdir(exist_ok=True)
 post=np.fromfile(native/'postvs'/f'eid-{eid}.bin',dtype='<f4',offset=meta['byteOffset']).reshape(-1,meta['stride']//4)
 inp=(read/'raw/mat'/f'eid-{eid}/inputs.bin').read_bytes();h=struct.unpack('<4s7I',inp[:32]);idx=np.frombuffer(inp,dtype='<u4',count=h[6],offset=len(inp)-h[6]*4);used,remap=np.unique(idx,return_inverse=True);idx=remap.astype('<u4');post=post[used]
 registers=np.zeros((len(post),10,4),dtype='<f4');offset=0
 for s in meta['signature']:
  n=s['compCount'];registers[:,s['regIndex'],:n]=post[:,offset:offset+n];offset+=n
 clip=registers[:,0].astype(float);p=clip@inv.T;p=p[:,:3]/p[:,3:4];p=p@frame.T
 # 法线用于Unity几何元数据；原PS输入仍完整保留在寄存器辅助流，绝不冒充此几何法线为源VS normal。
 normal=np.zeros_like(p)
 for a,b,c in idx.reshape(-1,3):
  v=np.cross(p[b]-p[a],p[c]-p[a]);normal[a]+=v;normal[b]+=v;normal[c]+=v
 norm=np.linalg.norm(normal,axis=1);normal/=np.where(norm[:,None]>0,norm[:,None],1)
 tangent=np.tile([1,0,0,1],(len(p),1));uv=[registers[:,1,:2],registers[:,1,2:],registers[:,2,:2],registers[:,2,2:]]
 if eid in [1649,1693]:
  # 受光衣料使用真实VS o3世界法线与o4切线；F为proper rotation，切线w不翻转。
  normal=registers[:,3,:3]@frame.T
  if eid==1649:tangent=np.column_stack([registers[:,4,:3]@frame.T,registers[:,4,3]])
 mesh=f/f'eid-{eid}.world2';mesh.write_bytes(struct.pack('<4I',len(p),len(idx),4,0)+b''.join(x.astype('<f4').tobytes() for x in [p,normal,tangent,*uv])+idx.tobytes())
 (f/'postvs-registers.bin').write_bytes(registers.tobytes());(f/'source-vertex-indices.bin').write_bytes(used.astype('<u4').tobytes())
 if eid==1649:
  # 此draw是有法线的受光几何，源VS没有COLOR输入；白色为未消费颜色通道的中性值。
  colors=np.ones((len(post),4),dtype='<f4');colorSource='no source COLOR varying; neutral unused stream (different lit family, not InkEffect)'
 else:
  colors=registers[:,5].astype('<f4');colorSource='actual VS o5 float4 (shared source VS bd401bd48f); no quantization'
 (f/'vertex-colors.float4').write_bytes(colors.tobytes())
 textureRecords=[]
 for t in d['textures']:
  if t['stage']!='ps':continue
  files=t.get('files') or []
  if not files:continue
  rid=int(t['resource'].split('::')[-1]);metaTex=next((x for x in json.loads((native/'texture-metadata.json').read_text()) if x['resourceId']==rid),{})
  if 'RenderTarget' in metaTex.get('creationFlags','') or 'DepthTarget' in metaTex.get('creationFlags',''):continue
  ptex=out/'textures'/f'{rid}.png';ptex.parent.mkdir(exist_ok=True)
  if not ptex.exists():shutil.copy2(read/pathlib.Path(files[0].replace('\\','/')),ptex)
  textureRecords.append({'slot':t['bind_point'],'resourceId':rid,'path':ptex.relative_to(base).as_posix(),'format':metaTex.get('format')})
 rows.append({'eid':eid,'meshPath':mesh.relative_to(base).as_posix(),'n':len(p),'nidx':len(idx),'nuv':4,'flags':0,'baked':True,'placed':False,'vertexColorPath':(f/'vertex-colors.float4').relative_to(base).as_posix(),'vertexColorSource':colorSource,'registersPath':(f/'postvs-registers.bin').relative_to(base).as_posix(),'registerCount':10,'registerLayout':'float32 [vertex][register0..9][xyzw], unused channels zero; register0 source clip; source signature below','signature':meta['signature'],'normalSource':'actual PostVS o3 world normal, F rotation' if eid in [1649,1693] else 'geometric face average, shader source varyings separately preserved','tangentSource':'actual PostVS o4 world tangent xyz and original w, F rotation' if eid==1649 else 'unused neutral geometry tangent','uvLayout':['source o1.xy','source o1.zw','source o2.xy','source o2.zw'],'sourceDraw':(read/'raw/mat'/f'eid-{eid}/draw.json').relative_to(base).as_posix(),'textures':textureRecords})
(out/'import.json').write_text(json.dumps({'origin':[-0.05014241172612291,3.4987388362881324,-0.9738223233136223],'coordinateFrame':'same Blender scene frame as Source/world2; apply common source-origin shift and BlenderToUnity once','sourceEvents':sourceEvents,'draws':rows},indent=2))
print('Published',len(rows),'posed FX meshes and complete source PS varying registers')
