"""把已归档的真实几何/参数整理为共享发布器的独立输入。

旧world2已是减去捕获相机绝对原点的unity-world。这里只选角色中心作为新场景
原点，发布器统一平移几何、相机、灯光一次；不套SI1的轴变换、不重新解算法线。
"""
from pathlib import Path
import argparse
import json
import math
import struct
import numpy as np


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def pipeline_rows(package, kind, event, slot, legacy):
    entry = next(x for x in package[kind] if x['sourceEid'] == event)
    page = next(x for x in entry['constants']
                if x['slot'] == slot and x.get('stage', 'ps') != 'vs')
    return list(struct.iter_unpack('<4f', (legacy / 'Pipeline' / page['path']).read_bytes()))


def linear_to_srgb(value):
    return value * 12.92 if value <= .0031308 else 1.055 * value ** (1 / 2.4) - .055


def prepare_environment(root, capture_id, reflection_resource_id=65716):
    ROOT = Path(root)
    DATA = ROOT / 'pro/Authoring/Extracted' / capture_id
    LEGACY = DATA / 'LegacySource'
    SOURCE = DATA / 'Source' 
    geometry = read_json(LEGACY / 'Geometry/import-manifest.json')
    capture = read_json(LEGACY / 'capture-package.json')
    pipeline = read_json(LEGACY / 'Pipeline/pipeline-package.json')
    # 归档中的canonicalEid标识已核实的同一producer公式，sourceEid随capture变化。
    def source_event(kind, canonical):
        return next(entry['sourceEid'] for entry in pipeline[kind] if entry['canonicalEid'] == canonical)
    roles = dict(shadow=source_event('fullscreen', 1331), dof=source_event('compute', 2311),
                 bloom=source_event('compute', 2551), scatter=source_event('compute', 2632),
                 display=source_event('fullscreen', 2742))
    primary_events = {d['geometryEid'] for d in capture['draws'] if d['kind'] == 'gbuffer'}
    positions = []
    for mesh in geometry['meshes']:
        if mesh['eid'] in primary_events and mesh['renderRole'] == 'character':
            raw = (LEGACY / mesh['path']).read_bytes()
            count = struct.unpack_from('<I', raw)[0]
            positions.append(np.frombuffer(raw, dtype='<f4', count=count * 3, offset=16).reshape(-1, 3))
    vertices = np.concatenate(positions)
    low, high = vertices.min(0), vertices.max(0)
    origin = [(float(low[0]) + float(high[0])) * .5, float(low[1]),
              (float(low[2]) + float(high[2])) * .5]
    vp = np.array(geometry['camera']['vp'], dtype=np.float64).reshape(4, 4)
    forward = vp[3, :3] / np.linalg.norm(vp[3, :3])
    up = -vp[1, :3] / np.linalg.norm(vp[1, :3])
    depth_scale = float(vp[2, :3] @ forward)
    camera = dict(coordinateFrame='unity-world', origin=origin, cameraPosition=[0, 0, 0],
                  cameraForward=forward.tolist(), cameraUp=up.tolist(),
                  fieldOfView=math.degrees(2 * math.atan(1 / np.linalg.norm(vp[1, :3]))),
                  aspect=geometry['camera']['width'] / geometry['camera']['height'],
                  nearClipPlane=float(vp[2, 3] / (1 - depth_scale)),
                  farClipPlane=float(-vp[2, 3] / depth_scale),
                  lightCoordinateFrame='unity-world')
    light_data = read_json(LEGACY / 'Lighting/local-lights.json')
    camera['localLights'] = [{key: light[key] for key in
                             ('name', 'type', 'position', 'forward', 'linearRadiance',
                              'range', 'spotAngle', 'innerSpotAngle')}
                            for light in light_data['lights']]
    for local, source in zip(camera['localLights'], light_data['lights']):
        local.update(responseMode=source['responseMode'],
                     castShadows=source['shadowProjectionIndex'] >= 0,
                     responseStrength=source['responseParameters'][0],
                     surfaceColorWeight=source['responseParameters'][1],
                     specularRoughnessBlend=source['responseParameters'][1],
                     radialFalloffPower=source['responseParameters'][1] * 2,
                     normalResponseWeight=source['responseParameters'][3],
                     falloffExponent=source['falloffExponent'],
                     specularScale=source['specularScale'],
                     evaluationOrder=source['sourceRecord'])
    # 源角色接收核与局部投影。这里只保存无量纲比例；运行矩阵随Unity灯/包围盒变化。
    shadow = pipeline_rows(pipeline, 'fullscreen', roles['shadow'], 3, LEGACY)
    receiver, rect, atlas = shadow[508], shadow[538], shadow[553]
    caster = read_json(LEGACY / 'Shadow/shadow-manifest.json')['draws'][0]
    camera['characterShadowProfile'] = dict(
        sourceEvent=roles['shadow'], tileResolution=round(rect[2] * atlas[2]),
        receiverDepthBiasTexels=receiver[0] / receiver[2],
        receiverNormalBiasTexels=receiver[1] / receiver[2], filterRadiusTexels=4,
        filterAspectRatio=atlas[2] / atlas[3],
        casterDepthBias=-caster['nativeDepthBias'], casterSlopeBias=-caster['nativeSlopeBias'])
    # 65716是仅ShaderRead的静态BC6 cube，角色实际使用；71587是另一环境draw的独立纹理。
    cube_import = DATA / 'TextureImports/EnvironmentReflection.json'
    write_json(cube_import, dict(dds=f'../LegacySource/Textures/resource-{reflection_resource_id}.dds.bytes',
                                viewFormat='BC6_UFLOAT', sourceResourceId=reflection_resource_id))
    camera['environmentReflectionDdsImportPath'] = cube_import.relative_to(DATA).as_posix()
    write_json(SOURCE / 'scene-environment.json', camera)

    dof = pipeline_rows(pipeline, 'compute', roles['dof'], 1, LEGACY)
    bloom_threshold = pipeline_rows(pipeline, 'compute', roles['bloom'], 1, LEGACY)[1]
    scatter = pipeline_rows(pipeline, 'compute', roles['scatter'], 0, LEGACY)[0][0]
    frame = pipeline_rows(pipeline, 'fullscreen', roles['display'], 0, LEGACY)
    display = pipeline_rows(pipeline, 'fullscreen', roles['display'], 1, LEGACY)
    knee = (bloom_threshold[2] * .5 - .00001) / bloom_threshold[0]
    post = dict(
        provenance={'depthOfField': f"CS{roles['dof']} cb1[1..2]", 'bloomThreshold': f"CS{roles['bloom']} cb1[1]",
                    'bloomScatter': f"CS{roles['scatter']} cb0[0].x", 'display': f"PS{roles['display']} cb0[27],cb1[1,2,4,9,11]",
                    'grading': 'Legacy shared LUT GPU-verified inferred parameters; producer CB not located'},
        exposure=math.log2(frame[27][0]), nearDof=list(dof[1][:3]), farDof=list(dof[2][:3]),
        bloomThresholdGamma=linear_to_srgb(bloom_threshold[0]), bloomSoftKnee=knee,
        bloomScatter=scatter, bloomMaxIterations=9, bloomIntensity=display[9][0],
        bloomTint=list(display[11]), bloomHighlightSuppression=display[9][2],
        vignetteCenter=list(display[1][:2]), vignetteAspectBlend=display[1][3],
        vignetteShape=list(display[2]), vignetteColor=list(display[4]),
        gradingSaturation=1.08, gradingShadowWeight=-.1052631139755249)
    write_json(SOURCE / 'semantic-post-process.json', post)
    write_json(ROOT / 'doc/capture' / capture_id.lower() / 'scene-parameter-mapping.json',
               {'captureSha256': capture['captureSha256'],
                'coordinateSource': 'LegacySource/Geometry/import-manifest.json, camera-relative unity-world',
                'originRule': 'Horizontal center and minimum Y of character GBuffer bounds; all scene positions shifted once at publication',
                'camera': camera, 'postProcess': post})
    return geometry, camera


def build_scene_plan(geometry, environment, root, capture_id):
    ROOT = Path(root)
    DATA = ROOT / 'pro/Authoring/Extracted' / capture_id
    SOURCE = DATA / 'Source' 
    materials = read_json(SOURCE / 'semantic-material-bindings.json')
    effects = read_json(SOURCE / 'semantic-effect-bindings.json')
    lighting = read_json(SOURCE / 'semantic-scene-settings.json')
    meshes = {m['eid']: m for m in geometry['meshes']}
    parts = []
    for source_part in sorted(materials['parts'] + effects['parts'], key=lambda part: part['sourceEvent']):
        part = dict(source_part)
        mesh = meshes[part.get('geometryEid', part['sourceEvent'])]
        part['binary'] = '../LegacySource/' + mesh['path']
        part['placement'] = mesh['matrix']
        part['placed'] = False  # 已baked，不再乘原实例矩阵。
        if mesh.get('extrasPath'):
            part['extrasPath'] = 'LegacySource/' + mesh['extrasPath']
            part['unityUvChannels'] = mesh.get('unityUvChannels', [])
            part['hasColor'] = mesh.get('hasColor', False)
            if part.get('shader') == 'Endfield/LayeredEffect' and any(
                    value['property'] == '_Model' and value['value'] == 2 for value in part.get('scalars', [])):
                # CameraFacingRibbon的UV5.xyz是camera-relative世界pivot，UV4是向量。
                part['extraPositionUvChannels'] = [5]
        part.setdefault('category', 'Environment' if mesh['renderRole'] == 'environment' else 'Character')
        parts.append(part)
    plan = dict(environment, captureId=capture_id, parts=parts,
                requireRefractionColorTexture=effects.get('requireRefractionColorTexture', False),
                mainLightDirection=lighting['directionTowardLight'],
                mainLightRadiance=lighting['linearRadiance'],
                ambientRadiance=lighting['linearAmbientRadiance'])
    write_json(SOURCE / 'scene-import.json', plan)
    print(capture_id + ' scene-import:', len(parts), 'parts;', len(plan['localLights']), 'Unity local lights')


def run(root, capture_id):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings-only', action='store_true', help='先准备独立相机/灯/后处理配置')
    args = parser.parse_args()
    geometry, environment = prepare_environment(root, capture_id)
    if not args.settings_only:
        build_scene_plan(geometry, environment, root, capture_id)
