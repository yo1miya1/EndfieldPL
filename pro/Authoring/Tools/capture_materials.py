"""已提取角色来源的公共语义读取、DDS描述和材质参数转换；不回放RDC。"""
from pathlib import Path
import json, math, os, struct

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'pro/Authoring/Extracted/Typhon2'
LEGACY = BASE / 'LegacySource'
OUT = BASE / 'Source'


class SourceReader:
    def __init__(self, extracted_root=None, capture_id='typhon2', legacy_root=None, evidence_root=None, origin=None):
        self.base=Path(extracted_root) if extracted_root is not None else BASE
        self.legacy=Path(legacy_root) if legacy_root is not None else self.base/'LegacySource'
        self.out=self.base/'Source'
        self.capture_id=capture_id
        self.name_prefix=self.base.name
        evidence=Path(evidence_root) if evidence_root is not None else self.base/'Evidence'
        self.package = json.loads((self.legacy/'capture-package.json').read_text(encoding='utf-8'))
        self.draws = {d['eid']: d for d in self.package['draws']}
        self.geometry = json.loads((self.legacy/'Geometry/import-manifest.json').read_text(encoding='utf-8'))
        self.meshes = {d['eid']: d for d in self.geometry['meshes']}
        self.caster_meshes = {d['meshEid'] for d in json.loads((self.legacy/'Shadow/shadow-manifest.json').read_text(encoding='utf-8'))['draws']}
        self.textures = {d['resourceId']: d for d in json.loads((self.legacy/'texture-import-manifest.json').read_text(encoding='utf-8'))['textures']}
        registry = json.loads((evidence/'character_family_registry.json').read_text(encoding='utf-8'))
        self.entries={entry['sourcePixelShaderSha256']:entry for entry in registry['entries']}
        self.materials = {m['eid']: m for m in registry['materials'] if m['capture']==capture_id}
        self.roles = json.loads((self.legacy/'page-calibration.json').read_text(encoding='utf-8'))['roles']
        self.origin = origin if origin is not None else json.loads((self.out/'scene-environment.json').read_text(encoding='utf-8'))['origin']
        self.cache = {}
        self.out.mkdir(parents=True, exist_ok=True)

    def data(self, eid, slot, stage='ps'):
        key = eid, slot, stage
        if key not in self.cache:
            draw = self.draws[eid]
            if draw['kind']=='forward' and stage=='ps':
                item = next(c for c in draw['constantBuffers'] if c['slot']==slot)
                path = self.legacy/item['path']
            else:
                name = ('GBuffer' if draw['kind']=='gbuffer' else 'Forward')+' '+stage.upper()
                blocks = self.materials.get(eid,{}).get('approvedBlocks',[])
                item = next((c for c in blocks if c['stage']==name and c['slot']==slot),None)
                if item is None:
                    item=next((r for r in self.roles if r['profileId']==draw['profileId'] and r['stage']==name and r['slot']==slot),None)
                if item is None:
                    # 环境GB的M页已按明确active-read行保存为vector；不为未读的行补语义。
                    prefix='_EF_'+stage.upper()+str(slot)+'_'
                    rows={int(v['name'][len(prefix):]):v['value'] for v in draw['vectors'] if v['name'].startswith(prefix)}
                    data=bytearray((max(rows)+1)*16)
                    for index,value in rows.items():struct.pack_into('<4f',data,index*16,*value)
                    self.cache[key]=bytes(data)
                    return self.cache[key]
                path = self.legacy/'Constants'/(item['sourceSha256']+'.bytes')
            self.cache[key] = path.read_bytes()
        return self.cache[key]

    def row(self, eid, slot, index, stage='ps'):
        return list(struct.unpack_from('<4f', self.data(eid,slot,stage), index*16))

    def vector(self, eid, name, default=None):
        return next((v['value'] for v in self.draws[eid].get('vectors',[]) if v['name']==name), default)

    def texture(self, eid, slot, property):
        binding = next(t for t in self.draws[eid]['textures'] if t['name']=='_EF_T'+str(slot))
        return self.resource(binding['resourceId'], property)

    def resource(self, resource_id, property):
        entry = self.textures[resource_id]
        folder = self.out/'DDSImports'; folder.mkdir(exist_ok=True)
        descriptor = folder/(str(resource_id)+'.json')
        source_file = self.legacy/entry['path']
        descriptor.write_text(json.dumps(dict(dds=os.path.relpath(source_file,folder).replace('\\','/'),
            viewFormat=entry['format']),indent=2),encoding='utf-8')
        return dict(property=property,ddsImportPath=descriptor.relative_to(self.base).as_posix(),
                    srgb=entry.get('srgb',False),wrapMode='Repeat',filterMode='Bilinear')


def scalar(name,value): return dict(property=name,value=float(value))
def vector(name,value): return dict(property=name,value=list(value))
def set_scalar(part,name,value):
    part['scalars']=[p for p in part['scalars'] if p['property']!=name]+[scalar(name,value)]
def set_vector(part,name,value):
    part['vectors']=[p for p in part['vectors'] if p['property']!=name]+[vector(name,value)]

PASS_BITS = {'EndfieldGBuffer':1,'EndfieldSurfaceLighting':2,'EndfieldForward':4,
    'EndfieldSurfaceOutline':8,'EndfieldOutline':16,'ShadowCaster':32,
    'CharacterShadowCaster':64,'EndfieldMotionVectors':128,'EndfieldEffect':256}

def fixed_state(reader,eid,part,passes):
    original={p['name']:p['value'] for p in reader.draws[eid].get('floatProperties',[])}
    part['enabledPasses']=passes
    set_scalar(part,'_RenderPassMask',sum(PASS_BITS[p] for p in passes))
    set_scalar(part,'_Cull',original.get('_EF_Cull',reader.draws[eid].get('cull',2)))
    set_scalar(part,'_ZWrite',original.get('_EF_ZWrite',int(reader.draws[eid].get('depthWrites',False))))
    for source,target,default in [('_EF_StencilRef','_OutlineStencilReference',0),
        ('_EF_StencilCompFront','_OutlineStencilComparison',8),
        ('_EF_StencilReadMask','_OutlineStencilReadMask',255),
        ('_EF_StencilWriteMask','_OutlineStencilWriteMask',255),
        ('_EF_StencilPassFront','_StencilPass',2),('_EF_StencilFailFront','_StencilFail',0),
        ('_EF_StencilZFailFront','_StencilZFail',0)]:
        set_scalar(part,target,original.get(source,default))


def common_surface(reader,eid,base_slot=None,normal_slot=None,mask_slot=None,lut_slot=None,ramp_slot=10):
    """可供独立受光FX复用；槽位必须由调用方的已知家族明确指定。"""
    d=reader.draws[eid]; m=lambda r:reader.row(eid,6,r); g=lambda r:reader.row(eid,1,r)
    part=dict(sourceEvent=eid,geometryEid=d['geometryEid'],shader='Endfield/HybridLit',
        materialName=reader.name_prefix+'_Surface_'+str(eid),
        category=reader.meshes[d['geometryEid']]['renderRole'].capitalize(),castShadows=False,
        renderQueue=d.get('renderQueue',2000),keywords=['EF_SOURCE_CHARACTER','EF_CLOTH'],
        scalars=[],vectors=[],textures=[])
    values={'_SourceCharacter':1,'_SourceMipBias':g(26)[0],'_NormalScale':m(0)[3],
        '_BackFaceNormal':m(1)[1], '_Roughness':1-m(0)[0], '_Specular':m(0)[1], '_Metallic':m(0)[2],
        '_SourceIndirectAlbedoGain':m(4)[2], '_SourceIndirectSaturation':m(4)[3],
        '_SourceRampBias':g(118)[3]*g(119)[0], '_SourceIndirectStrength':g(107)[2],
        '_SourceDiffuseStrength':g(107)[1], '_SourceSpecularStrength':g(120)[3],
        '_SourceShadowStrength':g(108)[1], '_SourceEnvironmentStrength':g(107)[3],
        '_SourceAmbientResponse':g(27)[0]*(g(29)[0]+g(119)[3]*(1-g(29)[0])),
        '_SourceDirectColorWeight':g(119)[1]}
    part['scalars']=[scalar(k,v) for k,v in values.items()]
    part['vectors']=[vector('_BaseColor',m(6)),vector('_BaseMap_ST',reader.vector(eid,'_EF_ForwardUV',[1,1,0,0])),
        vector('_SourceHemisphereDirection',g(113)),vector('_SourceHemisphereParams',g(114)),
        vector('_SourceAmbientTint',[1,1,1,1]),vector('_SourceEnvironmentRotation',g(123))]
    if base_slot is not None: part['textures'].append(reader.texture(eid,base_slot,'_BaseMap'))
    if normal_slot is not None:
        part['keywords'].append('EF_NORMAL_MAP');part['textures'].append(reader.texture(eid,normal_slot,'_NormalMap'))
    if mask_slot is not None:
        part['keywords']+=['EF_SOURCE_PACKED_MASK','EF_SOURCE_ENVIRONMENT_REFLECTION']
        part['textures'].append(reader.texture(eid,mask_slot,'_SourceMaskMap'))
    if lut_slot is not None:
        part['keywords'].append('EF_SOURCE_COLOR_LUT');part['textures'].append(reader.texture(eid,lut_slot,'_AlbedoResponseLut'))
        part['textures'][-1]['wrapMode']='Clamp'
    if ramp_slot is not None:
        part['textures'].append(reader.texture(eid,ramp_slot,'_LightingRamp'));part['textures'][-1]['wrapMode']='Clamp'
    fixed_state(reader,eid,part,['EndfieldSurfaceLighting'])
    return part

