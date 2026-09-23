#!/usr/bin/env python3
"""INKWELL UI and file-content regression checks.

Normal mode opens the app on a local HTTP server. `--sandbox` renders local HTML
with page.set_content, replacing storage and download delivery when a managed
browser blocks all navigation. Sandbox mode exercises the real drawing and export
codecs but does NOT prove native persistence, service-worker caching, or OS file
save dialogs. See docs/TEST-REPORT.md for the mode used on this release.

Requires: pip install playwright pillow
          playwright install chromium
Run: python tests/test_inkwell.py [--sandbox] [--browser /path/to/chromium]
"""
from __future__ import annotations
import argparse
import base64
import functools
import http.server
import json
import math
from pathlib import Path
import tempfile
import threading
import xml.etree.ElementTree as ET
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RESULTS: list[str] = []

def check(condition: bool, description: str) -> None:
    if not condition:
        raise AssertionError(description)
    RESULTS.append(description)
    print('PASS', description, flush=True)

MOCK = r"""(seed) => {
 const data = {...seed};
 const storage = {getItem:k=>data[k]??null,setItem:(k,v)=>{data[k]=String(v)},removeItem:k=>{delete data[k]},clear:()=>{for(const k of Object.keys(data))delete data[k]}};
 Object.defineProperty(window,'localStorage',{value:storage,configurable:true});
 window.__storageData=data;
 window.__downloads=[];
 const original = URL.createObjectURL.bind(URL); window.__blobs=new Map();
 URL.createObjectURL = blob => {const url=original(blob);window.__blobs.set(url,blob);return url};
 HTMLAnchorElement.prototype.click = function() { if(this.download)window.__downloads.push({name:this.download,blob:window.__blobs.get(this.href)}); };
 window.print = () => {window.__printCalled=true;};
} """


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--sandbox',action='store_true')
    parser.add_argument('--browser')
    args=parser.parse_args()
    html=(ROOT/'index.html').read_text()
    artifacts=ROOT/'tests'/'artifacts'
    artifacts.mkdir(exist_ok=True)
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}/'
    all_errors=[]
    with sync_playwright() as pw:
        kw={'headless':True,'args':['--no-sandbox']}
        if args.browser: kw['executable_path']=args.browser
        browser=pw.chromium.launch(**kw)
        def boot(width=1440,height=1000,touch=False,seed=None,storage=True):
            context=browser.new_context(viewport={'width':width,'height':height},has_touch=touch,device_scale_factor=1,accept_downloads=True)
            page=context.new_page()
            page.on('pageerror',lambda error:all_errors.append(str(error)))
            if args.sandbox:
                if storage: page.evaluate(MOCK,seed or {})
                page.set_content(html,wait_until='load')
            else:
                page.goto(base,wait_until='load')
            page.wait_for_function('window.Inkwell !== undefined')
            page.evaluate('Inkwell.ready')
            return page,context
        page,context=boot()
        check(page.evaluate('Inkwell.getProject().marks.length')==0,'Initial workspace is blank, not seeded with demo data')
        check(page.evaluate('Inkwell.version')=='1.0.0','Visible version and integration API are present')
        check(page.locator('[data-tool="rect"]').is_hidden(),'Easy mode hides advanced shape tools')
        def world(x,y):
            return page.evaluate('''([x,y])=>{const v=Inkwell.getStatus().view,r=document.getElementById('stage').getBoundingClientRect();return [r.left+v.tx+x*v.scale,r.top+v.ty+y*v.scale]}''',[x,y])
        def draw(points):
            start=world(*points[0]);page.mouse.move(*start);page.mouse.down()
            for x,y in points[1:]: page.mouse.move(*world(x,y))
            page.mouse.up()
        draw([(200+i*10,300+math.sin(i*.2)*65) for i in range(45)])
        mark=page.evaluate('Inkwell.getProject().marks[0]')
        check(mark['type']=='stroke' and len(mark['points'])>30,'Mouse handwriting records a continuous vector stroke')
        check(page.evaluate("document.getElementById('inkCanvas').getContext('2d').getImageData(200,300,1,1).data[3]")>0,'Mouse handwriting paints visible canvas pixels')
        # Active strokes render before pointer-up, without being saved prematurely.
        start=world(300,480);page.mouse.move(*start);page.mouse.down();page.mouse.move(*world(600,480),steps=12);page.wait_for_timeout(50)
        check(page.evaluate("document.getElementById('liveCanvas').getContext('2d').getImageData(450,480,1,1).data[3]")>0,'Live stroke preview is visible before pointer-up')
        page.keyboard.press('Escape');page.mouse.up()
        check(page.evaluate('Inkwell.getProject().marks.length')==1,'Escape cancels the unfinished mark')
        page.locator('#zoomIn').click();zoom=page.evaluate('Inkwell.getStatus().view.scale')
        page.locator('#undoButton').click()
        check(page.evaluate('Inkwell.getProject().marks.length')==0,'Undo removes a committed stroke')
        check(page.evaluate('Inkwell.getStatus().view.scale')==zoom,'Undo preserves the viewport for same-sized sheets')
        page.locator('#redoButton').click()
        check(page.evaluate('Inkwell.getProject().marks.length')==1,'Redo restores a committed stroke')
        page.wait_for_timeout(600)
        check(page.evaluate('!Inkwell.getStatus().dirty'),'Successful autosave changes the state to saved')
        if args.sandbox:
            seed=page.evaluate('window.__storageData')
            restored,restored_ctx=boot(seed=seed)
            check(restored.evaluate('Inkwell.getProject().marks.length')==1,'Autosave serialization restores in a fresh document (storage adapter)')
            restored_ctx.close()
        else:
            page.reload();page.evaluate('Inkwell.ready')
            check(page.evaluate('Inkwell.getProject().marks.length')==1,'Native autosave survives browser reload')
        page.locator('button[data-mode="advanced"]').first.click()
        check(page.locator('[data-tool="rect"]').is_visible(),'Advanced mode reveals shape and text controls')
        page.locator('[data-tool="rect"]').click()
        draw([(800,200),(1000,360)])
        check(page.evaluate('Inkwell.getProject().marks.at(-1).type')=='rect','Rectangle tool commits editable shape geometry')
        page.locator('[data-tool="text"]').click();page.mouse.click(*world(350,600))
        page.locator('#noteText').fill('An <editable> note & label')
        page.locator('#textForm button[type="submit"]').click()
        check(page.evaluate('Inkwell.getProject().marks.at(-1).type')=='text','Typed annotation is placed through its form')
        check(page.evaluate('Inkwell.toSVG().includes("&lt;editable&gt;")'),'SVG escapes text rather than executing markup')
        page.locator('[data-pattern="grid"]').click()
        check(page.evaluate('Inkwell.getProject().paper.pattern')=='grid','Paper guide setting updates the project')
        paper_before=page.evaluate('Inkwell.getProject().paper.color')
        page.evaluate("document.getElementById('themeSelect').value='dark';document.getElementById('themeSelect').dispatchEvent(new Event('change'))")
        check(page.evaluate('document.documentElement.dataset.theme')=='dark' and page.evaluate('Inkwell.getProject().paper.color')==paper_before,'Dark theme does not alter artwork colors')
        page.evaluate("document.getElementById('themeSelect').value='contrast';document.getElementById('themeSelect').dispatchEvent(new Event('change'))")
        check(page.evaluate('document.documentElement.dataset.theme')=='contrast','High-contrast theme activates')
        page.evaluate("document.getElementById('themeSelect').value='light';document.getElementById('themeSelect').dispatchEvent(new Event('change'))")
        # Invalid project validation must be atomic.
        before=page.evaluate('JSON.stringify(Inkwell.getProject())')
        failure=page.evaluate('''()=>{let bad=Inkwell.getProject();bad.schema=99;try{Inkwell.loadProject(bad)}catch(e){return e.message}}''')
        check('Unsupported' in failure and page.evaluate('JSON.stringify(Inkwell.getProject())')==before,'Unsupported schema is rejected without changing the workspace')
        for mutation in ['bad.paper.width=90000','bad.paper.color="url(https://example.invalid)"','bad.marks[0].points[0][0]=Infinity','bad.marks[0].points[0][2]=4','bad.marks[0].type="script"']:
            rejected=page.evaluate(f'()=>{{let bad=Inkwell.getProject();{mutation};try{{Inkwell.validateProject(bad);return false}}catch(e){{return true}}}}')
            check(rejected,f'Import validation rejects {mutation.split("=")[0]} abuse')
        check(page.evaluate('JSON.stringify(Inkwell.getProject())')==before,'All malformed-import checks preserve the current drawing')
        # Known geometry for alpha, erase ordering, cropping, and file signatures.
        fixture=page.evaluate('Inkwell.getProject()')
        fixture['title']='Export validation'
        fixture['paper']={'width':400,'height':300,'color':'#fffdf7','pattern':'blank','spacing':40,'transparent':True}
        fixture['marks']=[
            {'type':'stroke','tool':'pen','color':'#ff0000','width':20,'opacity':1,'points':[[50,150,1],[350,150,1]]},
            {'type':'stroke','tool':'eraser','color':'#000000','width':50,'opacity':1,'points':[[200,100,1],[200,200,1]]},
            {'type':'stroke','tool':'pen','color':'#0000ff','width':10,'opacity':1,'points':[[200,150,1]]},
        ]
        page.evaluate('raw=>Inkwell.loadProject(raw)',fixture)
        check(page.evaluate("document.getElementById('inkCanvas').getContext('2d').getImageData(185,150,1,1).data[3]")==0,'Eraser removes earlier ink to true transparency')
        rgba=page.evaluate("Array.from(document.getElementById('inkCanvas').getContext('2d').getImageData(200,150,1,1).data)")
        check(rgba==[0,0,255,255],'Ink drawn after erasing remains visible')
        page.locator('#exportButton').click()
        page.locator('#exportTransparent').check()
        def export(fmt, name=None):
            page.select_option('#exportFormat',fmt);page.wait_for_timeout(200)
            if args.sandbox:
                page.locator('#downloadImage').click()
                page.wait_for_function('window.__downloads.length>0')
                payload=page.evaluate('''async()=>{const v=window.__downloads.pop();if(!v.blob)throw new Error('Missing export blob');const a=new Uint8Array(await v.blob.arrayBuffer());let s='';for(let i=0;i<a.length;i+=8192)s+=String.fromCharCode(...a.subarray(i,i+8192));return {name:v.name,type:v.blob.type,data:btoa(s)}}''')
                dest=artifacts/(name or payload['name']);dest.write_bytes(base64.b64decode(payload['data']))
                return dest,payload['type']
            with page.expect_download() as event:page.locator('#downloadImage').click()
            download=event.value;dest=artifacts/(name or download.suggested_filename);download.save_as(str(dest));return dest,''
        expected={'png':'PNG','jpeg':'JPEG','webp':'WEBP','bmp':'BMP'}
        for fmt,pilformat in expected.items():
            disabled=page.locator(f'#exportFormat option[value="{fmt}"]').get_attribute('disabled')
            if disabled is not None:
                print('SKIP codec',fmt);continue
            dest,mime=export(fmt)
            with Image.open(dest) as image:
                image.load()
                check(image.format==pilformat and image.size==(400,300),f'{fmt.upper()} output is a genuine decodable {pilformat} file at the selected size')
                rgba=image.convert('RGBA')
                check(rgba.getpixel((200,150))[2]>220,f'{fmt.upper()} preserves later ink inside an erased region')
                if fmt in ['png','webp']:
                    check(rgba.getpixel((185,150))[3]==0 and rgba.getpixel((0,0))[3]==0,f'{fmt.upper()} preserves transparent background and erasing')
                else:
                    check(rgba.getpixel((0,0))[3]==255 and rgba.getpixel((0,0))[0]>245,f'{fmt.upper()} flattens against the paper color, not black')
        svg_path,_=export('svg')
        svg=svg_path.read_text();ET.fromstring(svg)
        check('<mask ' in svg and '<image' not in svg and '<path' in svg,'SVG contains vector paths and eraser masks, not a embedded screenshot')
        # Let the browser itself rasterize SVG and verify masking semantics.
        pixels=page.evaluate('''async(svg)=>{const img=new Image();img.src='data:image/svg+xml;base64,'+btoa(unescape(encodeURIComponent(svg)));await img.decode();const c=document.createElement('canvas');c.width=400;c.height=300;let ctx=c.getContext('2d');ctx.drawImage(img,0,0);return [Array.from(ctx.getImageData(185,150,1,1).data),Array.from(ctx.getImageData(200,150,1,1).data)]}''',svg)
        check(pixels[0][3]==0 and pixels[1]==[0,0,255,255],'Browser-rendered SVG reproduces erasure ordering and transparency')
        page.select_option('#exportCrop','ink');page.locator('#exportPadding').fill('0');page.wait_for_timeout(200)
        cropped,_=export('png','cropped.png')
        with Image.open(cropped) as image:
            check(image.width<400 and image.height<=24,'Crop-to-ink uses actual remaining alpha pixels, not the eraser bounding box')
        page.select_option('#exportScale','2');page.wait_for_timeout(200)
        scaled,_=export('png','scaled.png')
        with Image.open(cropped) as a,Image.open(scaled) as b:
            check(b.size==(a.width*2,a.height*2),'2× export renders to exactly double the pixel dimensions')
        # Print rendering is checked; sandbox substitutes only the OS print dialog.
        page.locator('#printButton').click();page.wait_for_timeout(200)
        check(page.evaluate("document.getElementById('printImage').naturalWidth>0"),'Print / PDF action prepares a decodable artwork image')
        page.locator('#exportDialog [data-close]').click()
        page.locator('#fileButton').click()
        if args.sandbox:
            page.locator('#saveProject').click()
            payload=page.evaluate('''async()=>{const v=window.__downloads.pop();return {name:v.name,text:await v.blob.text()}}''')
            saved=json.loads(payload['text'])
            check(saved['schema']==1 and len(saved['marks'])==3 and payload['name'].endswith('.inkwell.json'),'Editable JSON download retains strokes, paper, and schema')
            (ROOT/'examples'/'export-validation.inkwell.json').write_text(json.dumps(saved,indent=2))
        page.locator('#fileDialog [data-close]').click()
        # JSON import exercises File.text, the actual file input, and confirmation.
        file_content=json.dumps(fixture)
        page.locator('#projectFile').set_input_files({'name':'roundtrip.json','mimeType':'application/json','buffer':file_content.encode()})
        page.wait_for_timeout(150)
        check(page.locator('#confirmDialog').is_visible(),'Opening over an existing drawing requests replacement confirmation')
        page.locator('#confirmAccept').click()
        check(page.evaluate('Inkwell.getProject().title')=='Export validation','JSON file input completes a validated project import')
        page.locator('#projectFile').set_input_files({'name':'broken.json','mimeType':'application/json','buffer':b'{nope'})
        page.wait_for_timeout(100)
        check(page.evaluate('Inkwell.getProject().marks.length')==3 and 'not valid JSON' in page.locator('#toast').inner_text(),'Malformed JSON reports an error without replacing the drawing')
        # Touch via native Chromium touch dispatch, not mouse emulation.
        mobile,mobile_ctx=boot(width=390,height=844,touch=True)
        check(mobile.evaluate('Inkwell.getProject().paper.height>Inkwell.getProject().paper.width'),'New phone workspace uses portrait paper')
        check(mobile.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Phone viewport has no horizontal page overflow')
        cdp=mobile_ctx.new_cdp_session(mobile)
        r=mobile.locator('#sheet').bounding_box();x=r['x']+r['width']*.25;y=r['y']+r['height']*.3
        def touch(kind,points):
            cdp.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':[{'x':xx,'y':yy,'id':i,'radiusX':4,'radiusY':4,'force':.7} for i,xx,yy in points]})
        touch('touchStart',[(1,x,y)])
        for i in range(1,18):touch('touchMove',[(1,x+i*5,y+math.sin(i*.3)*20)])
        touch('touchEnd',[])
        check(mobile.evaluate('Inkwell.getProject().marks.length')==1,'Native touch event sequence draws a finger stroke')
        start_scale=mobile.evaluate('Inkwell.getStatus().view.scale')
        touch('touchStart',[(1,x,y)])
        touch('touchStart',[(1,x,y),(2,x+80,y+80)])
        touch('touchMove',[(1,x-20,y-20),(2,x+110,y+110)])
        touch('touchEnd',[])
        check(mobile.evaluate('Inkwell.getProject().marks.length')==1,'Two-finger navigation cancels the unfinished finger mark')
        check(mobile.evaluate('Inkwell.getStatus().view.scale')>start_scale,'Pinch gesture changes canvas zoom')
        mobile.locator('#inspectorToggle').click()
        check(mobile.locator('#inspector').is_visible(),'Mobile settings open as a usable side panel')
        mobile.locator('button[data-mode="advanced"]').last.click()
        mobile.locator('#penOnlyToggle').check();mobile.locator('#closeInspector').click()
        touch('touchStart',[(1,x,y)]);touch('touchMove',[(1,x+35,y+15)]);touch('touchEnd',[])
        check(mobile.evaluate('Inkwell.getProject().marks.length')==1,'Pen-only mode turns finger input into navigation, not ink')
        mobile.locator('#inspectorToggle').click();mobile.locator('#penOnlyToggle').uncheck();mobile.locator('button[data-mode="easy"]').last.click();mobile.locator('#closeInspector').click()
        mobile.locator('#fitButton').click()
        mobile.screenshot(path=str(ROOT/'docs'/'mobile.png'))
        mobile.locator('#exportButton').click()
        check(mobile.locator('#downloadImage').is_visible() and mobile.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Export dialog fits a phone viewport')
        mobile.screenshot(path=str(ROOT/'docs'/'mobile-export.png'))
        # Physical-pen event properties through PointerEvent (hardware is not tested).
        page.evaluate('''()=>{const s=document.getElementById('stage'),r=s.getBoundingClientRect(),v=Inkwell.getStatus().view;document.querySelector('[data-tool="brush"]').click();const send=(type,x,y,pressure)=>s.dispatchEvent(new PointerEvent(type,{pointerId:41,pointerType:'pen',clientX:r.left+v.tx+x*v.scale,clientY:r.top+v.ty+y*v.scale,pressure,buttons:type==='pointerup'?0:1,button:0,bubbles:true,cancelable:true}));send('pointerdown',50,80,.1);send('pointermove',90,80,.8);send('pointermove',130,80,.9);send('pointerup',160,80,.3);}''')
        brush=page.evaluate('Inkwell.getProject().marks.at(-1)')
        check(brush.get('tool')=='brush' and max(p[2] for p in brush['points'])>min(p[2] for p in brush['points']),'Pen-pressure PointerEvents produce varying brush widths')
        # Native local storage is unavailable in opaque-origin sandbox; failure
        # handling is explicitly tested, not hidden by the normal storage adapter.
        if args.sandbox:
            blocked,blocked_ctx=boot(storage=False)
            blocked.evaluate('Inkwell.loadProject(Inkwell.getSample())');blocked.wait_for_timeout(650)
            check(blocked.evaluate('Inkwell.getStatus().dirty') and 'Not saved' in blocked.locator('#saveStatus').inner_text(),'Blocked storage never falsely reports a successful autosave')
            blocked_ctx.close()
        else:
            page.wait_for_function('document.getElementById("offlineStatus").textContent.includes("cache ready")')
            context.set_offline(True);page.reload();page.evaluate('Inkwell.ready')
            check(page.evaluate('Inkwell.version')=='1.0.0','Service-worker shell reloads while offline')
            context.set_offline(False)
        # Destructive actions provide confirmation and reliable recovery.
        old_count=page.evaluate('Inkwell.getProject().marks.length')
        page.locator('#fileButton').click();page.locator('#clearButton').click()
        check(page.locator('#confirmDialog').is_visible(),'Clear ink requires confirmation')
        page.locator('#confirmAccept').click()
        check(page.evaluate('Inkwell.getProject().marks.length')==0,'Clear ink removes all marks')
        page.locator('#undoButton').click()
        check(page.evaluate('Inkwell.getProject().marks.length')==old_count,'Undo restores the drawing after Clear ink')
        page.locator('#fileButton').click();page.locator('#freshButton').click();page.locator('#confirmAccept').click()
        check(page.evaluate('Inkwell.getProject().marks.length')==0 and page.locator('#undoButton').is_disabled(),'Fresh Start resets the workspace and undo history')
        check(page.evaluate('document.documentElement.dataset.mode')=='easy' and page.evaluate('document.documentElement.dataset.theme')=='light','Fresh Start resets mode and theme preferences')
        mobile.set_viewport_size({'width':320,'height':568})
        check(mobile.evaluate('document.documentElement.scrollWidth<=innerWidth'),'Small 320-pixel phone layout avoids horizontal page overflow')
        # Final screenshots and editable sample.
        page.evaluate('Inkwell.loadProject(Inkwell.getSample())')
        page.locator('button[data-mode="easy"]').first.click()
        page.locator('[data-tool="pen"]').click()
        page.wait_for_timeout(600)
        page.evaluate('document.getElementById("toast").hidden=true')
        page.screenshot(path=str(ROOT/'docs'/'desktop.png'))
        sample=page.evaluate('Inkwell.getProject()')
        (ROOT/'examples'/'a-little-ink.inkwell.json').write_text(json.dumps(sample,indent=2))
        page.locator('#exportButton').click();page.select_option('#exportScale','1');page.select_option('#exportCrop','sheet');page.locator('#exportTransparent').uncheck();page.wait_for_timeout(200)
        page.screenshot(path=str(ROOT/'docs'/'export.png'))
        check(not all_errors,'No uncaught JavaScript errors across the tested workflows')
        report={'version':'1.0.0','mode':'sandbox: real canvas/codecs; mocked storage and file delivery' if args.sandbox else 'native HTTP browser','browser':browser.version,'checks':RESULTS,'uncaught_errors':all_errors,'not_tested':['Physical iPhone/iPad Safari','Physical Android Chrome','Hardware stylus pressure and palm rejection','OS share sheet','OS print dialog']+(['Native durable storage','Service-worker offline reload','Native OS download delivery'] if args.sandbox else [])}
        (artifacts/'results.json').write_text(json.dumps(report,indent=2))
        browser.close()
    server.shutdown()
    print(f'\n{len(RESULTS)} checks passed. Results: {artifacts / "results.json"}')

if __name__=='__main__':main()
