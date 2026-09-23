/** Offline-shell logic tests, using in-memory Cache/Fetch adapters.
 * Run: node tests/test_service_worker.mjs
 * This tests scope, cache invalidation, and offline fallbacks, not browser
 * registration/installation or durable browser caching.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const scope='https://inkwell.test/tools/inkwell/',prefix='inkwell@'+scope+':';
const cachesByName=new Map(),listeners=new Map();
let offline=false,networkBody=null;
const key=x=>typeof x==='string'?x:x.url;
async function fakeFetch(request){
  if(offline)throw new Error('Offline');
  if(networkBody!==null)return new Response(networkBody,{status:200});
  const url=new URL(key(request));
  let filename=url.pathname.slice(new URL(scope).pathname.length)||'index.html';
  const data=await fs.readFile(path.join(root,filename));
  return new Response(data,{status:200});
}
class TestCache {
  data=new Map();
  async addAll(urls){for(const url of urls)this.data.set(url,await fakeFetch(url));}
  async put(request,response){this.data.set(key(request),response.clone());}
  async match(request){return this.data.get(key(request))?.clone();}
}
const caches={
  async open(name){if(!cachesByName.has(name))cachesByName.set(name,new TestCache());return cachesByName.get(name);},
  async keys(){return [...cachesByName.keys()];},
  async delete(name){return cachesByName.delete(name);},
  async match(request){for(const c of cachesByName.values()){const r=await c.match(request);if(r)return r;}}
};
await caches.open(prefix+'0.9.0');await caches.open('inkwell@https://inkwell.test/other/:0.9.0');
let claimed=false,skipped=false;
const self={registration:{scope},addEventListener:(name,handler)=>listeners.set(name,handler),skipWaiting:async()=>{skipped=true;},clients:{claim:async()=>{claimed=true;}}};
vm.runInNewContext(await fs.readFile(path.join(root,'sw.js'),'utf8'),{self,caches,fetch:fakeFetch,URL,location:{origin:new URL(scope).origin},Promise,console});
async function fire(name,request){
  const waits=[];let response=null;
  const event={request,waitUntil:p=>waits.push(p),respondWith:p=>{response=p;}};
  listeners.get(name)(event);const result=response?await response:null;await Promise.all(waits);return result;
}
let count=0;
function check(value,label){assert.ok(value,label);console.log('PASS',label);count++;}
await fire('install');
check(skipped,'Install precaches all four deployed assets and requests activation');
check(cachesByName.get(prefix+'1.0.0').data.size===4,'Offline shell cache contains the expected four URLs');
await fire('activate');
check(claimed&&!cachesByName.has(prefix+'0.9.0'),'Activation claims clients and removes the old same-scope cache');
check(cachesByName.has('inkwell@https://inkwell.test/other/:0.9.0'),'Activation preserves caches belonging to another deployment');
offline=true;
const home=await fire('fetch',{url:scope,method:'GET',mode:'navigate'});
check((await home.text()).includes('<title>INKWELL'),'Offline root navigation returns the cached app shell');
const fallback=await fire('fetch',{url:scope+'uncached-page',method:'GET',mode:'navigate'});
check((await fallback.text()).includes('window.Inkwell'),'Uncached offline navigation falls back to index.html');
check(await fire('fetch',{url:'https://example.invalid/',method:'GET',mode:'navigate'})===null,'External requests are not intercepted');
check(await fire('fetch',{url:scope,method:'POST',mode:'cors'})===null,'POST requests are not intercepted or cached');
check(await fire('fetch',{url:'https://inkwell.test/other/',method:'GET',mode:'navigate'})===null,'Requests outside the app folder are not intercepted');
offline=false;networkBody='<html>updated shell</html>';
const fresh=await fire('fetch',{url:scope,method:'GET',mode:'navigate'});
check((await fresh.text()).includes('updated shell'),'Online navigation prefers the network response');
offline=true;
const updated=await fire('fetch',{url:scope,method:'GET',mode:'navigate'});
check((await updated.text()).includes('updated shell'),'Updated navigation responses are retained for the next offline visit');
console.log(`\n${count} offline-shell logic checks passed.`);
