const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),zlib=require('node:zlib');
const {spawnSync}=require('node:child_process'),os=require('node:os');
const {paintScan,png}=require('../examples/scan_fixture.cjs'),{paintCleanupScan}=require('../examples/cleanup_fixture.cjs');
const root=path.join(__dirname,'..'),html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]),box={};vm.createContext(box);
vm.runInContext(scripts[0]+'\nglobalThis.scan=ScanTracer;globalThis.pre=ScanPreprocessor;globalThis.model=TracerModel;',box);
const plain=v=>JSON.parse(JSON.stringify(v)),recognize=(image,options={cleanup:16})=>plain(box.scan.recognize(image,options));
const image=paintCleanupScan(),original=image.data.slice(),draft=recognize(image),prepared=box.pre.prepare(image,{cleanup:16});
assert.deepEqual(image.data,original);assert.deepEqual(recognize(image),draft);
assert.throws(()=>recognize(image,{}),/Komponenten|Fremdpixel/,'cleanup is opt-in');
assert.throws(()=>recognize(image,{cleanup:8}),/Komponenten|Fremdpixel/,'large components stay in the mask');
assert.deepEqual(prepared.image.data,box.pre.prepare(paintScan()).image.data,'only the isolated marks disappear');
const cleanup=draft.recognition.preprocessing.cleanup;
assert.equal(cleanup.removed_pixels,27);assert.equal(cleanup.components.length,3);
assert.equal(cleanup.original_foreground_pixels,draft.recognition.foreground_pixels+27);
assert.deepEqual(plain(box.model.Drawing.load(draft).record(true)),draft);
assert.throws(()=>box.model.Drawing.load(draft).record(),/oberen Strang/);
for(const cleanup of [-1,65,1.5,NaN,true,null])assert.throws(()=>recognize(image,{cleanup}),/Pixelgrenze/);
const records=[];
for(const options of [{},{rotation:Math.PI/2},{rotation:.2},{mirror:true},{radius:1},{radius:5},{kind:'circle'}]){
  const record=recognize(paintCleanupScan(options));
  assert.deepEqual(record.waypoints,recognize(paintScan(options),{}).waypoints);
  const visits=box.model.intersections(record.waypoints).flatMap(c=>c.segments.map(segment=>({c,segment}))).sort((a,b)=>a.segment-b.segment);
  record.crossings=plain(visits.filter((_,i)=>i%2===0).map(({c,segment})=>({coordinate:c.coordinate,over_segment:segment})));delete record.draft;
  records.push(record);
}
for(const options of [{gaps:true},{gaps:true,lineGaps:true}]){
  const record=recognize(paintCleanupScan({gapIndices:[0,2,4],...(options.lineGaps?{lineBreaks:[0]}:{})}),{cleanup:16,...options});
  assert.equal(record.recognition.inferred_crossings,3);assert.equal(record.recognition.preprocessing.cleanup.removed_pixels,27);
  assert.deepEqual(plain(box.model.Drawing.load(record).record()),record);records.push(record);
}
const rotated={...image,data:image.data.slice()};
for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++)rotated.data.set(image.data.subarray(4*(y*image.width+x),4*(y*image.width+x)+4),4*(x*image.width+image.width-1-y));
assert.equal(recognize(rotated).recognition.preprocessing.cleanup.removed_pixels,27,'rotate the actual ink and marks');
const transparent={...image,data:image.data.slice()};for(let i=3;i<transparent.data.length;i+=4)transparent.data[i]=0;
assert.throws(()=>recognize(transparent),/Keine kontrastreiche/);
// Adversarial mask cases test the isolation rule independently of the curve.
function mask(w=120,h=120){const data=new Uint8ClampedArray(w*h*4);data.fill(255);return {width:w,height:h,data};}
function ink(image,x,y,w=1,h=1){for(let yy=y;yy<y+h;yy++)for(let xx=x;xx<x+w;xx++)image.data.set([0,0,0,255],4*(yy*image.width+xx));}
const near=mask();ink(near,40,40,1,60);ink(near,45,40);assert.throws(()=>box.pre.prepare(near,{cleanup:16}),/zu nah/);
const pair=mask();ink(pair,90,20,1,60);ink(pair,20,20);ink(pair,25,20);assert.throws(()=>box.pre.prepare(pair,{cleanup:16}),/zu nah/);
const edge=mask();ink(edge,90,20,1,60);ink(edge,0,20);assert.throws(()=>box.pre.prepare(edge,{cleanup:16}),/Bildrand/);
const all=mask();ink(all,20,20);assert.throws(()=>box.pre.prepare(all,{cleanup:16}),/kein verbleibender/);
const many=mask(1200,100);ink(many,1100,20,1,60);for(let i=0;i<33;i++)ink(many,20+20*i,20);assert.throws(()=>box.pre.prepare(many,{cleanup:16}),/32 kleine/);
const total=mask(1200,100);ink(total,1100,20,1,70);for(let i=0;i<17;i++)ink(total,20+30*i,20,8,8);assert.throws(()=>box.pre.prepare(total,{cleanup:64}),/zu viele/);
const diagonal=mask();ink(diagonal,90,20,1,70);ink(diagonal,20,20);ink(diagonal,21,21);
assert.equal(box.pre.prepare(diagonal,{cleanup:2}).report.cleanup.components[0].pixels,2,'8-connected diagonal ink forms one component');
const exact=mask();ink(exact,40,20,1,70);ink(exact,28,20);assert.equal(box.pre.prepare(exact,{cleanup:1}).report.cleanup.removed_pixels,1);
const connected=mask();ink(connected,40,20,1,70);ink(connected,41,20);assert.equal(box.pre.prepare(connected,{cleanup:16}).report.cleanup.removed_pixels,0);
assert.throws(()=>recognize(paintScan({open:true})),/Offene|Lücke/,'cleanup does not close gaps');
// Exercise actual encoded PNG pixels.
const bytes=png(image),parts=[];
for(let i=8;i<bytes.length;){const n=bytes.readUInt32BE(i);if(bytes.toString('ascii',i+4,i+8)==='IDAT')parts.push(bytes.subarray(i+8,i+8+n));i+=n+12;}
const raw=zlib.inflateSync(Buffer.concat(parts)),data=new Uint8ClampedArray(image.data.length);
for(let y=0;y<image.height;y++){assert.equal(raw[y*(image.width*4+1)],0);data.set(raw.subarray(y*(image.width*4+1)+1,(y+1)*(image.width*4+1)),y*image.width*4);}
assert.deepEqual(recognize({...image,data}),draft);
const invalid=[null,{}, {...cleanup,algorithm:'unknown'}, {...cleanup,max_area:true}, {...cleanup,max_area:65},
  {...cleanup,clearance:11},{...cleanup,removed_pixels:26},{...cleanup,original_foreground_pixels:0},
  {...cleanup,components:[{bounds:[0,20,2,22],pixels:9}]},
  {...cleanup,components:cleanup.components.map((e,i)=>i?e:{...e,pixels:true})},
  {...cleanup,components:cleanup.components.map((e,i)=>i?e:{...e,bounds:[20,20,20,20]})},
  {...cleanup,components:[cleanup.components[0],cleanup.components[0],cleanup.components[0]]}];
const invalidRecords=invalid.map(cleanup=>({...draft,recognition:{...draft.recognition,preprocessing:{...draft.recognition.preprocessing,cleanup}}}));
for(const r of invalidRecords)assert.throws(()=>box.model.Drawing.load(r),/Bereinigungsbericht/);
const tempRoot=fs.realpathSync(os.tmpdir()),directory=fs.mkdtempSync(path.join(tempRoot,'knots-cleanup-'));
try{
  fs.writeFileSync(path.join(directory,'records.json'),JSON.stringify(records));fs.writeFileSync(path.join(directory,'invalid.json'),JSON.stringify(invalidRecords));
  const result=spawnSync('python',['-c',`
import json,sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict,annotation_to_dict,trace_annotation,write_traced_diagram
from knots_grid.validator import validate_cycle
from knots_grid.core import trace_turtle
from knots_grid.classification import classify_knot
root=Path(sys.argv[1]);records=json.loads((root/'records.json').read_text())
for record in records:
    annotation=annotation_from_dict(record)
    assert annotation_to_dict(annotation)==record
    trace=trace_annotation(annotation)
    assert validate_cycle(trace.points).is_valid
    assert trace_turtle(trace.code).points==trace.points
    assert classify_knot(trace.points).determinant==(3 if record['crossings'] else 1)
for record in json.loads((root/'invalid.json').read_text()):
    try: annotation_from_dict(record)
    except ValueError as error: assert 'scan cleanup' in str(error)
    else: raise AssertionError('invalid report accepted')
write_traced_diagram(annotation_from_dict(records[0]),root/'gallery')
assert json.loads((root/'gallery'/'trace.json').read_text())['annotation']==records[0]
assert 'Entfernte Fremdkomponenten' in (root/'gallery'/'index.html').read_text(encoding='utf8')
print('Cleanup: pixel cases, JS/Python reports, valid grid, exact turtle roundtrip and export passed.')
`,directory],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);process.stdout.write(result.stdout);
  const gallery=spawnSync('node',[path.join(__dirname,'test_gallery_runtime.cjs'),path.join(directory,'gallery/index.html')],{encoding:'utf8'});assert.equal(gallery.status,0,gallery.stdout+gallery.stderr);
}finally{assert.equal(path.dirname(fs.realpathSync(directory)),tempRoot);fs.rmSync(directory,{recursive:true,force:true});}
async function testUI(){
  const elements={};let current=image,downloaded,rectangles=0;
  class Element{
    constructor(id){this.value=({spacing:'24','origin-x':'0','origin-y':'0',threshold:'160','scan-radius':'24','scan-contrast':'30','scan-cleanup':'0'})[id]??'';this.checked=id==='show-image';this.width=560;this.height=560;this.listeners={};this.dataset={};}
    addEventListener(n,f){this.listeners[n]=f;}setAttribute(n,v){this[n]=v;}getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
    getContext(){return new Proxy({getImageData:()=>current,createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),strokeRect:()=>rectangles++},{get:(t,k)=>t[k]??(()=>{})});}
    fire(n,p={}){return this.listeners[n]?.(p);}click(){}
  }
  for(const m of html.matchAll(/\bid="([^"]+)"/g))elements[m[1]]=new Element(m[1]);
  Object.assign(box,{document:{getElementById:id=>elements[id],createElement:()=>new Element('')},Blob:class{constructor(parts){downloaded=parts.join('');}},
    Image:class{constructor(){this.naturalWidth=560;this.naturalHeight=560;}set src(v){this.onload();}},URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},setTimeout:fn=>fn()});
  vm.runInContext(scripts[1],box);elements.image.files=[{name:'marked_scan.png'}];elements.image.fire('change');
  elements['scan-recognize'].fire('click');assert.equal(elements.status.dataset.error,'true');
  elements['scan-cleanup'].value='16';elements['scan-cleanup'].fire('change');elements['scan-preview'].fire('click');
  assert.equal(elements.status.dataset.error,'false');assert.match(elements.status.textContent,/3 Fremdkomponenten/);assert.equal(rectangles,3);assert.equal(elements.draft.disabled,true);
  elements['scan-recognize'].fire('click');assert.equal(elements.status.dataset.error,'false');elements.draft.fire('click');const saved=JSON.parse(downloaded);
  assert.deepEqual(saved.recognition.preprocessing.cleanup,cleanup);
  current=near;elements['scan-recognize'].fire('click');assert.equal(elements.status.dataset.error,'true');elements.draft.fire('click');assert.deepEqual(JSON.parse(downloaded),saved);
  elements['scan-cleanup'].value='65';elements['scan-preview'].fire('click');assert.equal(elements.status.dataset.error,'true');
  elements.import.files=[{text:async()=>JSON.stringify(saved)}];await elements.import.fire('change');assert.equal(Number(elements['scan-cleanup'].value),16);
  for(const c of box.model.intersections(saved.waypoints))elements.scene.fire('click',{clientX:c.coordinate[0]*3,clientY:-c.coordinate[1]*3});
  elements.download.fire('click');assert.deepEqual(JSON.parse(downloaded).recognition.preprocessing.cleanup,cleanup);
  elements.spacing.value='2';elements.spacing.fire('change');elements.download.fire('click');assert.equal(JSON.parse(downloaded).recognition,undefined);
  console.log('Cleanup UI: opt-in, marked preview, recognition, failure recovery, import, choices and provenance invalidation passed.');
}
testUI().catch(error=>{console.error(error);process.exitCode=1;});
