const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),zlib=require('node:zlib');
const {spawnSync}=require('node:child_process'),os=require('node:os');
const {paintCurve}=require('../examples/curve_fixture.cjs'),{paintScan}=require('../examples/scan_fixture.cjs');
const root=path.join(__dirname,'..'),html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]),box={};vm.createContext(box);
vm.runInContext(scripts[0]+'\nglobalThis.curve=CurveTracer;globalThis.scan=ScanTracer;globalThis.model=TracerModel;',box);
const plain=v=>JSON.parse(JSON.stringify(v)),recognize=(image,options={})=>plain(box.curve.recognize(image,{gaps:true,...options}));
const fixture=options=>paintCurve({gapIndices:[0,2,4],...options});
const image=fixture(),original=image.data.slice(),record=recognize(image);
assert.deepEqual(image.data,original,'the source pixels must not be mutated');
assert.deepEqual(recognize(image),record,'deterministic evidence and geometry');
assert.equal(record.recognition.inferred_crossings,3);assert.equal(record.recognition.unresolved_crossings,0);
assert.equal(record.crossings.length,3);assert.equal(record.draft,undefined);
assert.deepEqual(plain(box.model.Drawing.load(record).record()),record);
assert.throws(()=>box.curve.recognize(image),/Komponenten|Offene|Lücke/,'the original continuous-curve mode never closes gaps');
const cases=[];
for(const options of [{},{rotation:Math.PI/2},{rotation:Math.PI},{rotation:3*Math.PI/2},{rotation:.2},{mirror:true},{radius:1},{radius:2},{radius:5},{gapIndices:[1,3,5]}]){
  const r=recognize(fixture(options));assert.equal(r.recognition.inferred_crossings,3);
  assert.deepEqual(plain(box.model.Drawing.load(r).record()),r);
  const gaps=r.recognition.crossing_gaps.evidence;
  assert.equal(gaps.length,3);
  assert.equal(r.recognition.foreground_pixels,fixture(options).data.filter((v,i)=>i%4===0&&v<160).length);
  for(const e of gaps){assert.ok(e.added_pixels>=4);assert.ok(r.crossings.some(c=>c.over_segment===e.over_segment&&c.coordinate.join()===e.coordinate.join()));}
  cases.push({record:r,name:options.mirror||options.gapIndices?'mirror(T(2,3))':'T(2,3)'});
}
const partial=recognize(fixture({gapIndices:[0]}));
assert.equal(partial.recognition.inferred_crossings,1);assert.equal(partial.recognition.unresolved_crossings,2);assert.equal(partial.draft,true);
assert.throws(()=>box.model.Drawing.load(partial).record(),/oberen Strang/);
const solid=recognize(paintCurve());assert.equal(solid.crossings.length,0);assert.equal(solid.recognition.unresolved_crossings,3);
const circle=recognize(paintCurve({kind:'circle'}));assert.equal(circle.draft,undefined);assert.equal(circle.recognition.inferred_crossings,0);
const scan=plain(box.scan.recognize(paintScan({gapIndices:[0,2,4]}),{gaps:true}));
assert.equal(scan.recognition.inferred_crossings,3);assert.ok(scan.recognition.preprocessing);cases.push({record:scan,name:'T(2,3)'});
// Pixel input failures must reject the whole recognition, never guess a connection.
for(const bad of [fixture({open:true}),fixture({gapHalf:25}),fixture({gapHalf:5}),paintCurve({kind:'circle',open:true})])
  assert.throws(()=>recognize(bad),/Offene|Lücke|Kreuzungs/);
const noise=fixture();noise.data.set([0,0,0,255],4*(20*noise.width+20));
assert.throws(()=>recognize(noise),/Fremdpixel|isolierte|Komponenten/);
// Remove the continuous overpass at one crossing: four loose arms are not evidence.
const missingOver=fixture();
for(let y=139;y<=161;y++)for(let x=344;x<=365;x++)missingOver.data.set([255,255,255,255],4*(y*missingOver.width+x));
assert.throws(()=>recognize(missingOver),/Offene|Lücke|Kreuzungs/);
const transparent=fixture();for(let i=3;i<transparent.data.length;i+=4)transparent.data[i]=0;
assert.throws(()=>recognize(transparent),/Keine dunkle/);
assert.throws(()=>recognize({width:1201,height:1,data:[]}),/höchstens/);
const manyEnds=paintCurve({kind:'circle'});
for(let i=0;i<21;i++)for(let x=15;x<31;x++)manyEnds.data.set([0,0,0,255],4*((10+i*20)*manyEnds.width+x));
assert.throws(()=>recognize(manyEnds),/40/);
// Decode the actual stored PNG, including its white crossing shoulders.
function readPNG(filename){
  const png=fs.readFileSync(filename),parts=[];assert.equal(png[24],8);assert.equal(png[25],6);
  for(let i=8;i<png.length;){const n=png.readUInt32BE(i);if(png.toString('ascii',i+4,i+8)==='IDAT')parts.push(png.subarray(i+8,i+8+n));i+=n+12;}
  const width=png.readUInt32BE(16),height=png.readUInt32BE(20),raw=zlib.inflateSync(Buffer.concat(parts)),data=new Uint8ClampedArray(width*height*4);
  for(let y=0;y<height;y++){assert.equal(raw[y*(width*4+1)],0);data.set(raw.subarray(y*(width*4+1)+1,(y+1)*(width*4+1)),y*width*4);}return {width,height,data};
}
assert.deepEqual(recognize(readPNG(path.join(root,'examples/gap_trace/gapped_trefoil.png'))),record);
const invalid=[];
function badReport(patch){const r=plain(record);Object.assign(r.recognition.crossing_gaps,patch);invalid.push(r);}
badReport({algorithm:'unknown'});badReport({evidence:null});badReport({evidence:[...record.recognition.crossing_gaps.evidence,record.recognition.crossing_gaps.evidence[0]]});
for(const patch of [{added_pixels:true},{added_pixels:81},{endpoints:[[0,0],[1,1]]},{crossing_pixel:[1200,0]},{coordinate:[0,0]},{over_segment:-1},{coordinate:'x'}]){
  const r=plain(record);Object.assign(r.recognition.crossing_gaps.evidence[0],patch);invalid.push(r);
}
for(const patch of [{inferred_crossings:2},{unresolved_crossings:1},{crossing_gaps:null},{algorithm:'grid-sampling-v1'}]){
  const r=plain(record);Object.assign(r.recognition,patch);invalid.push(r);
}
invalid.push({...record,editor_view:null});
for(const bad of invalid)assert.throws(()=>box.model.Drawing.load(bad),/Bericht/);
const tempRoot=fs.realpathSync(os.tmpdir()),directory=fs.mkdtempSync(path.join(tempRoot,'knots-gaps-'));
try{
  fs.writeFileSync(path.join(directory,'cases.json'),JSON.stringify(cases));fs.writeFileSync(path.join(directory,'invalid.json'),JSON.stringify(invalid));
  fs.writeFileSync(path.join(directory,'draft.json'),JSON.stringify(partial));
  const result=spawnSync('python',['-c',`
import json,sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict,annotation_to_dict,trace_annotation,write_traced_diagram
from knots_grid.validator import validate_cycle
from knots_grid.core import trace_turtle
from knots_grid.classification import classify_knot
root=Path(sys.argv[1]);cases=json.loads((root/'cases.json').read_text())
for case in cases:
    record=case['record'];a=annotation_from_dict(record)
    assert annotation_to_dict(a)==record
    trace=trace_annotation(a)
    assert validate_cycle(trace.points).is_valid
    assert trace_turtle(trace.code).points==trace.points
    assert classify_knot(trace.points).name==case['name']
for bad in json.loads((root/'invalid.json').read_text()):
    try: annotation_from_dict(bad)
    except ValueError: pass
    else: raise AssertionError(bad)
try: write_traced_diagram(annotation_from_dict(json.loads((root/'draft.json').read_text())),root/'invalid')
except ValueError as error: assert 'missing over/under' in str(error)
else: raise AssertionError('partial draft must not export')
assert not (root/'invalid').exists()
write_traced_diagram(annotation_from_dict(cases[0]['record']),root/'gallery')
metadata=json.loads((root/'gallery'/'trace.json').read_text())
assert metadata['source']=='reviewed_gap_annotation'
assert metadata['annotation']==cases[0]['record']
print('Gap-to-grid: known handedness, rotations, mirrors, evidence validation, exact turtle roundtrip, drafts and gallery provenance passed.')
`,directory],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);process.stdout.write(result.stdout);
  const gallery=spawnSync('node',[path.join(__dirname,'test_gallery_runtime.cjs'),path.join(directory,'gallery/index.html')],{encoding:'utf8'});
  assert.equal(gallery.status,0,gallery.stdout+gallery.stderr);
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
  assert.equal(elements['gap-recognize'].disabled,true);assert.equal(elements['scan-gap-recognize'].disabled,true);
  elements.image.files=[{name:'gaps.png'}];elements.image.fire('change');elements['gap-recognize'].fire('click');
  assert.equal(elements.status.dataset.error,'false');assert.equal(elements.download.disabled,false);
  elements.download.fire('click');const saved=JSON.parse(downloaded);assert.equal(saved.recognition.inferred_crossings,3);
  current=missingOver;elements['gap-recognize'].fire('click');assert.equal(elements.status.dataset.error,'true');
  elements.download.fire('click');assert.deepEqual(JSON.parse(downloaded),saved,'failed evidence preserves drawing, choices and grid');
  current=fixture({gapIndices:[0]});elements['gap-recognize'].fire('click');assert.equal(elements.download.disabled,true);
  elements.draft.fire('click');const draft=JSON.parse(downloaded);assert.equal(draft.crossings.length,1);
  elements.import.files=[{text:async()=>JSON.stringify(draft)}];await elements.import.fire('change');
  assert.equal(elements['gap-recognize'].disabled,true);
  for(const c of box.model.intersections(draft.waypoints))if(!draft.crossings.some(p=>p.coordinate.join()===c.coordinate.join()))
    elements.scene.fire('click',{clientX:c.coordinate[0]*3,clientY:-c.coordinate[1]*3});
  assert.equal(elements.download.disabled,false);elements.download.fire('click');assert.equal(JSON.parse(downloaded).crossings.length,3);
  // A manual override retains the historical initial evidence.
  const c=draft.crossings[0];elements.scene.fire('click',{clientX:c.coordinate[0]*3,clientY:-c.coordinate[1]*3});elements.download.fire('click');
  const changed=JSON.parse(downloaded);assert.notEqual(changed.crossings.find(p=>p.coordinate.join()===c.coordinate.join()).over_segment,c.over_segment);
  assert.deepEqual(changed.recognition,draft.recognition);
  current=paintScan({gapIndices:[0,2,4]});elements.image.files=[{name:'scan.png'}];elements.image.fire('change');elements['scan-gap-recognize'].fire('click');
  assert.equal(elements.status.dataset.error,'false');elements.download.fire('click');assert.ok(JSON.parse(downloaded).recognition.preprocessing);
  elements.spacing.value='2';elements.spacing.fire('change');elements.download.fire('click');assert.equal(JSON.parse(downloaded).recognition,undefined);
  console.log('Gap UI: both recognition modes, failure recovery, mixed drafts, save/load, manual override and provenance invalidation passed.');
}
testUI().catch(error=>{console.error(error);process.exitCode=1;});
