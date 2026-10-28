import ctypes as C,pathlib,json,hashlib
root=pathlib.Path('F:/Project/_Game/EndfieldRebuild')
base=root/'pro/Authoring/Extracted/SI1/UIRead'
out=root/'pro/Authoring/Extracted/SI1/UIPrograms';out.mkdir(exist_ok=True)
api=C.CDLL(str(pathlib.Path(__file__).with_name('HLSLDecompiler.dll')))
api.Decompile.argtypes=[C.c_void_p,C.c_int,C.POINTER(C.c_void_p),C.POINTER(C.c_int)];api.Decompile.restype=C.c_int
seen=set();records=[]
for p in sorted((base/'raw/mat').glob('eid-*/draw.json')):
 d=json.loads(p.read_text());e=d['eid']
 if e in [2148,2906]:continue
 shader=d['shaders']['ps'];key=shader['sha1']
 if key in seen:continue
 seen.add(key);data=(base/pathlib.Path(shader['file'].replace('\\','/'))).read_bytes();ptr=C.c_void_p();ln=C.c_int();buf=C.create_string_buffer(data);code=api.Decompile(buf,len(data),C.byref(ptr),C.byref(ln));text=C.string_at(ptr,ln.value).decode('utf-8','replace');
 if ptr.value:C.windll.kernel32.LocalFree.argtypes=[C.c_void_p];C.windll.kernel32.LocalFree(ptr)
 if code:raise RuntimeError(text)
 (out/(key+'.hlsl')).write_text(text);records.append({'eid':e,'sha1':key,'sha256':hashlib.sha256(data).hexdigest()})
(out/'index.json').write_text(json.dumps(records,indent=2));print(records)
