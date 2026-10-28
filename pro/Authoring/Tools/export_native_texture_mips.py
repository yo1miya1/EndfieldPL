"""qrenderdoc内执行：实际静态纹理的全部mip导EXR，不经8位PNG量化。"""
import os, json, hashlib, traceback
from pathlib import Path
import renderdoc as rd

plan = json.loads(Path(os.environ['ENDFIELD_TEXTURE_PLAN']).read_text(encoding='utf-8-sig'))
out = Path(plan['output']); out.mkdir(parents=True, exist_ok=True)
capture = rd.OpenCaptureFile(); controller = None
results = []
try:
    status = capture.OpenFile(plan['capture'], '', None)
    if status != rd.ResultCode.Succeeded: raise RuntimeError(str(status))
    status, controller = capture.OpenCapture(rd.ReplayOptions(), None)
    if controller is None: raise RuntimeError(str(status))
    textures = {int(t.resourceId): t for t in controller.GetTextures()}
    for requested in plan['resources']:
        rid = requested['resourceId']; folder = out / str(rid); folder.mkdir(exist_ok=True)
        try:
            texture = textures[rid]
            if texture.depth > 1 or texture.arraysize > 1:
                raise ValueError('This exporter expects static 2D textures; cubes/volumes have separate whole-resource exporters')
            controller.SetFrameEvent(requested['consumers'][0]['sourceEvent'], True)
            item = dict(requested, width=texture.width, height=texture.height, mipCount=texture.mips,
                        sourceFormat=texture.format.Name(), creationFlags=str(texture.creationFlags),
                        valueEncoding='GPU decoded linear RGBA', rowOrder='D3D top-down; no row flip', mips=[])
            for mip in range(texture.mips):
                path = folder / ('mip-%02d.exr' % mip)
                save = rd.TextureSave(); save.resourceId = texture.resourceId; save.mip = mip
                save.slice.sliceIndex = 0; save.destType = rd.FileType.EXR
                save.alpha = rd.AlphaMapping.Preserve; save.channelExtract = -1; save.typeCast = rd.CompType.Typeless
                controller.SaveTexture(save, str(path))
                if not path.is_file() or not path.stat().st_size: raise RuntimeError('EXR export failed')
                item['mips'].append(dict(level=mip, width=max(1, texture.width >> mip), height=max(1, texture.height >> mip),
                                         path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            (folder / 'export.json').write_text(json.dumps(item, indent=2), encoding='utf-8')
            results.append(dict(resourceId=rid, ok=True))
        except Exception:
            results.append(dict(resourceId=rid, ok=False, error=traceback.format_exc()))
        (out / 'export-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
finally:
    if controller: controller.Shutdown()
    capture.Shutdown()
os._exit(0 if all(r['ok'] for r in results) else 1)
