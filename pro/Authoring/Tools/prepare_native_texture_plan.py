"""从已发布语义绑定生成最小实际纹理清单，不选择捕获颜色/深度RT。"""
from pathlib import Path
import json, re

root = Path(__file__).resolve().parents[3]
base = root / 'pro/Authoring/Extracted/SI1'
records = {}
source_views = {}
for material in json.loads((base / 'Source/material-bindings.json').read_text(encoding='utf-8'))['materials']:
    for stage, bindings in material['stages'].items():
        for binding in bindings.get('readOnlyResources', []):
            for descriptor in binding.get('descriptors', []):
                ref = descriptor.get('resourceId', '')
                if not ref.startswith('ResourceId::'): continue
                rid = int(ref.split('::')[-1])
                source_views.setdefault(rid, []).append(dict(sourceEvent=material['eid'], stage=stage,
                    slot=binding['bindPoint'], format=descriptor['format'], view=descriptor.get('viewId')))
for path in sorted((base / 'Source').glob('semantic*bindings*.json')):
    for part in json.loads(path.read_text(encoding='utf-8'))['parts']:
        for texture in part.get('textures', []):
            ref = str(texture.get('resourceId', '')) or str(texture.get('path', ''))
            match = re.search(r'(?:ResourceId::|ResourceId_|tex_)(\d+)', ref)
            if not match: continue
            rid = int(match[1])
            records.setdefault(rid, []).append(dict(sourceEvent=part['sourceEvent'], property=texture['property'],
                sourceDeclaredSrgb=texture.get('srgb'), bindingManifest=path.relative_to(base).as_posix()))
for rid, eid, prop in [(24401,1210,'_BaseMap'), (25127,1210,'_PatternMap'), (24403,1190,'_EffectTexture'), (1727219,635,'_OutlineMask')]:
    records.setdefault(rid, []).append(dict(sourceEvent=eid, property=prop))
plan = dict(capture=str(root / 'pro/Authoring/Work/SI1.rdc'), output=str(base / 'TexturesNative'),
            resources=[dict(resourceId=rid, consumers=consumers, sourceViews=source_views.get(rid, [])) for rid,consumers in records.items()])
destination = root / 'pro/Authoring/Work/native-texture-plan.json'
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(plan, indent=2), encoding='utf-8')
print(destination)
