#!/usr/bin/env python3
"""Focused INKWELL input regressions in a real Chromium renderer.

Uses set_content and a memory storage adapter for restricted containers; no
native disk persistence or service worker claims. Pointer fault scenarios use
synthetic PointerEvents. The last scenarios use Chromium-native mouse/touch
input. Run with --app to compare another release without modifying that release.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_inkwell import MOCK

ROOT = Path(__file__).resolve().parents[1]
HELPERS = r"""() => {
 window.fire = (type,id,x=200,y=250,extra={},target='stage') => {
   const v=Inkwell.getStatus().view,r=document.getElementById('stage').getBoundingClientRect();
   const init={bubbles:true,cancelable:true,composed:true,pointerId:id,pointerType:'mouse',isPrimary:true,
     buttons:/up|cancel|lostpointercapture/.test(type)?0:1,button:0,pressure:.6,
     clientX:r.left+v.tx+x*v.scale,clientY:r.top+v.ty+y*v.scale,...extra};
   const event=new PointerEvent(type,init);
   if(extra.coalesced==='throw')Object.defineProperty(event,'getCoalescedEvents',{value:()=>{throw Error('Unavailable');}});
   else if(extra.coalesced==='none')Object.defineProperty(event,'getCoalescedEvents',{value:undefined});
   else if(Array.isArray(extra.coalesced))Object.defineProperty(event,'getCoalescedEvents',{value:()=>extra.coalesced.map(([px,py])=>new PointerEvent('pointermove',{...init,clientX:r.left+v.tx+px*v.scale,clientY:r.top+v.ty+py*v.scale}))});
   (target==='window'?window:target==='body'?document.body:document.getElementById(target)).dispatchEvent(event);
 };
 window.marks=()=>Inkwell.getProject().marks;
 window.tap=(id,x=200,y=250,extra={})=>{fire('pointerdown',id,x,y,extra);fire('pointerup',id,x,y,extra);};
 window.start=(id=1,extra={})=>{fire('pointerdown',id,200,250,extra);fire('pointermove',id,250,260,extra);fire('pointermove',id,300,270,extra);};
 window.alpha=(x,y)=>document.getElementById('inkCanvas').getContext('2d').getImageData(x,y,1,1).data[3];
 window.near=(a,b)=>Math.abs(a-b)<.02;
 window.last=()=>marks().at(-1).points.at(-1);
}"""
CASES = [
('A tap paints a visible dot without a move or animation frame', "tap(1);return marks().length===1&&alpha(200,250)>0;"),
('100 rapid mouse strokes all commit independently before animation frames', "for(let i=0;i<100;i++){fire('pointerdown',1,200+i*4,250);fire('pointerup',1,201+i*4,260);}return marks().length===100&&marks().every(m=>m.points.length>=2);"),
('Mouse cancellation retains captured ink without invented cancel coordinates', "start();fire('pointercancel',1,0,0);return marks().length===1&&near(last()[0],300)&&near(last()[1],270)&&alpha(200,250)>0;"),
('Touch cancellation retains captured ink', "start(11,{pointerType:'touch'});fire('pointercancel',11,0,0,{pointerType:'touch'});return marks().length===1&&near(last()[0],300);"),
('Pen cancellation retains captured ink', "start(12,{pointerType:'pen'});fire('pointercancel',12,0,0,{pointerType:'pen'});return marks().length===1&&near(last()[0],300);"),
('Lost capture with no buttons preserves ink once; later up cannot duplicate it', "start();fire('lostpointercapture',1,0,0);fire('pointerup',1,0,0,{},'window');return marks().length===1&&near(last()[0],300);"),
('Lost capture while drawing continues through window move/up listeners', "start();fire('lostpointercapture',1,300,270,{buttons:1});fire('pointermove',1,350,280,{},'body');fire('pointerup',1,400,290,{},'body');return marks().length===1&&near(last()[0],400)&&near(last()[1],290);"),
('Failed pointer capture still receives movement and release outside the stage', "const s=document.getElementById('stage');const old=s.setPointerCapture;s.setPointerCapture=()=>{throw Error('No capture');};start();fire('pointermove',1,350,280,{},'window');fire('pointerup',1,400,290,{},'window');s.setPointerCapture=old;return marks().length===1&&near(last()[0],400);"),
('A new down after a missed up saves the old stroke and starts a separate one', "start();fire('pointerdown',1,600,250);fire('pointermove',1,620,250);fire('pointerup',1,640,250);return marks().length===2&&near(marks()[0].points.at(-1)[0],300)&&near(marks()[1].points[0][0],600);"),
('Mouse hover after a missed release ends ink without a long connecting line', "start();fire('pointermove',1,900,800,{buttons:0,pressure:0});tap(1,600,250);return marks().length===2&&near(marks()[0].points.at(-1)[0],300);"),
('Pen hover after a missed release does not draw phantom ink', "start(12,{pointerType:'pen'});fire('pointermove',12,900,800,{pointerType:'pen',buttons:0,pressure:0});tap(12,600,250,{pointerType:'pen'});return marks().length===2&&near(marks()[0].points.at(-1)[0],300);"),
('A fresh primary touch recovers stale contacts instead of starting a false pinch', "start(11,{pointerType:'touch'});tap(22,600,250,{pointerType:'touch',isPrimary:true});return marks().length===2&&near(marks()[1].points[0][0],600);"),
('A second finger does not erase an already-written first-finger stroke', "start(11,{pointerType:'touch'});fire('pointerdown',22,500,450,{pointerType:'touch',isPrimary:false});fire('pointerup',11,300,270,{pointerType:'touch'});fire('pointerup',22,500,450,{pointerType:'touch',isPrimary:false});return marks().length===1&&near(last()[0],300);"),
('Immediate two-finger navigation discards only its provisional starting dot', "fire('pointerdown',11,200,250,{pointerType:'touch'});fire('pointerdown',22,400,400,{pointerType:'touch',isPrimary:false});fire('pointerup',11,200,250,{pointerType:'touch'});fire('pointerup',22,400,400,{pointerType:'touch',isPrimary:false});return marks().length===0;"),
('Finishing a pinch allows the next one-finger stroke', "fire('pointerdown',11,200,250,{pointerType:'touch'});fire('pointerdown',22,400,400,{pointerType:'touch',isPrimary:false});fire('pointerup',11,200,250,{pointerType:'touch'});fire('pointerup',22,400,400,{pointerType:'touch',isPrimary:false});tap(33,200,250,{pointerType:'touch'});return marks().length===1;"),
('Palm contacts during pen ink cannot put subsequent drawing into gesture lock', "start(12,{pointerType:'pen'});fire('pointerdown',21,500,450,{pointerType:'touch'});fire('pointerdown',22,550,500,{pointerType:'touch',isPrimary:false});fire('pointerup',12,300,270,{pointerType:'pen'});tap(1,600,250);return marks().length===2;"),
('A coalesced-event API error falls back to the dispatched move', "fire('pointerdown',1,200,250);fire('pointermove',1,350,100,{coalesced:'throw'});fire('pointerup',1,500,250);return marks().length===1&&marks()[0].points.length>=3&&marks()[0].points.some(p=>p[1]<200);"),
('An unavailable coalesced-event API still draws', "fire('pointerdown',1,200,250);fire('pointermove',1,350,100,{coalesced:'none'});fire('pointerup',1,500,250);return marks().length===1&&marks()[0].points.length>=3;"),
('Empty coalesced samples fall back to the dispatched move', "fire('pointerdown',1,200,250);fire('pointermove',1,350,100,{coalesced:[]});fire('pointerup',1,500,250);return marks().length===1&&marks()[0].points.length>=3;"),
('Coalesced movement samples preserve a curved path', "fire('pointerdown',1,200,250);fire('pointermove',1,500,250,{coalesced:[[250,100],[350,80],[500,250]]});fire('pointerup',1,550,250);return marks().length===1&&marks()[0].points.length>=5&&marks()[0].points.some(p=>p[1]<150);"),
('Subpixel final movement is retained rather than dropping the endpoint', "fire('pointerdown',1,200,250);fire('pointerup',1,200.1,250.1);return marks().length===1&&marks()[0].points.length===2&&near(last()[0],200.1);"),
('Blur preserves unfinished ink and clears input ownership', "start();window.dispatchEvent(new Event('blur'));tap(1,600,250);return marks().length===2&&near(marks()[0].points.at(-1)[0],300);"),
('Pagehide preserves ink and permits a fresh primary touch', "start(11,{pointerType:'touch'});window.dispatchEvent(new Event('pagehide'));tap(22,600,250,{pointerType:'touch'});return marks().length===2;"),
('Escape still intentionally discards the unfinished stroke', "start();window.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));fire('pointerup',1,300,270);return marks().length===0;"),
('Undo and redo retain their behavior for an interrupted stroke', "start();fire('pointercancel',1,0,0);document.getElementById('undoButton').click();if(marks().length!==0)return false;document.getElementById('redoButton').click();return marks().length===1&&near(last()[0],300);"),
('Eraser interruption preserves the completed part of the erase', "start();fire('pointerup',1,300,270);document.querySelector('[data-tool=eraser]').click();fire('pointerdown',1,200,250);fire('pointermove',1,210,255);fire('pointercancel',1);return marks().length===2&&alpha(200,250)===0;"),
('A stale hand-tool pan does not hijack a new pen stroke', "document.querySelector('[data-tool=hand]').click();fire('pointerdown',1,200,250);document.querySelector('[data-tool=pen]').click();start();fire('pointerup',1,300,270);return marks().length===1&&marks()[0].points.length>=3;"),
('An interrupted shape keeps its known geometry rather than disappearing', "document.querySelector('[data-mode=advanced]').click();document.querySelector('[data-tool=rect]').click();start();fire('pointercancel',1,0,0);return marks().length===1&&marks()[0].type==='rect'&&near(marks()[0].x2,300);"),
]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--app',type=Path,default=ROOT/'index.html')
    ap.add_argument('--browser',default='/usr/bin/chromium')
    ap.add_argument('--output',type=Path,default=ROOT/'tests'/'input-results.json')
    args=ap.parse_args()
    html=args.app.read_text()
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':1400,'height':950},has_touch=True)
        def boot():
            page=context.new_page();errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.evaluate(MOCK,{})
            page.set_content(html,wait_until='load')
            page.evaluate('Inkwell.ready')
            page.evaluate(HELPERS)
            return page,errors
        version='unknown'
        for name,script in CASES:
            page,errors=boot()
            try:
                version=page.evaluate('Inkwell.version')
                value=page.evaluate('()=>{'+script+'}')
                ok=value is True and not errors
                row={'name':name,'passed':ok,'errors':errors}
            except Exception as e:
                row={'name':name,'passed':False,'errors':errors+[str(e)]}
            results.append(row)
            print(('PASS ' if row['passed'] else 'FAIL ')+name,flush=True)
            page.close()
        # Native engine-dispatched mouse input with no testing of synthetic states.
        page,errors=boot()
        r=page.locator('#sheet').bounding_box()
        x=r['x']+r['width']*.2;y=r['y']+r['height']*.3
        for i in range(40):
            page.mouse.move(x+i*5,y);page.mouse.down()
            page.mouse.move(x+i*5+2,y+12);page.mouse.up()
        ok=page.evaluate('marks().length')==40 and not errors
        results.append({'name':'40 native mouse strokes without dropped marks','passed':ok,'errors':errors})
        print(('PASS ' if ok else 'FAIL ')+results[-1]['name'],flush=True)
        page.close()
        page,errors=boot()
        r=page.locator('#sheet').bounding_box()
        x=r['x']+r['width']*.2;y=r['y']+r['height']*.3
        cdp=context.new_cdp_session(page)
        for i in range(25):
            pts=[{'x':x+i*6,'y':y,'id':1,'force':.7,'radiusX':3,'radiusY':3}]
            cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':pts})
            pts[0]['y']=y+12
            cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':pts})
            cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        ok=page.evaluate('marks().length')==25 and not errors
        results.append({'name':'25 native touch strokes without dropped marks','passed':ok,'errors':errors})
        print(('PASS ' if ok else 'FAIL ')+results[-1]['name'],flush=True)
        page.close()
        # Real browser capture release while the primary button is still down.
        page,errors=boot()
        r=page.locator('#sheet').bounding_box()
        x=r['x']+r['width']*.2;y=r['y']+r['height']*.3
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+40,y+20)
        page.evaluate("()=>{const s=document.getElementById('stage');if(s.hasPointerCapture(1))s.releasePointerCapture(1);}")
        page.mouse.move(x+80,y+30);page.mouse.up()
        ok=page.evaluate('marks().length===1&&marks()[0].points.length>=3') and not errors
        results.append({'name':'Native mouse capture loss keeps one continuous stroke','passed':ok,'errors':errors})
        print(('PASS ' if ok else 'FAIL ')+results[-1]['name'],flush=True)
        page.close()
        # Native Chromium touchcancel, rather than dispatchEvent fault injection.
        page,errors=boot();cdp=context.new_cdp_session(page)
        r=page.locator('#sheet').bounding_box()
        x=r['x']+r['width']*.2;y=r['y']+r['height']*.3
        points=[{'x':x,'y':y,'id':1,'force':.7,'radiusX':3,'radiusY':3}]
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':points})
        points[0]['x']=x+70
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':points})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchCancel','touchPoints':[]})
        ok=page.evaluate('marks().length===1&&marks()[0].points.length>=2') and not errors
        results.append({'name':'Native touch cancellation retains the written stroke','passed':ok,'errors':errors})
        print(('PASS ' if ok else 'FAIL ')+results[-1]['name'],flush=True)
        page.close()
        # A genuine second-finger contact after actual first-finger writing.
        page,errors=boot();cdp=context.new_cdp_session(page)
        r=page.locator('#sheet').bounding_box()
        x=r['x']+r['width']*.2;y=r['y']+r['height']*.3
        points=[{'x':x,'y':y,'id':1,'force':.7,'radiusX':3,'radiusY':3}]
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':points})
        points[0]['x']=x+70
        cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':points})
        points.append({'x':x+130,'y':y+80,'id':2,'force':.7,'radiusX':3,'radiusY':3})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':points})
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        ok=page.evaluate('marks().length===1&&marks()[0].points.length>=2') and not errors
        results.append({'name':'Native second-finger contact does not erase existing finger ink','passed':ok,'errors':errors})
        print(('PASS ' if ok else 'FAIL ')+results[-1]['name'],flush=True)
        page.close()
        report={'version':version,'browser':browser.version,'mode':'set_content; real Canvas; memory storage; synthetic fault events plus native Chromium mouse/touch',
                'passed':sum(r['passed'] for r in results),'total':len(results),'checks':results,
                'not_tested':['Physical touchscreens and styluses','Safari and Firefox','Native durable storage','Native service worker installation','OS file dialogs']}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+'\n')
        browser.close()
    print(f"{report['passed']}/{report['total']} passed; {args.output}",flush=True)
    raise SystemExit(0 if report['passed']==report['total'] else 1)

if __name__=='__main__':main()
