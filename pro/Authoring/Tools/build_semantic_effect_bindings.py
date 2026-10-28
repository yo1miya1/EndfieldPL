"""读取源墨纹材质，发布语义参数；运行时没有原CB页或shader-id调度。"""
import pathlib, json, struct, re

root=pathlib.Path(__file__).resolve().parents[3]
extracted=root/'pro/Authoring/Extracted/SI1'
output=extracted/'Source/semantic-effect-bindings.json'
events=[1554,1571,1589,1607,1625,1672,1712]
parts=[p for p in json.loads(output.read_text(encoding='utf-8')).get('parts',[]) if p['sourceEvent'] not in events] if output.exists() else []
names={1554:'InkRibbonFine',1571:'InkRibbon',1589:'InkRibbonDepth',1607:'InkRibbonSideDepth',1625:'InkRibbonSide',1672:'InkRibbonFineDepth',1712:'ClothingSparkle'}
for sequence,eid in enumerate(events):
    folder=extracted/f'EffectsRead/raw/mat/eid-{eid}'
    def rows(slot):
        data=(folder/f'cb-ps-{slot}.bin').read_bytes()
        return [struct.unpack('<4f',data[offset:offset+16]) for offset in range(0,len(data),16)]
    material,frame,instance=rows(3),rows(1),rows(2)
    draw=json.loads((folder/'draw.json').read_text(encoding='utf-8'))
    native=json.loads((extracted/f'EffectsNative/graphics/eid-{eid}.json').read_text(encoding='utf-8'))
    bindings=json.loads((extracted/f'EffectsNative/bindings/eid-{eid}.json').read_text(encoding='utf-8'))['stages']['ShaderStage.Pixel']
    formats={entry['descriptor']['resource']:entry['descriptor']['format']['name'] for entry in bindings['readOnly']}
    texnames=['_InkBaseMap','_InkMaskMap','_InkOverlayMap','_InkNoiseMap']
    textures=[]
    sourceProgram=(extracted/f'EffectsPrograms/{eid}.hlsl').read_text(encoding='utf-8')
    samplerByTexture={int(t):int(s) for t,s in re.findall(r't(\d+)\.Sample\w*\(s(\d+)_s',sourceProgram)}
    samplers={int(s['access']['index']):s['sampler'] for s in bindings['samplers']}
    for slot,name in enumerate(texnames,start=1 if eid in [1554,1672] else 0):
        binding=next(t for t in draw['textures'] if t['stage']=='ps' and t['bind_point']==slot)
        path=pathlib.PureWindowsPath(binding['files'][0]).as_posix()
        textures.append(dict(property=name,path='EffectsRead/'+path,srgb='SRGB' in formats[binding['resource']]))
        sampler=samplers[samplerByTexture[slot]]
        # RenderDoc AddressMode: 0=Wrap，3=ClampEdge，4才是ClampBorder。
        if sampler['addressU'] not in [0,3] or sampler['addressV'] not in [0,3]: raise ValueError('Unexpected source address mode')
        textures[-1].update(wrapModeU='Clamp' if sampler['addressU']==3 else 'Repeat',
                            wrapModeV='Clamp' if sampler['addressV']==3 else 'Repeat', filterMode='Bilinear',
                            sourceSamplerSlot=samplerByTexture[slot])
    vector_rows={'_InkBaseTint':4,'_InkOverlayTint':21,
                 '_InkBaseUVTransform':9,'_InkBaseUVRotation':7,'_InkBaseUVVelocity':6,'_InkBaseUVWeights':8,
                 '_InkMaskUVTransform':12,'_InkMaskUVRotation':14,'_InkMaskUVVelocity':13,'_InkMaskUVWeights':15,
                 '_InkOverlayUVTransform':17,'_InkOverlayUVRotation':19,'_InkOverlayUVVelocity':18,'_InkOverlayUVWeights':20,
                 '_InkNoiseUVTransform':33,'_InkNoiseUVRotation':35,'_InkNoiseUVVelocity':34,'_InkNoiseUVWeights':36,
                 '_InkNoiseResponse':31,'_InkProjectionParams':39}
    vectors=[dict(property=name,value=list(material[row])) for name,row in vector_rows.items()]
    vectors.append(dict(property='_InkDepthRanges',value=[material[37][1],material[37][2],material[37][3],material[38][0]]))
    scalars={'_InkUVStreamBlend':material[1][0], '_InkPhase':frame[105][3]*(1-instance[14][0])+instance[14][1],
             '_InkAnimationSpeed':0,'_InkMipBias':frame[26][0],
             '_InkIgnoreVertexColor':material[1][1],'_InkColorGain':material[1][2],'_InkAlphaGain':material[1][3],
             '_InkBaseMonochrome':material[5][1],'_InkBaseDistortion':material[5][0],
             '_InkMaskMonochrome':material[11][0],'_InkMaskDistortion':material[11][1],
             '_InkOverlayDistortion':material[16][0],'_InkOverlayIgnoreVertexColor':material[16][1],
             '_InkDepthFadeEnabled':material[37][0],'_InkInstanceOpacity':1-instance[4][1],'_InkLODFade':instance[4][0],
             '_InkAlphaMode':material[0][1],'_InkPreExposureWeight':material[3][0],
             '_InkCutoff':material[41][0] if eid==1589 else material[42][0] if eid in [1607,1672] else 0,
             '_InkSoftIntersectionDistance':material[40][0] if eid in [1554,1672] else 0,
             '_InkSoftIntersectionOffset':material[40][1] if eid in [1554,1672] else 0}
    state=native['outputMerger'];blend=state['blendState']['blends'][0]
    scalars.update(_Cull=native['rasterizer']['state']['cullMode'],_ZWrite=int(state['depthStencilState']['depthWrites']),
                   _SrcBlend=1,_DstBlend=10 if blend['enabled'] else 0,_ColorMask=blend['writeMask'])
    part=dict(sourceEvent=eid,materialName=names[eid]+'_'+str(eid),shader='Endfield/InkEffect',keywords=['EF_INK_ALPHA_CLIP'] if eid in [1589,1607,1672] else [],
              renderQueue=3000+([1554,1571,1589,1607,1625,1649,1672,1693,1712,1730].index(eid)),
              textures=textures,vectors=vectors,scalars=[dict(property=name,value=value) for name,value in scalars.items()])
    projection=extracted/f'Effects/{eid}/projection-origin.json'
    view=rows(0)
    root_relative=[instance[3][k]-view[44][k] for k in range(3)]
    part['projectionOriginSceneFrame']=[root_relative[0],-root_relative[2],root_relative[1]]
    part['requiresOpaqueDepthTexture']=eid in [1554,1672]
    parts.append(part)
output.write_text(json.dumps(dict(schemaVersion=1,parts=parts),ensure_ascii=False,indent=2),encoding='utf-8')
print(output)
