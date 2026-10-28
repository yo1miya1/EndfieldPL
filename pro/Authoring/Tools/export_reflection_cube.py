"""在qrenderdoc内执行：保存源Cube全部face/mip，保持D3D切片序与解码精度。"""
import renderdoc as rd
from pathlib import Path
import json,os,hashlib

root=Path(os.environ['ENDFIELD_ROOT'])
out=root/'pro/Authoring/Extracted/SI1/EnvironmentReflection/11550'
capture=Path(os.environ.get('ENDFIELD_SOURCE_CAPTURE',str(root/'pro/Authoring/Work/SI1.rdc')))
cap=rd.OpenCaptureFile();status=cap.OpenFile(str(capture),'',None)
if status!=rd.ResultCode.Succeeded:raise RuntimeError(str(status))
status,controller=cap.OpenCapture(rd.ReplayOptions(),None)
if controller is None:raise RuntimeError(str(status))
try:
    controller.SetFrameEvent(1122,True)
    texture=next(t for t in controller.GetTextures() if int(t.resourceId)==11550)
    entries=[]
    for face in range(6):
        folder=out/('face-%d'%face);folder.mkdir(parents=True,exist_ok=True)
        for mip in range(texture.mips):
            path=folder/('mip-%02d.exr'%mip)
            save=rd.TextureSave();save.resourceId=texture.resourceId;save.mip=mip;save.slice.sliceIndex=face
            save.destType=rd.FileType.EXR;save.alpha=rd.AlphaMapping.Preserve;save.channelExtract=-1;save.typeCast=rd.CompType.Float
            controller.SaveTexture(save,str(path))
            entries.append(dict(face=face,mip=mip,width=max(1,texture.width>>mip),height=max(1,texture.height>>mip),path=path.relative_to(out).as_posix(),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (out/'all-mips.json').write_text(json.dumps(dict(resourceId=11550,eventId=1122,format=texture.format.Name(),mips=texture.mips,faces=6,faceOrder=['+X','-X','+Y','-Y','+Z','-Z'],coordinateConversionApplied=False,files=entries),indent=2),encoding='utf-8')
finally:
    controller.Shutdown();cap.Shutdown()
os._exit(0)
