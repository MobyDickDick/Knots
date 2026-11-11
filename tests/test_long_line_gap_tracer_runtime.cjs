const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),os=require('node:os'),zlib=require('node:zlib');
const {spawnSync}=require('node:child_process');
const {paintCurve}=require('../examples/curve_fixture.cjs'),{paintScan}=require('../examples/scan_fixture.cjs');
const {paintCleanupScan}=require('../examples/cleanup_fixture.cjs');
const root=path.join(__dirname,'..'),html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]),box={};vm.createContext(box);
vm.runInContext(scripts[0]+';globalThis.curve=CurveTracer;globalThis.scan=ScanTracer;globalThis.model=TracerModel;',box);
const plain=v=>JSON.parse(JSON.stringify(v)),fixture=options=>paintCurve({straightBreak:true,lineGapHalf:22,lineBreaks:[0],gapIndices:[0,2,4],...options});
const recognize=image=>plain(box.curve.recognize(image,{gaps:true,lineGaps:true,maxLineGap:64}));
const image=fixture(),original=image.data.slice(),record=recognize(image),cases=[];
// Exact pixel distances, including the switch from legacy to extended rules.
function brokenRectangle(distance,start=170){
  const image={width:400,height:400,data:new Uint8ClampedArray(400*400*4)};image.data.fill(255);
  const ink=(x,y)=>image.data.set([0,0,0,255],4*(y*400+x));
  for(let x=50;x<=350;x++){ink(x,50);ink(x,350);}
  for(let y=50;y<=350;y++){ink(50,y);if(y<=start||y>=start+distance)ink(350,y);}
  return image;
}
for(const distance of [32,33,64]){
  const image=brokenRectangle(distance),r=recognize(image),e=r.recognition.line_gaps.evidence[0];
  assert.equal(e.added_pixels,distance-1);cases.push({record:r,name:'0_1'});
  if(distance>32)assert.throws(()=>box.curve.recognize(image,{lineGaps:true}),/Lücke/);
  else assert.ok(box.curve.recognize(image,{lineGaps:true}));
}
assert.throws(()=>recognize(brokenRectangle(65)),/Lücke/);
assert.throws(()=>recognize(brokenRectangle(64,70)),/Lücke/,'long evidence arms cannot turn around a corner');
function twoLongGaps(separation){
  const image={width:400,height:400,data:new Uint8ClampedArray(400*400*4)};image.data.fill(255);
  const ink=(x,y)=>image.data.set([0,0,0,255],4*(y*400+x));
  for(let x=150;x<=150+separation;x++){ink(x,50);ink(x,350);}
  for(let y=50;y<=350;y++)if(y<=170||y>=234){ink(150,y);ink(150+separation,y);}
  return image;
}
assert.throws(()=>recognize(twoLongGaps(87)),/nahe/,'two radius-44 protection disks must not overlap');
const separated=recognize(twoLongGaps(88));assert.equal(separated.recognition.line_gaps.evidence.length,2);
cases.push({record:separated,name:'0_1'});

assert.equal(record.recognition.line_gaps.algorithm,'local-line-gaps-v2');
assert.equal(record.recognition.line_gaps.max_distance,64);
assert.throws(()=>box.curve.recognize(image,{gaps:true,lineGaps:true}),/Lücke/,'long gaps require explicit opt-in');
for(const maxLineGap of [0,33,65,true,'64',null,Infinity])assert.throws(()=>box.curve.recognize(image,{lineGaps:true,maxLineGap}),/Grenze/);
for(const options of [{lineGapHalf:15},{lineGapHalf:26},{alpha:220}]){
  const r=recognize(fixture(options)),e=r.recognition.line_gaps.evidence[0];
  const distance=Math.hypot(e.endpoints[0][0]-e.endpoints[1][0],e.endpoints[0][1]-e.endpoints[1][1]);
  assert.ok(distance>32&&distance<=64);cases.push({record:r,name:'T(2,3)'});
}
const boundary=recognize(fixture({lineGapHalf:26})).recognition.line_gaps.evidence[0].endpoints;
assert.equal(Math.hypot(boundary[0][0]-boundary[1][0],boundary[0][1]-boundary[1][1]),64);
assert.throws(()=>recognize(fixture({straightBreak:false})),/Lücke/,'curved arms do not justify a long straight bridge');
const legacy=plain(box.curve.recognize(paintCurve({lineBreaks:[0],gapIndices:[0,2,4]}),{gaps:true,lineGaps:true}));
assert.equal(legacy.recognition.line_gaps.algorithm,'local-line-gaps-v1');
assert.equal(legacy.recognition.line_gaps.max_distance,undefined);
assert.deepEqual(plain(box.model.Drawing.load(legacy).record()),legacy);

assert.deepEqual(image.data,original);assert.deepEqual(recognize(image),record);
assert.equal(record.recognition.line_gaps.evidence.length,1);assert.equal(record.recognition.inferred_crossings,3);
assert.deepEqual(plain(box.model.Drawing.load(record).record()),record);
assert.throws(()=>box.curve.recognize(image,{gaps:true}),/Lücke/,'AP-06 still rejects ordinary breaks');
assert.throws(()=>box.curve.recognize(image,{lineGaps:true}),/Lücke/,'line-only API never guesses an underpass');
for(const options of [{},{rotation:Math.PI/2},{rotation:Math.PI},{rotation:3*Math.PI/2},{rotation:.2},{mirror:true},{radius:2},{radius:5}]){
  const r=recognize(fixture(options));assert.equal(r.recognition.line_gaps.evidence.length,options.lineBreaks?.length??1);
  assert.equal(r.recognition.inferred_crossings,3);assert.deepEqual(plain(box.model.Drawing.load(r).record()),r);
  cases.push({record:r,name:options.mirror?'mirror(T(2,3))':'T(2,3)'});
}
const scan=plain(box.scan.recognize(paintScan({straightBreak:true,lineGapHalf:22,lineBreaks:[0],gapIndices:[0,2,4]}),{gaps:true,lineGaps:true,maxLineGap:64}));
assert.ok(scan.recognition.preprocessing);assert.equal(scan.recognition.line_gaps.evidence.length,1);cases.push({record:scan,name:'T(2,3)'});
const cleaned=plain(box.scan.recognize(paintCleanupScan({straightBreak:true,lineGapHalf:22,lineBreaks:[0],gapIndices:[0,2,4]}),{gaps:true,lineGaps:true,maxLineGap:64,cleanup:16}));
assert.equal(cleaned.recognition.preprocessing.cleanup.removed_pixels,27);
assert.equal(cleaned.recognition.line_gaps.max_distance,64);cases.push({record:cleaned,name:'T(2,3)'});
const circle=plain(box.curve.recognize(paintCurve({kind:'circle',lineBreaks:[0]}),{lineGaps:true}));
assert.equal(circle.recognition.inferred_crossings,0);assert.equal(circle.recognition.line_gaps.evidence.length,1);cases.push({record:circle,name:'0_1'});
const draft=recognize(fixture({gapIndices:[]}));assert.equal(draft.recognition.unresolved_crossings,3);assert.equal(draft.draft,true);
assert.throws(()=>box.model.Drawing.load(draft).record(),/oberen Strang/);
const solid=recognize(paintCurve());assert.equal(solid.recognition.line_gaps.evidence.length,0);assert.equal(solid.recognition.inferred_crossings,0);
for(const bad of [fixture({lineGapHalf:30}),fixture({lineGapHalf:2}),fixture({open:true}),fixture({lineBreaks:[0,.1]})])
  assert.throws(()=>recognize(bad),/Lücke|Kreuzung|Offene/);
// A third stroke, isolated ink or branch near a gap must not disappear in thinning.
const endpoints=record.recognition.line_gaps.evidence[0].endpoints,center=endpoints[0].map((v,k)=>Math.round((v+endpoints[1][k])/2));
for(const kind of ['pixel','stroke','island']){
  const bad=fixture();
  if(kind==='pixel')bad.data.set([0,0,0,255],4*((center[1]+6)*bad.width+center[0]+8));
  if(kind==='stroke')for(let x=center[0]-8;x<=center[0]+8;x++)bad.data.set([0,0,0,255],4*(center[1]*bad.width+x));
  if(kind==='island')for(let y=center[1]-1;y<=center[1]+1;y++)for(let x=center[0]-1;x<=center[0]+1;x++)bad.data.set([0,0,0,255],4*(y*bad.width+x));
  assert.throws(()=>recognize(bad),/Lücke|Fremdpixel|isolierte|Komponenten|Kreuzung/);
}
const invalid=[];
function badReport(patch){const r=plain(record);Object.assign(r.recognition.line_gaps,patch);invalid.push(r);}
badReport({algorithm:'unknown'});badReport({algorithm:'local-line-gaps-v1'});badReport({max_distance:undefined});badReport({max_distance:true});badReport({max_distance:65});badReport({evidence:null});badReport({evidence:Array(21).fill(record.recognition.line_gaps.evidence[0])});
badReport({evidence:[...record.recognition.line_gaps.evidence,...record.recognition.line_gaps.evidence]});
for(const patch of [{added_pixels:true},{added_pixels:129},{added_pixels:2},{endpoints:null},{endpoints:[[1,1],[2,2]]},{endpoints:[[0,0],[65,0]]},{endpoints:[[560,1],[560,20]]},{endpoints:[[true,0],[20,0]]}]){
  const r=plain(record);Object.assign(r.recognition.line_gaps.evidence[0],patch);invalid.push(r);
}
for(const patch of [{line_gaps:null},{unresolved_crossings:1},{algorithm:'grid-sampling-v1'}]){
  const r=plain(record);Object.assign(r.recognition,patch);invalid.push(r);
}
const reused=plain(record);reused.recognition.line_gaps.evidence[0].endpoints=reused.recognition.crossing_gaps.evidence[0].endpoints;invalid.push(reused);
invalid.push({...record,editor_view:null});for(const bad of invalid)assert.throws(()=>box.model.Drawing.load(bad),/Bericht/);
// Decode stored PNG bytes independently of the fixture painter.
function readPNG(filename){
  const bytes=fs.readFileSync(filename),parts=[];assert.equal(bytes[24],8);assert.equal(bytes[25],6);
  for(let i=8;i<bytes.length;){const n=bytes.readUInt32BE(i);if(bytes.toString('ascii',i+4,i+8)==='IDAT')parts.push(bytes.subarray(i+8,i+8+n));i+=n+12;}
  const width=bytes.readUInt32BE(16),height=bytes.readUInt32BE(20),raw=zlib.inflateSync(Buffer.concat(parts)),data=new Uint8ClampedArray(width*height*4);
  for(let y=0;y<height;y++){assert.equal(raw[y*(width*4+1)],0);data.set(raw.subarray(y*(width*4+1)+1,(y+1)*(width*4+1)),y*width*4);}return {width,height,data};
}
assert.deepEqual(recognize(readPNG(path.join(root,'examples/long_line_gap_trace/interrupted_trefoil.png'))),record);
const tempRoot=fs.realpathSync(os.tmpdir()),directory=fs.mkdtempSync(path.join(tempRoot,'knots-long-line-gaps-'));
try{
  for(const [name,value] of [['cases',cases],['invalid',invalid],['draft',draft]])fs.writeFileSync(path.join(directory,name+'.json'),JSON.stringify(value));
  const result=spawnSync('python',['-c',`
import json,sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict,annotation_to_dict,trace_annotation,write_traced_diagram
from knots_grid.validator import validate_cycle
from knots_grid.core import trace_turtle
from knots_grid.classification import classify_knot
root=Path(sys.argv[1]);cases=json.loads((root/'cases.json').read_text())
for case in cases:
    record=case['record'];annotation=annotation_from_dict(record)
    assert annotation_to_dict(annotation)==record
    trace=trace_annotation(annotation)
    assert validate_cycle(trace.points).is_valid
    assert trace_turtle(trace.code).points==trace.points
    assert classify_knot(trace.points).name==case['name']
for bad in json.loads((root/'invalid.json').read_text()):
    try: annotation_from_dict(bad)
    except ValueError: pass
    else: raise AssertionError(bad)
try: write_traced_diagram(annotation_from_dict(json.loads((root/'draft.json').read_text())),root/'invalid')
except ValueError: pass
else: raise AssertionError('unresolved draft exported')
assert not (root/'invalid').exists()
write_traced_diagram(annotation_from_dict(cases[0]['record']),root/'gallery')
metadata=json.loads((root/'gallery'/'trace.json').read_text())
assert metadata['source']=='reviewed_line_gap_annotation'
assert metadata['annotation']==cases[0]['record']
print('Long line gaps: pixel evidence, rotations, mirror, unknot/trefoil, drafts, report validation, provenance and exact Turtle roundtrip passed.')
`,directory],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);process.stdout.write(result.stdout);
  const gallery=spawnSync('node',[path.join(__dirname,'test_gallery_runtime.cjs'),path.join(directory,'gallery/index.html')],{encoding:'utf8'});
  assert.equal(gallery.status,0,gallery.stdout+gallery.stderr);
  const exported=fs.readFileSync(path.join(directory,'gallery/index.html'),'utf8');assert.match(exported,/reviewed_line_gap_annotation/);assert.match(exported,/Ergänzte Linienlücken/);
}finally{assert.equal(path.dirname(fs.realpathSync(directory)),tempRoot);fs.rmSync(directory,{recursive:true,force:true});}
async function testUI(){
  const elements={};let downloaded,current=image;
  class Element{
    constructor(id){this.value=({spacing:'24','origin-x':'0','origin-y':'0',threshold:'160','scan-radius':'24','scan-contrast':'30'})[id]??'';this.checked=true;this.width=560;this.height=560;this.listeners={};this.dataset={};}
    addEventListener(name,fn){this.listeners[name]=fn;}setAttribute(name,value){this[name]=value;}
    getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
    getContext(){return new Proxy({getImageData:()=>current,createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)})},{get:(t,k)=>t[k]??(()=>{})});}
    fire(name,props={}){return this.listeners[name]?.(props);}click(){}
  }
  for(const m of html.matchAll(/\bid="([^"]+)"/g))elements[m[1]]=new Element(m[1]);
  Object.assign(box,{document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},
    Blob:class {constructor(parts){downloaded=parts.join('');}},Image:class {constructor(){this.naturalWidth=560;this.naturalHeight=560;}set src(v){this.onload();}},
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},setTimeout:fn=>fn()});
  vm.runInContext(scripts[1],box);
  for(const id of ['line-gap-recognize','scan-line-gap-recognize'])assert.equal(elements[id].disabled,true);
  elements['long-line-gaps'].checked=false;
  elements.image.files=[{name:'interrupted.png'}];elements.image.fire('change');elements['line-gap-recognize'].fire('click');
  assert.equal(elements.status.dataset.error,'true');assert.equal(elements.download.disabled,true);
  elements['long-line-gaps'].checked=true;elements['line-gap-recognize'].fire('click');
  assert.equal(elements.status.dataset.error,'false');assert.match(elements.status.textContent,/1 Linienlücken ergänzt/);
  elements.download.fire('click');const saved=JSON.parse(downloaded);assert.equal(saved.recognition.line_gaps.evidence.length,1);
  const grid=elements.spacing.value;current=fixture({lineGapHalf:30});elements['line-gap-recognize'].fire('click');
  assert.equal(elements.status.dataset.error,'true');assert.equal(elements.spacing.value,grid);
  elements.download.fire('click');assert.deepEqual(JSON.parse(downloaded),saved);
  current=fixture({gapIndices:[]});elements['line-gap-recognize'].fire('click');assert.equal(elements.download.disabled,true);
  elements.draft.fire('click');const partial=JSON.parse(downloaded);assert.equal(partial.draft,true);
  elements.import.files=[{text:async()=>JSON.stringify(partial)}];await elements.import.fire('change');
  assert.equal(elements['line-gap-recognize'].disabled,true);assert.equal(elements['long-line-gaps'].checked,true);elements.draft.fire('click');assert.deepEqual(JSON.parse(downloaded),partial);
  for(const c of box.model.intersections(partial.waypoints))elements.scene.fire('click',{clientX:c.coordinate[0]*3,clientY:-c.coordinate[1]*3});
  elements.download.fire('click');assert.deepEqual(JSON.parse(downloaded).recognition,partial.recognition);
  current=paintScan({straightBreak:true,lineGapHalf:22,lineBreaks:[0],gapIndices:[0,2,4]});elements.image.files=[{name:'scan.png'}];elements.image.fire('change');elements['scan-line-gap-recognize'].fire('click');
  assert.equal(elements.status.dataset.error,'false');elements.download.fire('click');assert.ok(JSON.parse(downloaded).recognition.preprocessing);
  elements.undo.fire('click');assert.equal(elements.draft.disabled,true);assert.equal(elements.download.disabled,true);
  const edited=box.model.Drawing.load(saved);edited.undo();assert.equal(edited.recognition,null);
  elements.import.files=[{text:async()=>fs.readFileSync(path.join(root,'examples/line_gap_trace/annotation.json'),'utf8')}];await elements.import.fire('change');
  assert.equal(elements['long-line-gaps'].checked,false);
  elements.image.files=[{name:'interrupted.png'}];elements.image.fire('change');elements['long-line-gaps'].checked=true;
  current=image;elements['line-gap-recognize'].fire('click');elements.spacing.value='2';elements.spacing.fire('change');elements.download.fire('click');assert.equal(JSON.parse(downloaded).recognition,undefined);
  console.log('Long line gap UI: both modes, visible repair count, failure recovery, drafts, reload, manual choices and provenance invalidation passed.');
}
testUI().catch(error=>{console.error(error);process.exitCode=1;});
