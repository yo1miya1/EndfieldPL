"""Run inside qrenderdoc --python. Offline assets, compute and post-VS evidence.

EF_EXPORT_CONFIG supplies absolute workspace paths. No game process is accessed.
"""

# qrenderdoc 原生离线导出入口：纹理、绑定、CB、状态与 PostVS 均来自指定截帧。
import os, sys, json, traceback, hashlib
from pathlib import Path
import renderdoc as rd

cfg = json.loads(Path(os.environ['EF_EXPORT_CONFIG']).read_text(encoding='utf-8-sig'))
out = Path(cfg['output'])
out.mkdir(parents=True, exist_ok=True)
result = {'ok': False, 'textures': [], 'postvs': [], 'compute': [], 'errors': []}


def note(msg):
    with (out / 'progress.log').open('a', encoding='utf-8') as f:
        f.write(msg + '\n')


def write_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def obj_fields(obj, exclude=()):
    ret = {}
    for name in dir(obj):
        if name.startswith('_') or name in exclude:
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue
        if callable(value):
            continue
        if isinstance(value, (str, int, float, bool)):
            ret[name] = value
        else:
            ret[name] = str(value)
    return ret


def structured(obj, depth=0):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if depth > 8:
        return str(obj)
    if isinstance(obj, (bytes, bytearray)):
        return {'bytes': len(obj)}
    try:
        return [structured(v, depth + 1) for v in obj]
    except TypeError:
        pass
    ret = {}
    if hasattr(obj, 'Name') and callable(obj.Name):
        try:
            ret['name'] = obj.Name()
        except Exception:
            pass
    for name in dir(obj):
        if name.startswith('_') or name in ('this', 'thisown', 'rawBytes', 'reflection'):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue
        if not callable(value):
            ret[name] = structured(value, depth + 1)
    return ret if ret else str(obj)


def save_texture(ctrl, tex, path, kind, mip=0, layer=0):
    desc = rd.TextureSave()
    desc.resourceId = tex.resourceId
    desc.mip = mip
    desc.slice.sliceIndex = layer
    desc.destType = kind
    desc.alpha = rd.AlphaMapping.Preserve
    desc.channelExtract = -1
    desc.typeCast = rd.CompType.Typeless
    status = ctrl.SaveTexture(desc, str(path))
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError('SaveTexture failed: ' + str(status))
    return {
        'path': str(path),
        'bytes': path.stat().st_size,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main():
    cap = rd.OpenCaptureFile()
    controller = None
    try:
        status = cap.OpenFile(cfg['capture'], '', None)
        if status != rd.ResultCode.Succeeded:
            raise RuntimeError('OpenFile ' + str(status))
        status, controller = cap.OpenCapture(rd.ReplayOptions(), None)
        if controller is None:
            raise RuntimeError('OpenCapture ' + str(status))
        textures = {int(t.resourceId): t for t in controller.GetTextures()}
        buffers = {int(b.resourceId): b for b in controller.GetBuffers()}
        resource_names = {str(int(r.resourceId)): r.name for r in controller.GetResources()}
        write_json(out / 'resource-names.json', resource_names)
        if cfg.get('resourceInventory', False):
            write_json(
                out / 'resource-inventory.json',
                [
                    dict(obj_fields(r), resourceId=int(r.resourceId))
                    for r in controller.GetResources()
                ],
            )
            write_json(
                out / 'shader-api-docs.json',
                {
                    name: getattr(controller, name).__doc__
                    for name in ['GetShader', 'GetShaderEntryPoints', 'GetResources']
                },
            )
            write_json(
                out / 'buffer-inventory.json',
                [
                    dict(
                        obj_fields(b),
                        resourceId=int(b.resourceId),
                        creationFlags=str(b.creationFlags),
                    )
                    for b in controller.GetBuffers()
                ],
            )
        if cfg.get('resourceUsage'):
            known_resources = {int(r.resourceId): r.resourceId for r in controller.GetResources()}
            write_json(
                out / 'resource-usage.json',
                {
                    str(rid): structured(controller.GetUsage(known_resources[rid]))
                    for rid in cfg['resourceUsage']
                },
            )
        if cfg.get('allShaderBytecode', False):
            shaders = []
            for resource in controller.GetResources():
                if resource.type != rd.ResourceType.Shader:
                    continue
                entry = {'resourceId': int(resource.resourceId), 'name': resource.name}
                try:
                    entries = controller.GetShaderEntryPoints(resource.resourceId)
                    reflection = controller.GetShader(
                        rd.ResourceId.Null(), resource.resourceId, entries[0]
                    )
                    bytecode = bytes(reflection.rawBytes)
                    sha = hashlib.sha256(bytecode).hexdigest()
                    path = out / 'shaders' / sha / 'source.dxbc'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(bytecode)
                    entry.update(
                        sha256=sha,
                        stage=str(entries[0].stage),
                        bytes=len(bytecode),
                        path=str(path),
                        ok=True,
                    )
                except Exception:
                    entry.update(ok=False, error=traceback.format_exc())
                shaders.append(entry)
            write_json(out / 'all-shaders.json', shaders)
            note('all shaders ' + str(len(shaders)))
        write_json(
            out / 'texture-metadata.json',
            [
                dict(
                    obj_fields(t),
                    resourceId=int(t.resourceId),
                    creationFlags=str(t.creationFlags),
                    format=t.format.Name(),
                )
                for t in textures.values()
            ],
        )
        # 像素探针用于核对导出文件的色彩数值；typeCast 明确区分原视图和线性/整数解释。
        if cfg.get('pixelProbes'):
            probes = []
            for requested in cfg['pixelProbes']:
                controller.SetFrameEvent(requested['eid'], True)
                texture = textures[requested['resourceId']]
                sub = rd.Subresource()
                sub.mip = requested.get('mip', 0)
                sub.slice = requested.get('slice', 0)
                cast = getattr(rd.CompType, requested.get('typeCast', 'Typeless'))
                pixel = controller.PickPixel(texture.resourceId, requested['x'], requested['y'], sub, cast)
                probes.append(dict(requested, format=texture.format.Name(), floatValue=list(pixel.floatValue)))
            write_json(out / 'pixel-probes.json', probes)
        actions = []

        def walk(seq):
            for a in seq:
                actions.append(a)
                walk(a.children)

        walk(controller.GetRootActions())
        by_eid = {a.eventId: a for a in actions}
        if cfg.get('characterShadowAudit', False):
            # 限定审计新增角色阴影链：一次会话内从真实附件和stage marker选择事件。
            stage_markers = {a.customName: a.eventId for a in actions if a.customName in ('GBuffer','Lighting','Transparent','UI','UI.RenderOverlays')}
            actor_maps = {rid for rid, name in resource_names.items() if name == '_CharacterShadowmapTexture'}
            actor_casts = [a for a in actions if a.flags & rd.ActionFlags.Drawcall and str(int(a.depthOut)) in actor_maps]
            body_gbuffer = next(a for a in actions if a.flags & rd.ActionFlags.Drawcall and a.numIndices == 27468 and stage_markers['GBuffer'] < a.eventId < stage_markers['Lighting'])
            body_receiver = next(a for a in actions if a.flags & rd.ActionFlags.Drawcall and a.numIndices == 27468 and stage_markers['Lighting'] < a.eventId < stage_markers['Transparent'])
            body_caster = next(a for a in actor_casts if a.numIndices == 27468)
            selected = [a.eventId for a in actor_casts] + [body_gbuffer.eventId, body_receiver.eventId]
            cfg['graphicsStates'] = list(dict.fromkeys(cfg.get('graphicsStates', []) + selected))
            cfg['graphicsConstants'] = list(dict.fromkeys(cfg.get('graphicsConstants', []) + selected))
            cfg['bindings'] = [body_gbuffer.eventId, body_receiver.eventId]
            cfg['postvs'] = [body_caster.eventId]
            cfg['diagnosticTextures'] = [dict(eid=body_receiver.eventId,resourceName='_CharacterShadowmapTexture',name='character-shadow',rawOnly=True),
                dict(eid=body_receiver.eventId,resourceName='_GBuffer2',name='actor-gbuffer2',rawOnly=True)]
            ui_draws = [a for a in actions if a.flags & rd.ActionFlags.Drawcall and stage_markers['UI'] < a.eventId < stage_markers['UI.RenderOverlays']]
            write_json(out/'character-audit-selection.json',dict(stages=stage_markers,bodyGBuffer=body_gbuffer.eventId,bodyReceiver=body_receiver.eventId,
                bodyCaster=body_caster.eventId,casters=[a.eventId for a in actor_casts],actorMapResources=sorted(actor_maps),
                uiDrawCount=len(ui_draws),uiSourceMeshCount=sum(a.numIndices!=3 for a in ui_draws),uiCompositionCount=sum(a.numIndices==3 for a in ui_draws)))
        write_json(
            out / 'actions.json',
            [obj_fields(a, ('children', 'events', 'parent', 'previous', 'next')) for a in actions],
        )
        # Resolve stable command-buffer marker names to their following draw.
        # This avoids a separate replay just to discover per-capture event IDs.
        named_occurrences = {}
        for index, action in enumerate(actions):
            if not action.customName:
                continue
            for child in actions[index + 1 :]:
                if child.flags & (rd.ActionFlags.Drawcall | rd.ActionFlags.Dispatch):
                    named_occurrences.setdefault(action.customName, []).append(child.eventId)
                    break
                if child.flags & rd.ActionFlags.PopMarker and not cfg.get('ignoreMarkerPop', False):
                    break
        occurrence = cfg.get('markerOccurrence', -1)
        named_draws = {
            name: eids[occurrence]
            for name, eids in named_occurrences.items()
            if -len(eids) <= occurrence < len(eids)
        }
        write_json(out / 'named-draw-occurrences.json', named_occurrences)
        write_json(out / 'named-draws.json', named_draws)
        # 旧离线包装器按精确源码锚点插桩；仅此最小语句块保留原排版。
        # fmt: off
        for key in ['postvs','graphicsStates','bindings','graphicsConstants']:
            resolved=list(cfg.get(key,[]))
            for prefix in cfg.get(key+'Markers',[]):
                matches=[eid for name,eid in named_draws.items() if name.startswith(prefix)]
                if not matches: note('No marker match: '+key+' '+prefix)
                resolved.extend(matches)
            for prefix in cfg.get(key+'AllMarkers',[]):
                resolved.extend(eid for name,eids in named_occurrences.items() if name.startswith(prefix) for eid in eids)
            cfg[key]=list(dict.fromkeys(resolved))
        # fmt: on
        if cfg.get('buffers'):
            buffers = {int(b.resourceId): b for b in controller.GetBuffers()}
            for requested in cfg['buffers']:
                eid = requested.get('eid')
                if eid is None:
                    eid = named_draws[requested['eventMarker']]
                controller.SetFrameEvent(eid, True)
                rid = requested.get('resourceId')
                if rid is None:
                    matches = [
                        int(key)
                        for key, name in resource_names.items()
                        if name == requested['resourceName'] and int(key) in buffers
                    ]
                    if len(matches) != 1:
                        raise ValueError('Buffer name must resolve uniquely: ' + str(requested))
                    rid = matches[0]
                resource = buffers[rid]
                blob = bytes(controller.GetBufferData(resource.resourceId, 0, 0))
                folder = out / 'buffers'
                folder.mkdir(exist_ok=True)
                name = requested.get('name', 'resource-%d' % rid)
                (folder / (name + '.bin')).write_bytes(blob)
                write_json(
                    folder / (name + '.json'),
                    dict(
                        obj_fields(resource),
                        resourceId=rid,
                        eid=eid,
                        bytes=len(blob),
                        sha256=hashlib.sha256(blob).hexdigest(),
                    ),
                )
        for requested in cfg.get('diagnosticTextures', []):
            eid = requested.get('eid')
            if eid is None:
                eid = named_draws[requested['eventMarker']]
            controller.SetFrameEvent(eid, True)
            rid = requested.get('resourceId')
            if rid is None:
                matches = [
                    int(key)
                    for key, name in resource_names.items()
                    if name == requested['resourceName'] and int(key) in textures
                ]
                if len(matches) != 1:
                    raise ValueError('Texture name must resolve uniquely: ' + str(requested))
                rid = matches[0]
            tex = textures[rid]
            folder = out / 'diagnostic-textures'
            folder.mkdir(exist_ok=True)
            path = folder / requested.get('name', str(rid))
            mip = requested.get('mip', 0)
            layer = requested.get('slice', 0)
            if not requested.get('rawOnly', False):
                save_texture(controller, tex, path.with_suffix('.exr'), rd.FileType.EXR, mip, layer)
            if requested.get('png', False):
                save_texture(controller, tex, path.with_suffix('.png'), rd.FileType.PNG, mip, layer)
            subresource = rd.Subresource()
            subresource.mip = mip
            subresource.slice = layer
            raw = bytes(controller.GetTextureData(tex.resourceId, subresource))
            path.with_suffix('.raw').write_bytes(raw)
            write_json(
                path.with_suffix('.json'),
                dict(
                    obj_fields(tex),
                    resourceId=rid,
                    format=tex.format.Name(),
                    bytes=len(raw),
                    eid=eid,
                    mip=mip,
                    slice=layer,
                ),
            )
        for requested in cfg.get('textures', []):
            rid = requested['resourceId']
            tex = textures[rid]
            folder = Path(requested['requestedDirectory'])
            folder.mkdir(parents=True, exist_ok=True)
            entry = {'resourceId': rid, 'creationFlags': str(tex.creationFlags), 'files': []}
            try:
                controller.SetFrameEvent(requested['boundEids'][0], True)
                entry['files'].append(
                    save_texture(controller, tex, folder / 'texture.dds', rd.FileType.DDS, -1, -1)
                )
                floating = 'FLOAT' in tex.format.Name()
                for layer in range(tex.arraysize):
                    ext = 'exr' if floating else 'png'
                    kind = rd.FileType.EXR if floating else rd.FileType.PNG
                    entry['files'].append(
                        save_texture(
                            controller, tex, folder / ('slice-%03d.' % layer + ext), kind, 0, layer
                        )
                    )
                entry['ok'] = True
            except Exception:
                entry['ok'] = False
                entry['error'] = traceback.format_exc()
            write_json(folder / 'export.json', entry)
            result['textures'].append(entry)
            note('texture ' + str(rid) + ' ' + str(entry.get('ok')))
        # fmt: off
        for eid in cfg.get('postvs',[]):
            entry={'eid':eid}; folder=out/'postvs'; folder.mkdir(exist_ok=True)
            try:
                controller.SetFrameEvent(eid,True); pipe=controller.GetPipelineState()
                data=controller.GetPostVSData(0,0,rd.MeshDataStage.VSOut)
                entry['mesh']=obj_fields(data)
                entry['stride']=data.vertexByteStride; entry['byteOffset']=data.vertexByteOffset
                blob=bytes(controller.GetBufferData(data.vertexResourceId,0,0))
                path=folder/('eid-%d.bin'%eid); path.write_bytes(blob)
                entry.update(bytes=len(blob),path=str(path),sha256=hashlib.sha256(blob).hexdigest())
                reflection=pipe.GetShaderReflection(rd.ShaderStage.Vertex)
                entry['signature']=[obj_fields(v) for v in reflection.outputSignature]
                entry['ok']=True
            except Exception: entry['ok']=False; entry['error']=traceback.format_exc()
            result['postvs'].append(entry); note('postvs '+str(eid)+' '+str(entry.get('ok')))
        # fmt: on
        write_json(out / 'postvs' / 'metadata.json', result['postvs'])
        for eid in cfg.get('graphicsStates', []):
            controller.SetFrameEvent(eid, True)
            state = controller.GetD3D11PipelineState()
            write_json(out / 'graphics' / ('eid-%d.json' % eid), structured(state))
            note('graphics ' + str(eid))
        for eid in cfg.get('graphicsConstants', []):
            controller.SetFrameEvent(eid, True)
            pipe = controller.GetPipelineState()
            folder = out / 'graphics-constants' / ('eid-%d' % eid)
            folder.mkdir(parents=True, exist_ok=True)
            blocks = []
            for stage in [rd.ShaderStage.Vertex, rd.ShaderStage.Pixel]:
                reflection = pipe.GetShaderReflection(stage)
                if not reflection:
                    continue
                if cfg.get('graphicsPrograms', False):
                    (folder / (str(stage).split('.')[-1]+'.dxbc')).write_bytes(bytes(reflection.rawBytes))
                for index, block in enumerate(reflection.constantBlocks):
                    bound = pipe.GetConstantBlock(stage, index, 0)
                    desc = bound.descriptor
                    payload = bytes(
                        controller.GetBufferData(desc.resource, desc.byteOffset, desc.byteSize)
                    )
                    path = folder / (str(stage).split('.')[-1] + '-cb-%d.bin' % index)
                    path.write_bytes(payload)
                    # fmt: off
                    blocks.append({'stage':str(stage),'index':index,'block':obj_fields(block,('variables',)),
                        'descriptor':obj_fields(desc),'path':str(path),'bytes':len(payload)})
                    if cfg.get('graphicsConstantLayouts', False):
                        blocks[-1]['variables'] = structured(block.variables)
                    # fmt: on
            write_json(folder / 'metadata.json', blocks)
            note('graphics constants ' + str(eid))
        for eid in cfg.get('bindings', []):
            controller.SetFrameEvent(eid, True)
            pipe = controller.GetPipelineState()
            binding = {'eid': eid, 'stages': {}}
            for stage in [rd.ShaderStage.Vertex, rd.ShaderStage.Pixel, rd.ShaderStage.Compute]:
                if not pipe.GetShader(stage):
                    continue
                stage_info = {}
                for name, getter in [
                    ('readOnly', pipe.GetReadOnlyResources),
                    ('readWrite', pipe.GetReadWriteResources),
                    ('samplers', pipe.GetSamplers),
                ]:
                    try:
                        stage_info[name] = structured(getter(stage, False))
                    except Exception:
                        stage_info[name] = {'error': traceback.format_exc()}
                if cfg.get('graphicsReadBuffers', False):
                    # Preserve each actual descriptor window at its draw. Content
                    # hashes deduplicate shared palettes without assuming that a
                    # resource ID still contains the same bytes at another EID.
                    stage_info['bufferFiles'] = []
                    reflection = pipe.GetShaderReflection(stage)
                    for access in pipe.GetReadOnlyResources(stage, False):
                        desc = access.descriptor
                        rid = int(desc.resource)
                        if rid not in buffers:
                            continue
                        blob = bytes(
                            controller.GetBufferData(desc.resource, desc.byteOffset, desc.byteSize)
                        )
                        sha = hashlib.sha256(blob).hexdigest()
                        path = out / 'graphics-read-buffers' / (sha + '.bin')
                        path.parent.mkdir(exist_ok=True)
                        if not path.exists():
                            path.write_bytes(blob)
                        ordinal = access.access.index
                        resource = reflection.readOnlyResources[ordinal]
                        stage_info['bufferFiles'].append(
                            dict(
                                resourceId=rid,
                                reflectionIndex=ordinal,
                                slot=resource.fixedBindNumber,
                                descriptor=obj_fields(desc),
                                path=str(path),
                                bytes=len(blob),
                                sha256=sha,
                            )
                        )
                binding['stages'][str(stage)] = stage_info
            write_json(out / 'bindings' / ('eid-%d.json' % eid), binding)
            note('bindings ' + str(eid))
        for action in actions:
            if cfg.get('skipCompute', False):
                break
            if not action.flags & rd.ActionFlags.Dispatch:
                continue
            if cfg.get('computeEids') and action.eventId not in cfg['computeEids']:
                continue
            eid = action.eventId
            folder = out / 'compute' / ('eid-%d' % eid)
            folder.mkdir(parents=True, exist_ok=True)
            entry = {'eid': eid, 'dispatch': list(action.dispatchDimension)}
            try:
                controller.SetFrameEvent(eid, True)
                pipe = controller.GetPipelineState()
                stage = rd.ShaderStage.Compute
                sh = pipe.GetShaderReflection(stage)
                bytecode = bytes(sh.rawBytes)
                (folder / 'cs.dxbc').write_bytes(bytecode)
                entry['shaderSha256'] = hashlib.sha256(bytecode).hexdigest()
                entry['threadGroupSize'] = list(sh.dispatchThreadsDimension)
                # Keep effective hardware sampler descriptors with each compute
                # stage; source replacement alone cannot validate Unity binding.
                entry['samplers'] = structured(pipe.GetSamplers(stage, False))
                entry['cbuffers'] = []
                for index, block in enumerate(sh.constantBlocks):
                    cb = pipe.GetConstantBlock(stage, index, 0)
                    desc = cb.descriptor
                    payload = bytes(
                        controller.GetBufferData(desc.resource, desc.byteOffset, desc.byteSize)
                    )
                    file = folder / ('cb-%d.bin' % index)
                    file.write_bytes(payload)
                    entry['cbuffers'].append(
                        dict(
                            index=index,
                            block=obj_fields(block, ('variables',)),
                            descriptor=obj_fields(desc),
                            path=str(file),
                        )
                    )
                entry['resources'] = {}
                for label, getter in [
                    ('read', pipe.GetReadOnlyResources),
                    ('write', pipe.GetReadWriteResources),
                ]:
                    entry['resources'][label] = []
                    for i, res in enumerate(getter(stage, False)):
                        desc = res.descriptor
                        reflection_resources = (
                            sh.readOnlyResources if label == 'read' else sh.readWriteResources
                        )
                        reflection_index = res.access.index
                        reflected = (
                            reflection_resources[reflection_index]
                            if reflection_index < len(reflection_resources)
                            else None
                        )
                        record = {
                            'descriptor': obj_fields(desc),
                            'access': obj_fields(res.access),
                            'viewFormat': desc.format.Name(),
                            'viewFormatDetails': structured(desc.format),
                            'reflectionResource': structured(reflected),
                        }
                        rid = int(desc.resource)
                        record['resourceName'] = resource_names.get(str(rid))
                        record['resourceKind'] = (
                            'texture'
                            if rid in textures
                            else 'buffer' if rid in buffers else 'null' if not rid else 'unknown'
                        )
                        if rid in textures:
                            texture = textures[rid]
                            record['resourceFormat'] = texture.format.Name()
                            record['resourceFormatDetails'] = structured(texture.format)
                            record['resourceShape'] = {
                                field: getattr(texture, field)
                                for field in (
                                    'width',
                                    'height',
                                    'depth',
                                    'dimension',
                                    'arraysize',
                                    'mips',
                                    'msQual',
                                    'msSamp',
                                )
                            }
                            record['resourceTextureType'] = int(texture.type)
                        if rid and rid not in textures:
                            payload = bytes(
                                controller.GetBufferData(
                                    desc.resource, desc.byteOffset, desc.byteSize
                                )
                            )
                            file = folder / ('%s-%d-resource-%d.bin' % (label, i, rid))
                            file.write_bytes(payload)
                            record['path'] = str(file)
                        entry['resources'][label].append(record)
                entry['ok'] = True
            except Exception:
                entry['ok'] = False
                entry['error'] = traceback.format_exc()
            write_json(folder / 'metadata.json', entry)
            result['compute'].append(entry)
            note('compute ' + str(eid) + ' ' + str(entry.get('ok')))
        if cfg.get('referenceMRT'):
            controller.SetFrameEvent(895, True)
            ref = out / 'reference-mrt'
            ref.mkdir(exist_ok=True)
            for rid in [83514, 83484, 83481, 83490, 83487]:
                save_texture(
                    controller, textures[rid], ref / ('resource-%d.exr' % rid), rd.FileType.EXR
                )
        result['ok'] = True
    finally:
        if controller:
            controller.Shutdown()
        cap.Shutdown()


code = 0
try:
    main()
except BaseException:
    result['fatal'] = traceback.format_exc()
    code = 1
write_json(out / 'result.json', result)
note('finished ' + str(result['ok']))
sys.stdout.flush()
sys.stderr.flush()
os._exit(code)
