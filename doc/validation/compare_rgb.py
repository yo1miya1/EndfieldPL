"""只比较已保存截图的RGB：丢弃附带alpha，不做透明合成或额外色彩变换。"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
REGIONS = {
    'background_top': [640, 25, 1070, 180],
    'background_left': [80, 180, 620, 470],
    'background_right': [1770, 850, 2460, 1210],
    'platform_left': [80, 1220, 650, 1300],
    'ui_top_left': [20, 20, 320, 150],
    'ui_top_right': [2070, 20, 2550, 140],
    'ui_stats': [2020, 160, 2510, 790],
    'ui_level': [0, 620, 600, 870],
    'ui_footer': [0, 1330, 650, 1440],
    'character_face': [1180, 310, 1440, 600],
    'character_dress': [1120, 730, 1600, 1180],
    'ink_left_stroke': [280, 900, 700, 1190],
    'ink_left_knot': [760, 470, 970, 690],
}

def alpha_info(image):
    if 'A' not in image.getbands(): return None
    alpha = np.asarray(image.getchannel('A'))
    return dict(mean=float(alpha.mean()), median=float(np.median(alpha)), minimum=int(alpha.min()),
                maximum=int(alpha.max()), opaqueFraction=float(np.mean(alpha == 255)),
                belowHalfFraction=float(np.mean(alpha < 128)))

def metric(a, b):
    delta = b.astype(np.float64) - a.astype(np.float64)
    absolute = abs(delta)
    return dict(sourceMeanRGB=a.mean((0,1)).tolist(), unityMeanRGB=b.mean((0,1)).tolist(),
                unityMinusSourceMeanRGB=delta.mean((0,1)).tolist(), maeRGB=absolute.mean((0,1)).tolist(),
                mae=float(absolute.mean()), rmse=float(np.sqrt((delta*delta).mean())),
                p90=float(np.percentile(absolute,90)), within8Fraction=float(np.mean(absolute <= 8)))

def edges(array):
    grey = array.astype(float).mean(2)
    return np.hypot(np.gradient(grey, axis=0), np.gradient(grey, axis=1))

def alignment(a, b):
    # 在局部高通边缘上比较，减小背景/材质亮度对UI位置判断的干扰。
    ea, eb = edges(a), edges(b)
    margin = 7
    ea = ea[margin:-margin,margin:-margin]
    if ea.size == 0 or ea.std() < .01: return None
    ea = ea - ea.mean(); best = None
    for dy in range(-5,6):
        for dx in range(-5,6):
            part = eb[margin+dy:eb.shape[0]-margin+dy,margin+dx:eb.shape[1]-margin+dx]
            part = part-part.mean()
            correlation = float((ea*part).sum() / max(1e-9,np.linalg.norm(ea)*np.linalg.norm(part)))
            if best is None or correlation > best['edgeCorrelation']:
                best = dict(unityOffsetPixels=[dx,dy], edgeCorrelation=correlation)
    return best

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT/'doc/capture/reference/final-with-ui.png')
    parser.add_argument('--unity', type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--skip-ui', action='store_true', help='UI geometry already confirmed; omit repeated UI region statistics')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    output = args.out or ROOT/'doc/validation'/('comparison-'+args.label)
    output.mkdir(parents=True, exist_ok=True)
    original = Image.open(args.source); unity_original = Image.open(args.unity)
    target = unity_original.size
    # source和Unity均为显示编码RGB。convert('RGB')直接移除alpha，不与黑/白底混合。
    source_rgb = original.convert('RGB')
    unity_rgb = unity_original.convert('RGB')
    source_rgb.save(output/'source-original-rgb.png')
    if source_rgb.size != target: source_rgb = source_rgb.resize(target, Image.Resampling.LANCZOS)
    source_rgb.save(output/'source-matched-rgb.png'); unity_rgb.save(output/'unity-rgb.png')
    a, b = np.asarray(source_rgb), np.asarray(unity_rgb)
    width, height = target; side = Image.new('RGB',(width*2,height+32),'white')
    side.paste(source_rgb,(0,32)); side.paste(unity_rgb,(width,32))
    draw = ImageDraw.Draw(side)
    draw.text((12,10),'SOURCE RGB / resized to '+str(target),fill='black')
    draw.text((width+12,10),'UNITY '+args.label+' RGB / native resolution',fill='black')
    side.save(output/'side-by-side-rgb.png')
    difference = np.mean(abs(a.astype(float)-b.astype(float)),axis=2)
    Image.fromarray(np.repeat(np.minimum(255,difference*4).astype('uint8')[:,:,None],3,axis=2)).save(output/'difference-rgb-x4.png')
    report = dict(label=args.label, status='intermediate evidence; not final acceptance',
        source=dict(path=str(args.source),size=list(original.size),sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),alpha=alpha_info(original)),
        unity=dict(path=str(args.unity),size=list(unity_original.size),sha256=hashlib.sha256(args.unity.read_bytes()).hexdigest(),alpha=alpha_info(unity_original)),
        comparisonSize=list(target), sampling='Source RGB resized once with Lanczos. Unity RGB retained at native size. No alignment/warping/color transform/alpha composition.',
        valueUnits='8-bit display RGB code values, not scene-linear irradiance', fullFrame=metric(a,b),regions={})
    for name, box in REGIONS.items():
        if args.skip_ui and name.startswith('ui_'): continue
        x0,y0,x1,y1 = [round(v*target[i%2]/original.size[i%2]) for i,v in enumerate(box)]
        ar, br = a[y0:y1,x0:x1], b[y0:y1,x0:x1]
        data = dict(sourceReferenceBox=box,comparisonBox=[x0,y0,x1,y1],**metric(ar,br))
        if name.startswith('ui_'): data['positionEstimate'] = alignment(ar,br)
        if name.startswith('ink_'):
            masks = [x.mean(2)<120 for x in [ar,br]]
            union = np.logical_or(*masks).sum()
            data['darkMask'] = dict(threshold=120,sourceFraction=float(masks[0].mean()),unityFraction=float(masks[1].mean()),
                intersectionOverUnion=float(np.logical_and(*masks).sum()/max(1,union)),
                caveat='Threshold also responds to tone/coverage; this is not an isolated effect-buffer comparison.')
        report['regions'][name]=data
    (output/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(output=str(output),fullFrameMAE=report['fullFrame']['mae'],regions={k:dict(mae=v['mae'],shift=v.get('positionEstimate')) for k,v in report['regions'].items()}),ensure_ascii=False))

if __name__ == '__main__': main()
