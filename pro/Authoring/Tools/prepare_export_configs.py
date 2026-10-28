"""把归档的相对路径导出配置实例化到Work；不打开RDC或执行Unity。"""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[3]
source = Path(__file__).resolve().parent / 'ExtractionConfigs'
destination = root / 'pro/Authoring/Work/ExportConfigs'
destination.mkdir(parents=True, exist_ok=True)
for template in sorted(source.glob('*.json')):
    data = template.read_text(encoding='utf-8').replace('{ROOT}', root.as_posix())
    parsed = json.loads(data)
    path = destination / template.name
    path.write_text(json.dumps(parsed, indent=2), encoding='utf-8')
    print(path)
