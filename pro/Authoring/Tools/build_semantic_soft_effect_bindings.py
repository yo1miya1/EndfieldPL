"""发布两层墨纹/流光的真实有效分支；不把捕获深度、雾体积或CB页接入运行。"""
from pathlib import Path, PureWindowsPath
import json,struct,re

root=Path(__file__).resolve().parents[3]
base=root/'pro/Authoring/Extracted/SI1'
output=base/'Source/semantic-effect-bindings.json'
parts=[p for p in json.loads(output.read_text(encoding='utf-8'))['parts'] if p['sourceEvent'] not in [1693,1730]]
for eid in [1693,1730]:
    folder=base/f'EffectsRead/raw/mat/eid-{eid}'
    def rows(slot):
        data=(folder/f'cb-ps-{slot}.bin').read_bytes()
        return [struct.unpack_from('<4f',data,i) for i in range(0,len(data),16)]
    material=rows(4 if eid==1693 else 3)
    instance,frame,view=rows(2),rows(1),rows(0)
    draw=json.loads((folder/'draw.json').read_text(encoding='utf-8'))
    native=json.loads((base/f'EffectsNative/graphics/eid-{eid}.json').read_text(encoding='utf-8'))
    bindings=json.loads((base/f'EffectsNative/bindings/eid-{eid}.json').read_text(encoding='utf-8'))['stages']['ShaderStage.Pixel']
    formats={v['descriptor']['resource']:v['descriptor']['format']['name'] for v in bindings['readOnly']}
    textures=[]
    program=(base/f'EffectsPrograms/{eid}.hlsl').read_text(encoding='utf-8')
    samplerByTexture={int(t):int(s) for t,s in re.findall(r't(\d+)\.Sample\w*\(s(\d+)_s',program)}
    samplers={int(s['access']['index']):s['sampler'] for s in bindings['samplers']}
    for slot,name in [(1,'_InkBaseMap'),(2,'_InkMaskMap'),(3,'_InkNoiseMap')]:
        t=next(v for v in draw['textures'] if v['stage']=='ps' and v['bind_point']==slot)
        textures.append(dict(property=name,path='EffectsRead/'+PureWindowsPath(t['files'][0]).as_posix(),srgb='SRGB' in formats[t['resource']]))
        sampler=samplers[samplerByTexture[slot]]
        # 源3为边缘Clamp，不应乘黑边界覆盖；实际mip Point对应Unity Bilinear。
        if sampler['addressU'] not in [0,3] or sampler['addressV'] not in [0,3]: raise ValueError('Unexpected source address mode')
        textures[-1].update(wrapModeU='Clamp' if sampler['addressU']==3 else 'Repeat',
                            wrapModeV='Clamp' if sampler['addressV']==3 else 'Repeat', filterMode='Bilinear',
                            sourceSamplerSlot=samplerByTexture[slot])
    vectorRows={'_InkBaseTint':4,'_InkBaseUVTransform':9,'_InkBaseUVRotation':7,'_InkBaseUVVelocity':6,'_InkBaseUVWeights':8,
                '_InkMaskUVTransform':12,'_InkMaskUVRotation':14,'_InkMaskUVVelocity':13,'_InkMaskUVWeights':15,
                '_InkNoiseUVTransform':27,'_InkNoiseUVRotation':29,'_InkNoiseUVVelocity':28,'_InkNoiseUVWeights':30,'_InkNoiseResponse':25}
    vectors=[dict(property=name,value=list(material[index])) for name,index in vectorRows.items()]
    depthRow=32 if eid==1693 else 31
    vectors.extend([dict(property='_InkDepthRanges',value=[material[depthRow][1],material[depthRow][2],material[depthRow][3],material[depthRow+1][0]]),
                    dict(property='_InkProjectionParams',value=[0,0,0,0] if eid==1693 else list(material[33]))])
    if eid==1693:
        vectors.extend([dict(property='_InkEdgeParams',value=list(material[31])),dict(property='_InkEdgeTint',value=list(rows(3)[0]))])
    scalar={'_InkUVStreamBlend':material[1][0], '_InkPhase':frame[105][3]*(1-instance[14][0])+instance[14][1],
            '_InkAnimationSpeed':0,'_InkMipBias':frame[26][0],
            '_InkIgnoreVertexColor':material[1][1],'_InkColorGain':material[1][2],'_InkAlphaGain':material[1][3],
            '_InkBaseMonochrome':material[5][1],'_InkBaseDistortion':material[5][0],
            '_InkMaskMonochrome':material[11][0],'_InkMaskDistortion':material[11][1],
            '_InkDepthFadeEnabled':material[depthRow][0],'_InkInstanceOpacity':1-instance[4][1],'_InkLODFade':instance[4][0],
            '_InkAlphaMode':material[0][1],'_InkPreExposureWeight':material[3][0],
            '_InkCutoff':0,'_InkSoftIntersectionDistance':material[35][0],'_InkSoftIntersectionOffset':material[35][1]}
    state=native['outputMerger'];blend=state['blendState']['blends'][0]
    scalar.update(_Cull=native['rasterizer']['state']['cullMode'],_ZWrite=int(state['depthStencilState']['depthWrites']),
                  _SrcBlend=1,_DstBlend=10 if blend['enabled'] else 0,_ColorMask=blend['writeMask'])
    relative=[instance[3][i]-view[44][i] for i in range(3)]
    parts.append(dict(sourceEvent=eid,materialName=('InkRibbonRim_' if eid==1693 else 'ClothingFlowOverlay_')+str(eid),
                      shader='Endfield/InkEffect',renderQueue=3007 if eid==1693 else 3009,
                      keywords=['EF_INK_TWO_LAYER']+(['EF_INK_EDGE_TINT'] if eid==1693 else []),
                      textures=textures,vectors=vectors,scalars=[dict(property=k,value=v) for k,v in scalar.items()],
                      projectionOriginSceneFrame=[relative[0],-relative[2],relative[1]],requiresOpaqueDepthTexture=True))
output.write_text(json.dumps(dict(schemaVersion=1,parts=sorted(parts,key=lambda p:p['renderQueue'])),ensure_ascii=False,indent=2),encoding='utf-8')
print(output)
