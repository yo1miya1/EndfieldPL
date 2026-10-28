import pathlib,json,re,struct,shutil,hashlib,numpy as np
root=pathlib.Path('F:/Project/_Game/EndfieldRebuild');base=root/'pro/Authoring/Extracted/SI1';src=base/'UIRead';native=base/'UINative';out=base/'UIPrepared';out.mkdir(exist_ok=True)
runtime=root/'pro/Assets/Endfield/Shaders/UI';runtime.mkdir(parents=True,exist_ok=True)
post={d['eid']:d for d in json.loads((native/'postvs/metadata.json').read_text())}
meta={d['resourceId']:d for d in json.loads((native/'texture-metadata.json').read_text())}
draws=[json.loads(p.read_text()) for p in sorted((src/'raw/mat').glob('eid-*/draw.json'),key=lambda p:int(p.parent.name[4:])) if int(p.parent.name[4:]) not in [2148,2906]]
families={}; results=[];textures={}
blendmap={0:0,1:1,2:3,3:6,4:2,5:4,6:5,7:10,8:7,9:8,10:9};comparemap={0:1,1:8,2:2,3:4,4:5,5:7,6:3,7:6};stencilmap={0:0,1:1,2:2,3:3,4:4,5:6,6:7,7:5}
rolemap={'76d926':'DepthClippedLayeredSprite','2aa0ee':'DepthClippedDistanceFieldText','0a3e75':'ScreenMaskedSprite','e79d7b':'ScreenDistanceFieldText','1bf0c6':'ScreenOutlineText','0dae3c':'ScreenDecoratedText','791c2f':'ScreenLayeredSprite'}
for d in draws:
 e=d['eid'];p=post[e];folder=out/str(e);folder.mkdir(exist_ok=True)
 arr=np.fromfile(native/'postvs'/f'eid-{e}.bin',dtype='<f4',offset=p['byteOffset']).reshape(-1,p['stride']//4)
 count=d['mesh']['need'];arr=arr[:count]; packed=np.zeros((count,10,4),dtype='<f4');offset=0
 for s in p['signature']:
  n=s['compCount'];reg=s['regIndex'];packed[:,reg,:n]=arr[:,offset:offset+n];offset+=n
 assert offset*4==p['stride']
 packed[:,0,1]*=(-1 if e<2906 else 1)
 (folder/'vertices.bin').write_bytes(packed.tobytes())
 inp=(src/'raw/mat'/f'eid-{e}'/'inputs.bin').read_bytes();h=struct.unpack('<4s7I',inp[:32]);nidx=h[6];idx=np.frombuffer(inp,dtype='<u4',count=nidx,offset=len(inp)-nidx*4);(folder/'indices.bin').write_bytes(idx.tobytes())
 state=json.loads((native/'graphics'/f'eid-{e}.json').read_text());om=state['outputMerger'];rast=state['rasterizer'];ds=om['depthStencilState'];blend=om['blendState']['blends'][0];front=ds['frontFace'];back=ds['backFace'];sc=rast['scissors'][0]
 fixed={'srcBlend':blendmap[blend['colorBlend']['source']] if blend['enabled'] else 1,'dstBlend':blendmap[blend['colorBlend']['destination']] if blend['enabled'] else 0,'srcBlendAlpha':blendmap[blend['alphaBlend']['source']] if blend['enabled'] else 1,'dstBlendAlpha':blendmap[blend['alphaBlend']['destination']] if blend['enabled'] else 0,'blendOp':blend['colorBlend']['operation'],'blendOpAlpha':blend['alphaBlend']['operation'],'colorMask':sum((1<<(3-i)) for i in range(4) if blend['writeMask']&(1<<i)),'zTest':comparemap[ds['depthFunction']] if ds['depthEnable'] else 8,'zWrite':int(ds['depthWrites'] and ds['depthEnable']),'stencilRef':front['reference'],'stencilReadMask':front['compareMask'],'stencilWriteMask':front['writeMask'] if ds['stencilEnable'] else 0}
 for face,nm in [(front,'Front'),(back,'Back')]:
  fixed['stencilComp'+nm]=comparemap[face['function']] if ds['stencilEnable'] else 8
  for k,k2 in [('Pass','passOperation'),('Fail','failOperation'),('ZFail','depthFailOperation')]:fixed['stencil'+k+nm]=stencilmap[face[k2]] if ds['stencilEnable'] else 0
 shaderkey=d['shaders']['ps']['sha1'];role=next(v for k,v in rolemap.items() if shaderkey.startswith(k));bindings=json.loads((native/'bindings'/f'eid-{e}.json').read_text())['stages']['ShaderStage.Pixel'];samplers={int(x['access']['index']):x['sampler'] for x in bindings['samplers']};keywords=[]
 for slot,s in samplers.items():
  if s['addressU']==2:keywords.append('UI_S%d_CLAMP'%slot)
  if s['filter']['minify']==1:keywords.append('UI_S%d_POINT'%slot)
 constants=[];decodedConstants={}
 psText=(base/'UIPrograms'/(shaderkey+'.hlsl')).read_text()
 declared={int(a):int(b) for a,b in re.findall(r'float4 cb(\d+)\[(\d+)\]',psText)}
 for cb in d['cbuffers']:
  if cb['stage']!='ps':continue
  countVectors=declared[cb['slot']]
  data=(src/pathlib.Path(cb['file'].replace('\\','/'))).read_bytes()[:countVectors*16]
  values=np.frombuffer(data,dtype='<f4').tolist();decodedConstants[cb['slot']]=values
  rel='constants/'+hashlib.sha256(data).hexdigest()+'.bin';(out/'constants').mkdir(exist_ok=True);(out/rel).write_bytes(data)
  constants.append({'name':'_UIParameters'+str(cb['slot']),'path':rel,'count':countVectors})
 tex=[]
 for t in d['textures']:
  if t['stage']!='ps':continue
  rid=int(t['resource'].split('::')[-1]);m=meta.get(rid,{});dynamic=('RenderTarget' in m.get('creationFlags','') or 'DepthTarget' in m.get('creationFlags','') or '2D Render Target' in m.get('name','') or '2D Depth Target' in m.get('name',''))
  # Creation flags, not the legacy is_target heuristic, decide reusable atlas data.
  if dynamic:
   tex.append({'slot':t['bind_point'],'resourceId':rid,'dynamic':'depth' if rid==20361 else 'scene','path':''});continue
  files=t.get('files') or []
  if not files:continue
  srcfile=src/pathlib.Path(files[0].replace('\\','/'));dest=out/'textures'/f'{rid}.png';dest.parent.mkdir(exist_ok=True)
  if not dest.exists():shutil.copy2(srcfile,dest)
  textures[rid]={'resourceId':rid,'path':dest.relative_to(out).as_posix(),'linear':'SRGB' not in m.get('format','')}
  tex.append({'slot':t['bind_point'],'resourceId':rid,'dynamic':'','path':textures[rid]['path']})
 families[role]={'key':shaderkey,'representativeEid':e,'textures':tex,'samplers':sorted(samplers)}
 results.append({'eid':e,'family':role,'vertexPath':(folder/'vertices.bin').relative_to(out).as_posix(),'indexPath':(folder/'indices.bin').relative_to(out).as_posix(),'vertexCount':count,'indexCount':nidx,'constants':constants,'textures':tex,'keywords':keywords,'fixedState':fixed,'scissorEnabled':rast['state']['scissorEnable'],'scissor':[sc['x'],sc['y'],sc['width'],sc['height']]})
 sourceSlot=2 if role=='DepthClippedLayeredSprite' else 1
 sourceRow=11 if 'Sprite' in role else 7
 results[-1]['alphaReduction']=decodedConstants[sourceSlot][sourceRow*4]
for role,f in families.items():
 text=(base/'UIPrograms'/(f['key']+'.hlsl')).read_text()
 text=re.sub(r'cbuffer cb(\d+)\s*:\s*register\(b\d+\)\s*\{\s*float4 cb\d+\[(\d+)\];\s*\}',lambda m:'float4 _UIParameters%s[%s];'%(m[1],m[2]),text)
 text=re.sub(r'\bcb(\d+)\b',r'_UIParameters\1',text)
 text=re.sub(r'(_UIParameters\d+\[\d+\]\.x)(\s*\*\s*-r0\.w\s*\+\s*r0\.w)',r'_AlphaReduction\2',text)
 text='float _AlphaReduction;\n'+text
 text=re.sub(r'Texture2D<float4> t(\d+) : register\(t\d+\);',lambda m:'Texture2D<float4> _UITexture%s;'%m[1],text)
 text=re.sub(r'\bt(\d+)\b',r'_UITexture\1',text)
 text=re.sub(r'SamplerState s(\d+)_s : register\(s\d+\);','',text)
 text=re.sub(r'\bs(\d+)_s\b',r'_UISampler\1',text)
 for t in f['textures']:
  if t['dynamic']=='depth':text=re.sub(r'\b_UITexture'+str(t['slot'])+r'\b','_CameraDepthTexture',text)
 sam='SamplerState sampler_UI_linear_repeat;\nSamplerState sampler_UI_linear_clamp;\nSamplerState sampler_UI_point_repeat;\nSamplerState sampler_UI_point_clamp;\n'
 pragmas=[]
 for slot in f['samplers']:
  subset=[d for d in results if d['family']==role]
  clampValues={('UI_S%d_CLAMP'%slot) in d['keywords'] for d in subset}
  pointValues={('UI_S%d_POINT'%slot) in d['keywords'] for d in subset}
  if len(clampValues)>1:pragmas.append('#pragma multi_compile_local __ UI_S%d_CLAMP'%slot)
  elif True in clampValues:sam+='#define UI_S%d_CLAMP\n'%slot
  if len(pointValues)>1:pragmas.append('#pragma multi_compile_local __ UI_S%d_POINT'%slot)
  elif True in pointValues:sam+='#define UI_S%d_POINT\n'%slot
  sam+=f'''#if defined(UI_S{slot}_POINT)
 #if defined(UI_S{slot}_CLAMP)
  #define _UISampler{slot} sampler_UI_point_clamp
 #else
  #define _UISampler{slot} sampler_UI_point_repeat
 #endif
#else
 #if defined(UI_S{slot}_CLAMP)
  #define _UISampler{slot} sampler_UI_linear_clamp
 #else
  #define _UISampler{slot} sampler_UI_linear_repeat
 #endif
#endif
'''
 # SV_Position was folded into clip geometry only. All remaining varyings are actual source VS results.
 params=re.search(r'void main\s*\((.*?)\)\s*\{',text,re.S)[1]
 inputs=re.findall(r'(?<!out )float([1-4]?)\s+(v\d+)\s*:\s*([^,\n]+)',params)
 arguments=[]
 for dim,var,sem in inputs:arguments.append('i.position' if sem.lower().startswith('sv_position') else 'i.o'+str(int(var[1:]))+('.'+'xyzw'[:int(dim)] if dim and int(dim)<4 else ''))
 text=re.sub(r'void main\s*\(.*?\)\s*\{','void SourceUI('+','.join('float%s %s'%(dim,var) for dim,var,_ in inputs)+',out float4 o0) {',text,count=1,flags=re.S)
 wrapper='struct UIInput { float4 clip:POSITION; float4 o1:COLOR; '+''.join(f'float4 o{k+2}:TEXCOORD{k};' for k in range(8))+' };\n'
 wrapper+='struct UIVaryings { float4 position:SV_POSITION;'+''.join(f'float4 o{k}:TEXCOORD{k-1};' for k in range(1,10))+' };\n'
 wrapper+='UIVaryings UIVertex(UIInput i) { UIVaryings o; o.position=float4(i.clip.x,-i.clip.y*_EndfieldOutputScaleBias.y,i.clip.zw);'+''.join(f'o.o{k}=i.o{k};' for k in range(1,10))+'return o;}\n'
 wrapper+='float4 UIFragment(UIVaryings i):SV_Target {float4 color=0; SourceUI('+','.join(arguments)+',color);return color;}\n'
 properties='_AlphaReduction("Alpha Reduction", Range(0,1))=0\n'+'\n'.join(f'[HideInInspector] _UITexture{k}("Source Texture {k}",2D)="white"{{}}' for k in range(5))
 properties+='\n'+'\n'.join('[HideInInspector] _'+k+'("'+k+'",Float)='+str(v) for k,v in results[0]['fixedState'].items())
 states='Cull Off\nZWrite [_zWrite]\nZTest [_zTest]\nBlend [_srcBlend] [_dstBlend], [_srcBlendAlpha] [_dstBlendAlpha]\nBlendOp [_blendOp], [_blendOpAlpha]\nColorMask [_colorMask]\nStencil { Ref [_stencilRef] ReadMask [_stencilReadMask] WriteMask [_stencilWriteMask] CompFront [_stencilCompFront] CompBack [_stencilCompBack] PassFront [_stencilPassFront] PassBack [_stencilPassBack] FailFront [_stencilFailFront] FailBack [_stencilFailBack] ZFailFront [_stencilZFailFront] ZFailBack [_stencilZFailBack] }'
 shader='Shader "Endfield/UI/'+role+'" { Properties {\n'+properties+'\n} SubShader { Tags { "RenderPipeline"="EndfieldPipeline" } Pass { '+states+'\nHLSLPROGRAM\n#pragma target 5.0\n#pragma vertex UIVertex\n#pragma fragment UIFragment\n'+'\n'.join(pragmas)+'\n'+sam+'\n'+text+'\n'+wrapper+'ENDHLSL\n} } }'
 (runtime/(role+'.shader')).write_text(shader)
(out/'manifest.json').write_text(json.dumps({'referenceWidth':2560,'referenceHeight':1440,'draws':results,'textures':list(textures.values()),'families':families},separators=(',',':')))
print('Prepared',len(results),'draws;',len(families),'families;',len(textures),'static textures')
