"""创建独立ASCII回放副本，逐字节哈希验证；原RDC始终只读。"""
from pathlib import Path
import hashlib, json, shutil

root = Path(__file__).resolve().parents[3]
source = root / 'src/SI-1.rdc'
destination = root / 'pro/Authoring/Work/SI1.rdc'
expected = 'e2c40a194bf57fe4827aa631a4a50562c792258a2007819d2c1d3f6745ef3bec'

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()

destination.as_posix().encode('ascii')
actual = digest(source)
if actual != expected:
    raise ValueError('输入并非已归档SI-1截帧：' + actual)
destination.parent.mkdir(parents=True, exist_ok=True)
if not destination.exists():
    shutil.copyfile(source, destination)
if destination.samefile(source) or digest(destination) != actual:
    raise ValueError('工作副本不是独立且内容相同的文件')
manifest = dict(source=source.relative_to(root).as_posix(), workCopy=destination.relative_to(root).as_posix(),
                bytes=source.stat().st_size, sha256=actual, sourceReadOnly=True)
(destination.parent / 'capture-integrity.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(destination)
