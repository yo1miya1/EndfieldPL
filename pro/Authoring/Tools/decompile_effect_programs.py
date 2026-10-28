import ctypes as C,pathlib,json
root=pathlib.Path(__file__).resolve().parents[3];base=root/'pro/Authoring/Extracted/SI1';out=base/'EffectsPrograms';out.mkdir(exist_ok=True)
api=C.CDLL(str(root/'tool/rdc2dcc/SI1Scripts/HLSLDecompiler.dll'));api.Decompile.argtypes=[C.c_void_p,C.c_int,C.POINTER(C.c_void_p),C.POINTER(C.c_int)];api.Decompile.restype=C.c_int
for eid in [1554,1571,1589,1607,1625,1649,1672,1693,1712,1730]:
 d=json.loads((base/'EffectsRead/raw/mat'/f'eid-{eid}/draw.json').read_text(encoding='utf-8'));data=(base/'EffectsRead'/pathlib.PureWindowsPath(d['shaders']['ps']['file'])).read_bytes();buf=C.create_string_buffer(data);ptr=C.c_void_p();size=C.c_int();code=api.Decompile(buf,len(data),C.byref(ptr),C.byref(size));text=C.string_at(ptr,size.value).decode('utf-8');
 if ptr.value:C.windll.kernel32.LocalFree.argtypes=[C.c_void_p];C.windll.kernel32.LocalFree(ptr)
 if code:raise RuntimeError(text)
 (out/f'{eid}.hlsl').write_text(text,encoding='utf-8')
print('Saved 10 actual FX PS programs')
