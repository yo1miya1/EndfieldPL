"""将1649实际材质映射到通用LayeredCloth功能，几何由Effects/import.json单独管理。"""
import pathlib,json,struct

root=pathlib.Path(__file__).resolve().parents[3]
extracted=root/'pro/Authoring/Extracted/SI1'
folder=extracted/'EffectsRead/raw/mat/eid-1649'
def rows(slot):
    data=(folder/f'cb-ps-{slot}.bin').read_bytes()
    return [struct.unpack('<4f',data[offset:offset+16]) for offset in range(0,len(data),16)]
material,frame=rows(6),rows(1)
draw=json.loads((folder/'draw.json').read_text(encoding='utf-8'))
bindings=json.loads((extracted/'EffectsNative/bindings/eid-1649.json').read_text(encoding='utf-8'))['stages']['ShaderStage.Pixel']
formats={entry['descriptor']['resource']:entry['descriptor']['format']['name'] for entry in bindings['readOnly']}
texture_slots={20:'_BaseMap',21:'_SourceMaskMap',22:'_NormalMap',14:'_LightingRamp',15:'_ClothCoatReflectanceMap',16:'_ClothCoatMaskMap'}
textures=[]
for slot,name in texture_slots.items():
    entry=next(t for t in draw['textures'] if t['stage']=='ps' and t['bind_point']==slot)
    rid=entry['resource'].split('::')[-1]
    path='EffectsRead/'+pathlib.PureWindowsPath(entry['files'][0]).as_posix() if slot==15 else f'Textures/tex_{rid}.png'
    textures.append(dict(property=name,path=path,resourceId=entry['resource'],srgb='SRGB' in formats[entry['resource']]))
textures.append(dict(next(t for t in textures if t['property']=='_BaseMap'),property='_AlphaMap'))
vectors={'_BaseColor':material[6], '_BaseMap_ST':[1,1,0,0],
         '_ClothAnisotropy':material[12],'_ClothSecondLobeColor':material[14], '_ClothCoatColor':material[16],
         '_SourceHemisphereDirection':[-frame[116][0],frame[116][1],-frame[116][2],0],
         '_SourceHemisphereParams':frame[117], '_SourceAmbientTint':[1,1,1,1]}
vectors['_SourceEnvironmentRotation']=frame[126]
scalars={'_SourceCharacter':1,'_NormalScale':material[0][3],'_BackFaceNormal':material[1][1],
         '_SourceMipBias':frame[26][0],'_SourceIndirectAlbedoGain':material[4][2], '_SourceIndirectSaturation':material[4][3],
         '_SourceRampBias':frame[121][3]*frame[122][0], '_SourceIndirectStrength':frame[110][2],
         '_SourceDiffuseStrength':frame[110][1], '_SourceSpecularStrength':frame[123][3], '_SourceShadowStrength':frame[111][1],
         '_ClothCoatSmoothness':material[15][0],'_ClothCoatMetallic':material[15][1],'_ClothCoatNormalBlend':material[15][2],
         '_Opacity':material[6][3],'_Cull':0,'_SrcBlend':1,'_DstBlend':10,'_ZWrite':1}
scalars['_SourceAmbientResponse']=frame[27][0]*(frame[29][0]+frame[122][3]*(1-frame[29][0]))
scalars['_SourceDirectColorWeight']=frame[122][1]
scalars['_ClothTangentMode']=material[13][0]
scalars['_SourceEnvironmentStrength']=frame[110][3]
part=dict(sourceEvent=1649,shader='Endfield/HybridLit',castShadows=True,renderQueue=3005,
          keywords=['EF_CLOTH','EF_NORMAL_MAP','EF_SOURCE_CHARACTER','EF_SOURCE_PACKED_MASK','EF_SOURCE_ANISOTROPIC','EF_SOURCE_STOCHASTIC_SHADOW','EF_SOURCE_ENVIRONMENT_REFLECTION'],
          textures=textures,vectors=[dict(property=k,value=list(v)) for k,v in vectors.items()],
          scalars=[dict(property=k,value=v) for k,v in scalars.items()])
output=extracted/'Source/semantic-layered-material-bindings.json'
output.write_text(json.dumps(dict(schemaVersion=1,parts=[part]),ensure_ascii=False,indent=2),encoding='utf-8')
print(output)
