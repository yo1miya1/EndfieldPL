"""从本次 SI-1 读取记录生成语义材质；不读取旧角色数据。"""
import json, pathlib, struct

root = pathlib.Path(__file__).resolve().parents[3]
source = root / 'pro/Authoring/Extracted/SI1/Source'
records = {}
for p in (source / 'Constants').glob('*.json'):
    d = json.loads(p.read_text(encoding='utf-8'))
    records[d['eventId'], d['stage'], d['bindSlot']] = {'result': d}
materials = json.loads((source / 'material-bindings.json').read_text(encoding='utf-8'))['materials']
bindings = {d['eid']: {'result': {'stages': d['stages']}} for d in materials}

def row(e, stage, slot, r):
    d = records[e, stage, slot]
    return d['result']['variables'][r]['floatValues']

def resource(e, slot, stage='ps'):
    for t in bindings[e]['result']['stages'][stage]['readOnlyResources']:
        if t['bindPoint'] == slot:
            return {'resourceId': t['resourceId'], 'srgb': 'SRGB' in t['descriptors'][0]['format']}
    raise KeyError((e, slot))

def texture(e, slot, prop, stage='ps'):
    return dict(property=prop, **resource(e, slot, stage))

def scalar(prop, value):
    return dict(property=prop, value=value)

def vector(prop, value):
    return dict(property=prop, value=list(value))

forward_for = {488:1040, 502:1061, 520:997, 538:1019, 553:1082, 568:1101, 585:1122, 599:1143, 617:1165}
parts = []
for e, f in forward_for.items():
    slot = 3 if e in (538,553,568) else 2
    instslot = 2 if slot == 3 else 1
    frameslot = 1 if slot == 3 else 0
    vs = 3
    kw = ['EF_SOURCE_CHARACTER']
    kw += ['EF_FACE' if e in (488,538,553,568) else 'EF_EYE' if e == 502 else 'EF_HAIR' if e == 617 else 'EF_CLOTH']
    if e not in (488,502): kw += ['EF_NORMAL_MAP']
    if e in (538,553,568): kw += ['EF_SOURCE_VIEW_TINT']
    if e == 617: kw += ['EF_SOURCE_COVERAGE']
    packed = struct.unpack('<I', struct.pack('<f', row(e, 'ps', instslot, 5)[2]))[0]
    payload = [(packed & 1023) / 1023, ((packed>>10)&1023)/1023, ((packed>>20)&1023)/1023, (packed>>30)/3]
    scalars = [scalar('_NormalScale', row(e,'ps',slot,0)[3]), scalar('_BackFaceNormal',row(e,'ps',slot,1)[1]),
               scalar('_SourceMipBias', row(e,'ps',frameslot,26)[0]), scalar('_SourceCharacter',1),
               scalar('_SourceGBufferTag', 1 if e==617 else .4 if e in (538,553,568) else 0),
               scalar('_Cull',0 if e in (520,585,599) else 2)]
    # 实际GBuffer的bit16门控：FaceDetail/Eye写保护，Hair只通过未保护像素。
    scalars += [scalar('_OutlineStencilReference',16 if e in (488,502) else 0),
                scalar('_OutlineStencilComparison',3 if e==617 else 8)]
    vectors = [vector('_BaseColor', row(e,'ps',slot,6)), vector('_SourceInstancePayload',payload), vector('_BaseMap_ST',row(e,'vs',vs,10))]
    textures = [texture(e,0,'_BaseMap')]
    if e not in (488,502): textures += [texture(e,1,'_NormalMap')]
    if e in (538,553,568):
        scalars += [scalar('_ViewTintStrength',row(e,'ps',slot,12)[0])]
        vectors += [vector('_ViewTintColor',row(e,'ps',slot,13))]
    if e == 617:
        scalars += [scalar('_Cutoff',row(e,'ps',slot,12)[0])]
        textures += [texture(e,2,'_CoverageMap')]
        kw += ['EF_SOURCE_SCREEN_OUTLINE']
        textures += [texture(635,1,'_SourceOutlineWidthMap',stage='vs'),texture(635,0,'_SourceOutlineCoverageMap')]
        scalars += [scalar('_SourceOutlineWidth',row(635,'vs',3,13)[0]),scalar('_SourceOutlineDepth',row(635,'vs',3,13)[1]),
                    scalar('_SourceOutlineSmoothNormal',row(635,'vs',3,14)[0]),scalar('_SourceOutlineCutoff',row(635,'ps',1,12)[0])]
    fm = lambda r: row(f,'ps',6,r)
    fg = lambda r: row(f,'ps',1,r)
    # 原Forward材质中的物理参数，Mask类从源纹理R/G/A逐像素读取。
    if e in (520,585,599):
        kw += ['EF_SOURCE_PACKED_MASK','EF_SOURCE_ENVIRONMENT_REFLECTION']
        vectors += [vector('_SourceEnvironmentRotation',fg(126))]
        textures += [texture(f,17 if e==520 else 18,'_SourceMaskMap')]
        scalars += [scalar('_SourceIndirectAlbedoGain',fm(4)[2]), scalar('_SourceIndirectSaturation',fm(4)[3])]
    if e in (585,599):
        textures += [texture(f,20,'_EmissionMap')]
        vectors += [vector('_EmissionColor',[value*fm(1)[3] for value in fm(7)[:3]]+[1])]
    if e == 599:
        kw += ['EF_SOURCE_PARALLAX_GLOW']
        textures += [dict(texture(f,13,'_ParallaxGlowMap'),wrapMode='Repeat',filterMode='Bilinear')]
        vectors += [vector('_ParallaxGlowParams',fm(12)),vector('_ParallaxGlowColor',fm(13)),vector('_ParallaxGlowMap_ST',fm(14))]
    if e == 585:
        kw += ['EF_SOURCE_ANISOTROPIC']
        textures += [texture(f,13,'_ClothCoatMaskMap'),texture(f,12,'_ClothCoatReflectanceMap')]
        vectors += [vector('_ClothAnisotropy',fm(12)),vector('_ClothSecondLobeColor',fm(14)),vector('_ClothCoatColor',fm(16))]
        scalars += [scalar('_ClothTangentMode',fm(13)[0])]
        scalars += [scalar('_ClothCoatSmoothness',fm(15)[0]),scalar('_ClothCoatMetallic',fm(15)[1]),scalar('_ClothCoatNormalBlend',fm(15)[2])]
    else:
        scalars += [scalar('_Roughness',1-fm(0)[0]), scalar('_Specular',fm(0)[1]), scalar('_Metallic',fm(0)[2])]
    if e in (553,568):
        lutslot = 14
        kw += ['EF_SOURCE_SKIN']
        textures += [texture(f,20,'_SkinLightingSdf'),texture(f,21,'_SkinRegionMap')]
        textures += [texture(f,12,'_SkinSpecularMap')]
        # posed网格已在场景局部空间，保留原实例的解剖轴并转为同一Unity基底。
        skin_right,skin_forward = row(f,'ps',2,0),row(f,'ps',2,2)
        vectors += [vector('_SkinRightOS',[-skin_right[0],skin_right[1],-skin_right[2],0]),
                    vector('_SkinForwardOS',[-skin_forward[0],skin_forward[1],-skin_forward[2],0]),
                    vector('_SkinViewTintStrength',fm(12))]
        vectors += [vector('_SkinSpecularParallax',fm(17))]
        skin_origin=row(f,'ps',2,3)
        camera_origin=row(f,'ps',0,44)
        relative=[skin_origin[i]-camera_origin[i] for i in range(3)]
        scene_frame=[relative[0],-relative[2],relative[1]]
        scene_origin=json.loads((source/'scene.rdc2scene').read_text(encoding='utf-8-sig'))['origin']['point']
        delta=[scene_frame[i]-scene_origin[i] for i in range(3)]
        vectors += [vector('_SkinHemisphereOriginOS',[-delta[0],delta[2],delta[1],0])]
        scalars += [scalar('_SkinSdfBias',fg(126)[3]*fg(111)[3])]
    else:
        lutslot = 12 if e in (488,538) else None
    if lutslot is not None:
        kw += ['EF_SOURCE_COLOR_LUT']
        textures += [texture(f,lutslot,'_AlbedoResponseLut')]
    textures += [texture(f,13 if e==617 else 11,'_LightingRamp')]
    if e in (502,617):
        scalars += [scalar('_SourceIndirectAlbedoGain',fm(4)[2]),scalar('_SourceIndirectSaturation',fm(4)[3])]
    ambient_source = fg(113) if e in (538,553,568) else fg(112)
    ambient_reference = fg(112)
    vectors += [vector('_SourceAmbientTint',[ambient_source[i]/ambient_reference[i] for i in range(3)]+[1])]
    hemi=fg(116)
    vectors += [vector('_SourceHemisphereDirection',[-hemi[0],hemi[1],-hemi[2],0]),vector('_SourceHemisphereParams',fg(117))]
    scalars += [scalar('_SourceAmbientResponse',fg(27)[0]*(fg(29)[0]+fg(122)[3]*(1-fg(29)[0]))),scalar('_SourceDirectColorWeight',fg(122)[1])]
    scalars += [scalar('_SourceEnvironmentStrength',fg(110)[3])]
    if e == 617:
        textures += [texture(f,17,'_HairMaskMap'),texture(f,18,'_HairNormalMap'),texture(f,14,'_HairSpecularRamp')]
        vectors += [vector('_HairPrimarySecondaryShift',fm(13)),vector('_HairSecondaryColor',fm(15))]
        textures += [texture(f,12,'_HairOcclusionMap')]
        vectors += [vector('_HairOcclusionLobe',fm(16)),vector('_HairOcclusionResponse',fm(17)),vector('_HairOcclusionMap_ST',fm(18))]
        scalars += [scalar('_HairPrimaryStrength',fm(13)[2]),scalar('_HairSecondarySmoothness',fm(14)[0]),scalar('_HairFlowDirection',fm(14)[1]),scalar('_HairDetailNormalScale',fm(12)[1])]
        scalars += [scalar('_HairViewAlignmentPower',fm(13)[3])]
        hr,hf=row(f,'ps',2,0),row(f,'ps',2,2)
        vectors += [vector('_HairRightOS',[-hr[0],hr[1],-hr[2],0]),vector('_HairForwardOS',[-hf[0],hf[1],-hf[2],0])]
    if e == 502:
        textures += [texture(f,14,'_EyeReflectionMap')]
        vectors += [vector('_EyeIrisTint',fm(15)),vector('_EyeScleraTint',fm(16)),vector('_EyeReflectionColor',fm(18))]
        scalars += [scalar('_EyeReflectionStrength',fm(18)[3]),scalar('_EyeParallax',fm(12)[1]),scalar('_EyeCurvature',fm(17)[1])]
    scalars += [scalar('_SourceRampBias',fg(121)[3]*fg(122)[0]), scalar('_SourceIndirectStrength',fg(110)[2]),
                scalar('_SourceDiffuseStrength',fg(110)[1]),scalar('_SourceSpecularStrength',fg(123)[3]),
                scalar('_SourceShadowStrength',fg(111)[1])]
    parts.append(dict(sourceEvent=e, sourceLightingEvent=f, shader='Endfield/HybridLit', keywords=kw, scalars=scalars,vectors=vectors,textures=textures))

# 环境绘制655与旧SharedEnvironment是同一数学段；物理字段沿原遮罩变换输出。
e=655
em=lambda r:row(e,'ps',2,r)
vectors=[vector('_BaseColor',em(8)),vector('_EnvironmentBaseUV_ST',em(11)),vector('_EnvironmentMaterialUV_ST',em(12)),vector('_EnvironmentRoughnessRange',[em(0)[2],em(0)[3],0,0])]
values={'_NormalScale':em(0)[0],'_Occlusion':em(1)[0],'_BackFaceNormal':em(1)[3],
        '_EnvironmentAlbedoUVWeight':em(2)[3],'_EnvironmentMaterialUVWeight':em(3)[0],
        '_EnvironmentMetallicOverrideWeight':em(3)[3],'_EnvironmentMetallicOverride':em(4)[1],
        '_EnvironmentBaseGain':em(4)[2],'_EnvironmentBaseBlend':em(4)[0],
        '_EnvironmentSpecularRoughnessWeight':em(4)[3],'_EnvironmentSpecularBias':em(5)[0],
        '_EnvironmentSpecularMetallicWeight':em(5)[1],'_EnvironmentLightingWeight':em(7)[0],
        '_EnvironmentReflectionMask':em(7)[1],'_EnvironmentNormalMipBias':em(3)[1],
        '_SourceMipBias':row(e,'ps',0,26)[0], '_SourceEnvironment':1,'_Cull':0}
inst=row(e,'ps',1,4)
values['_EnvironmentMotionDisabled']=1 if max(inst[1],inst[2])>.1 else 0
tag=row(e,'ps',3,0)
values['_EnvironmentMaterialTag']=tag[3] if tag[0]>.5 else 0
parts.append(dict(sourceEvent=e,shader='Endfield/HybridLit',renderQueue=2500,keywords=['EF_SOURCE_ENVIRONMENT'],scalars=[scalar(k,v) for k,v in values.items()],vectors=vectors,textures=[texture(e,0,'_BaseMap'),texture(e,1,'_NormalMap'),texture(e,2,'_EnvironmentMaskMap')]))

# 1190 原不透明效果前向：One/Zero + ZWrite + CullFront；此帧关闭溶解/屏幕扭曲/深度淡出。
e=1190
fx=lambda r:row(e,'ps',3,r)
frame=lambda r:row(e,'ps',1,r)
values={'_SourceEffect':1,'_Cull':1,'_SrcBlend':1,'_DstBlend':0,'_ZWrite':1,
        '_SourceMipBias':frame(26)[0],'_EffectMipBias':fx(5)[2],
        '_EffectIgnoreVertexColor':1 if fx(1)[1]!=0 else 0,
        '_EffectColorIntensity':fx(1)[2],'_EffectAlphaIntensity':fx(1)[3],
        '_EffectMonochromeWeight':fx(5)[1],'_EffectInvisibleWeight':fx(13)[3],
        '_EffectDissolveEnabled':fx(14)[1],'_EffectDissolveMask':fx(13)[2],
        '_EffectDissolveHeight':fx(16)[3],
        '_EffectBloomThreshold':fx(2)[1],'_EffectBloomBoost':fx(2)[2],
        '_EffectPreExposureWeight':fx(3)[0],'_EffectDepthFadeEnabled':fx(11)[0],
        '_EffectInstanceOpacity':1-row(e,'ps',2,4)[1],
        '_EffectOpacity':1+fx(19)[1]*(frame(109)[0]-1),
        '_EffectAlphaMode':fx(0)[1],'_EffectColorResponseWeight':fx(2)[3]}
vectors=[vector('_EffectColor',fx(4)),vector('_EffectDissolveColor',fx(21)),
         vector('_EffectDissolveProfile',fx(17)),vector('_EffectColorResponse',frame(106)),
         vector('_EffectDepthRanges',[fx(11)[1],fx(11)[2],fx(11)[3],fx(12)[0]]),
         vector('_BaseMap_ST',row(e,'vs',4,9))]
color_file=root/'doc/capture/effect1190-constant-color.json'
vectors.append(vector('_EffectVertexColor',json.loads(color_file.read_text(encoding='utf-8'))['value']))
# SaveTexture的PNG已是BC7_SRGB解码后的线性像素：例如texel(0,0) GPU=.9296875，PNG=237/255。
# 不能仅凭原SRV格式再声明sRGB，否则发布资产会对它二次解码。
sky_texture=texture(e,0,'_BaseMap')
sky_texture['srgb']=False
parts.append(dict(sourceEvent=e,shader='Endfield/HybridLit',keywords=['EF_SOURCE_EFFECT'],scalars=[scalar(k,v) for k,v in values.items()],vectors=vectors,textures=[sky_texture],renderQueue=2000))

output = source/'semantic-material-bindings.json'
output.write_text(json.dumps({'schemaVersion':1, 'parts':parts},ensure_ascii=False,indent=2),encoding='utf-8')
print(output)
print('parts:',len(parts))

# Create the initial Unity Light from semantic radiance and direction, never from a runtime source CB.
g=lambda r:row(1019,'ps',1,r)
l=lambda r:row(1019,'ps',3,r)
direction=[g(111)[3]*(g(121)[i]+l(0)[i])-l(0)[i] for i in range(3)]
energy=l(3)[3]+g(122)[3]*(g(115)[3]-l(3)[3])
radiance=[(l(3)[i]+g(122)[1]*(g(114)[i]-l(3)[i]))*energy for i in range(3)]
ambient=g(112)[:3]
scene=dict(sourceEvent=1019,sourceSpace='Source D3D world, Y-up; convert by the geometry importer basis, not Blender camera basis.',directionTowardLight=direction,linearRadiance=radiance,
           ambientMode='Custom',sourceAmbientBranch='PS cb1[111].y=1: source1040 line71 SH-volume branch (<0.5) skipped; else returns cb1[112].rgb.',
           linearAmbientRadiance=ambient,unityAmbientProbeL0=ambient,
           ambientEncoding='Unity SHCoefficients.GetSHA directly copies sh[channel,0]-sh[channel,6] into shader constant w. Assign sh[channel,0]=linearAmbientRadiance[channel], all other coefficients zero. Do not divide by a standard SH basis constant; Unity storage is already pre-scaled. No extra gamma conversion.',
           ambientStatus='This capture uses the source constant ambient fallback. Static 3D SH volumes are bound but inactive in this branch.')
# 角色独立阴影的语义Profile：从真实producer CB与Caster状态导出，运行时不读取原CB。
# 914 cb3[188].z已由矩阵X梯度及1024 tile严格确认是worldTexelX，偏移为其3/6倍。
shadow_source = source.parent / 'ShadowReceiverNative'
shadow_cb = (shadow_source / 'graphics-constants/eid-914/Pixel-cb-3.bin').read_bytes()
shadow_row = lambda r: struct.unpack_from('<4f', shadow_cb, 16*r)
receiver = shadow_row(188)
tile_scale = shadow_row(218)
atlas_size = shadow_row(233)
caster_state = json.loads((shadow_source / 'graphics/eid-372.json').read_text(encoding='utf-8'))['rasterizer']['state']
scene['characterShadowProfile'] = dict(sourceEvent=914,
    receiverDepthBiasTexels=receiver[0]/receiver[2],
    receiverNormalBiasTexels=receiver[1]/receiver[2],
    filterRadiusTexels=4, # 914原程序的radius=cb3[233].x*4，不是可猜测的blur半径。
    tileResolution=round(tile_scale[2]*atlas_size[2]),
    # Unity在D3D reversed-Z下翻转SetGlobalDepthBias的符号；Native源值为-8/-0。
    casterDepthBias=-caster_state['depthBias'],casterSlopeBias=-caster_state['slopeScaledDepthBias'])
(source/'semantic-scene-settings.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2),encoding='utf-8')
