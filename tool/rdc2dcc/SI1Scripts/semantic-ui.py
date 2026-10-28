import pathlib,json,re,numpy as np,struct,math
root=pathlib.Path('F:/Project/_Game/EndfieldRebuild');base=root/'pro/Authoring/Extracted/SI1/UIPrepared';doc=json.loads((base/'manifest.json').read_text());mappings={}
glyph={(0,0):('WaveTimeControl','波形时间输入，仅使用源y分量，时间单位未恢复'),(1,2):('WaveEnabled','x启用字形波动'),(1,4):('DirectionalFade','w控制方向性透明渐变'),(1,5):('WaveParameters','xyzw为振幅、频率、相位速度、幂次'),(1,6):('GlyphSamplingAndSoftness','x多点采样开关，y面平滑，z采样半径，w边缘平滑'),(1,7):('OpacityControl','x为源输出alpha减量'),(2,0):('FaceUVScroll','xy为面纹理UV的相位偏移系数'),(2,1):('FaceColor','字形面RGBA，源公式与顶点色及面纹理相乘'),(2,2):('OutlineSoftnessAndUVScroll','y轮廓柔度，zw轮廓纹理UV的相位偏移系数'),(2,3):('OutlineColor','字形轮廓RGBA'),(2,4):('OutlineWidth','x轮廓宽度，乘梯度尺度及顶点SDF尺度'),(2,20):('DistanceFieldScale','w为距离场梯度尺度'),(2,24):('FontAtlasDimensions','zw为字体图集宽高'),(2,25):('GlyphPadding','x用于约束波动UV偏移'),(3,45):('AnimationPhase','y作为面/轮廓纹理滚动相位，未假定真实时间单位'),(3,47):('ReferenceViewport','xy为源UI参考视口宽高'),(3,48):('DepthLinearization','zw把采样深度转换为倒数线性深度'),(4,6):('ClipRect','xy最小边界，zw最大边界'),(4,7):('ClipFadeWidths','x/y/z/w分别参与矩形四边smoothstep过渡')}
spriteExtra={11:('OpacityControl','x为输出alpha减量'),12:('TextureAlphaOverride','x非零时忽略图集alpha'),13:('PatternUVTransform','xy缩放zw偏移，进入源固定200倍纹样坐标'),14:('PatternControl','x纹样反差，y乘法亮度，z启用'),15:('GridColor','RGB网格色，a混合强度'),16:('GridControl','x开关，y重复频率，z单元阈值'),18:('LayerFeatures','x备用颜色层，y屏幕抖动，z/w抖动响应'),19:('LayerScreenAndDepth','xy源整数位模式尺寸，z预乘模式，w深度插值'),20:('DepthOffsetControl','x插值参考深度，yz裁剪深度偏移因子')}
for family in doc['families']:
 p=root/'pro/Assets/Endfield/Shaders/UI'/(family+'.shader');text=p.read_text()
 # 只删除捕获CB接口，源公式后面的所有行索引都由下面的明确语义表替换。
 text=re.sub(r'float4 _UIParameters\d+\[\d+\];','',text)
 used={}
 for a,b,swizzle in re.findall(r'_UIParameters(\d+)\[(\d+)\](?:\.([xyzw]+))?',text):
  key=(int(a),int(b));used.setdefault(key,set()).update(swizzle or 'xyzw')
 rows=[]; declarations=[];properties=[]
 for key,mask in sorted(used.items()):
  if 'Sprite' in family:
   materialSlot=2 if family=='DepthClippedLayeredSprite' else 1
   sampleSlot=1 if family=='DepthClippedLayeredSprite' else 0
   common={(0,48):('DepthLinearization','zw源倒数深度线性化'),(sampleSlot,5):('TextureSampleAdd','采样RGBA相加项'),(sampleSlot,6):('ClipRect','xy最小边界，zw最大边界'),(sampleSlot,7):('ClipFadeWidths','四边平滑宽度')}
   info=spriteExtra[key[1]] if key[0]==materialSlot else common[key]
  else:info=glyph[key]
  name='_'+info[0]
  text=text.replace('_UIParameters%d[%d]'%key,name)
  declarations.append('float4 '+name+'; // '+info[1])
  kind='Color' if info[0] in ['FaceColor','OutlineColor','GridColor'] else 'Vector'
  properties.append(name+'("'+info[0]+'",'+kind+')=(0,0,0,0)')
  rows.append({'sourceSlot':key[0],'sourceRow':key[1],'property':name,'usedComponents':''.join(c for c in 'xyzw' if c in mask),'meaning':info[1],'confidence':'direct-instruction-use; physical/editor names inferred'})
 # 源以asint读取尺寸；公开材质属性采用可读整数尺寸，保持源计算结果。
 if '_LayerScreenAndDepth' in text:
  text=text.replace('asint(_LayerScreenAndDepth.xy)','_DitherResolution.xy')
  declarations.append('float4 _DitherResolution; // 原cb尺寸位模式解码为可读像素数')
  properties.append('_DitherResolution("Dither Resolution",Vector)=(2560,1440,0,0)')
 text=text.replace('float _AlphaReduction;','float _AlphaReduction;\n'+'\n'.join(declarations))
 text=text.replace('Properties {','Properties {\n'+'\n'.join(properties),1)
 text=text.replace('float _AlphaReduction;', 'float4 _EndfieldOutputScaleBias;\nfloat _AlphaReduction;')
 text='// 本UI家族保持源片元算法，捕获页已拆为可编辑的用途参数。\n// 几何携带真实源VS输出，材质不再绑定捕获CB数组或EID。\n'+text
 p.write_text(text)
 mappings[family]=rows
for draw in doc['draws']:
 pages={int(p['name'].split('Parameters')[-1]):np.fromfile(base/p['path'],dtype='<f4').reshape(-1,4) for p in draw['constants']}
 parameters=[]
 for row in mappings[draw['family']]:
  value=pages[row['sourceSlot']][row['sourceRow']].copy();mask=row['usedComponents']
  for c in 'xyzw':
   if c not in mask:value['xyzw'.index(c)]=0
  if row['property']=='_LayerScreenAndDepth':
   dims=pages[row['sourceSlot']][row['sourceRow']][:2].view('<i4').astype(float).tolist();parameters.append({'name':'_DitherResolution','values':dims+[0,0]});value[:2]=0
  if row['property']=='_ClipRect':value=np.nan_to_num(value,posinf=2e10,neginf=-2e10)
  if not np.isfinite(value).all():raise RuntimeError((draw['eid'],row,value))
  parameters.append({'name':row['property'],'values':value.tolist()})
 draw['parameters']=parameters
 draw.pop('constants',None)
(base/'manifest.json').write_text(json.dumps(doc,separators=(',',':')))
(root/'doc/capture/ui-parameter-mapping.json').write_text(json.dumps(mappings,ensure_ascii=False,indent=2))
print('Removed CB runtime protocol; mapped',sum(len(x) for x in mappings.values()),'family parameter rows to material properties')
