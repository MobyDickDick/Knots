const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),zlib=require('node:zlib');
const {spawnSync}=require('node:child_process'),os=require('node:os');
const {paintCurve}=require('../examples/curve_fixture.cjs'),{paintScan}=require('../examples/scan_fixture.cjs');
const root=path.join(__dirname,'..'),html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]),box={};vm.createContext(box);
vm.runInContext(scripts[0]+'\nglobalThis.scan=ScanTracer;globalThis.pre=ScanPreprocessor;globalThis.curve=CurveTracer;globalThis.model=TracerModel;',box);
const plain=v=>JSON.parse(JSON.stringify(v)),recognize=(image,options)=>plain(box.scan.recognize(image,options));
const image=paintScan(),original=image.data.slice(),draft=recognize(image);
assert.deepEqual(image.data,original,'preparation must not mutate the original');
assert.deepEqual(recognize(image),draft,'deterministic recognition');
assert.equal(draft.recognition.unresolved_crossings,3);assert.equal(draft.recognition.inferred_crossings,0);
assert.equal(draft.crossings.length,0);assert.equal(draft.draft,true);
assert.throws(()=>box.curve.recognize(image),/200000|Bildrand|Offene|Komponenten|Fremdpixel/,'the uncorrected shadow is not a clean curve');
// This fixture is designed so illumination correction preserves exactly the ink mask.
const clean=paintCurve(),prepared=box.pre.prepare(image);
for(let i=0;i<image.width*image.height;i++)assert.equal(prepared.image.data[4*i]===0,clean.data[4*i]<160);
assert.deepEqual(plain(box.model.Drawing.load(draft).record(true)),draft);
assert.throws(()=>box.model.Drawing.load(draft).record(),/oberen Strang/);
function review(record){
  const result=plain(record),visits=box.model.intersections(result.waypoints).flatMap(c=>c.segments.map(segment=>({c,segment}))).sort((a,b)=>a.segment-b.segment);
  result.crossings=visits.filter((_,i)=>i%2===0).map(({c,segment})=>({coordinate:plain(c.coordinate),over_segment:segment}));delete result.draft;return result;
}
const records=[];
for(const options of [{},{shadow:140},{shadow:0,texture:12},{rotation:Math.PI/2},{rotation:.2},{mirror:true},{radius:1},{radius:5},{kind:'circle'}]){
  const record=recognize(paintScan(options));
  assert.equal(record.recognition.unresolved_crossings,options.kind==='circle'?0:3);
  assert.deepEqual(plain(box.model.Drawing.load(record).record(true)),record);records.push(review(record));
}
for(const options of [{radius:16,contrast:20},{radius:40,contrast:40},{radius:80,contrast:30}])assert.equal(recognize(image,options).recognition.unresolved_crossings,3);
const transparent={...image,data:image.data.slice()};for(let i=3;i<transparent.data.length;i+=4)transparent.data[i]=0;
assert.throws(()=>recognize(transparent),/Keine kontrastreiche/);
const partial={...clean,data:clean.data.slice()};for(let i=3;i<partial.data.length;i+=4)partial.data[i]=180;
assert.equal(recognize(partial).recognition.unresolved_crossings,3,'alpha composites against white');
for(const options of [{radius:7},{radius:81},{radius:24.5},{contrast:4},{contrast:101},{contrast:NaN}])assert.throws(()=>recognize(image,options),/ungültig/);
for(const bad of [{width:1201,height:1,data:[]},{width:10,height:901,data:[]},{width:10,height:10,data:[]}])assert.throws(()=>recognize(bad),/höchstens/);
const noise=paintScan();noise.data.set([0,0,0,255],4*(20*noise.width+20));
assert.throws(()=>recognize(noise),/Fremdpixel|Komponenten/,'high contrast speckles are retained and rejected');
assert.throws(()=>recognize(paintScan({open:true})),/Offene|Lücke/,'no gap closure');
const textured=paintScan({texture:90});assert.throws(()=>recognize(textured),/Komponenten|Bildrand|Offene|Fremdpixel/);
const many={width:1200,height:900,data:new Uint8ClampedArray(1200*900*4)};
for(let i=0;i<many.data.length;i+=4)many.data.set([(i/4)%2?255:0,(i/4)%2?255:0,(i/4)%2?255:0,255],i);
assert.throws(()=>recognize(many),/200000/);
const invalidReports=[null,{...draft.recognition.preprocessing,algorithm:'unknown'},
  {...draft.recognition.preprocessing,window_radius:true},{...draft.recognition.preprocessing,window_radius:81},
  {...draft.recognition.preprocessing,contrast:0},{...draft.recognition.preprocessing,foreground_pixels:0},
  {...draft.recognition.preprocessing,background_min:256},{...draft.recognition.preprocessing,background_max:-1}];
for(const preprocessing of invalidReports)assert.throws(()=>box.model.Drawing.load({...draft,recognition:{...draft.recognition,preprocessing}}),/Scan-Aufbereitungsbericht/);
// Decode the stored PNG and exercise its actual pixel buffer.
const png=fs.readFileSync(path.join(root,'examples/scan_trace/simulated_scan.png')),parts=[];
assert.equal(png[24],8);assert.equal(png[25],6);
for(let i=8;i<png.length;){const n=png.readUInt32BE(i);if(png.toString('ascii',i+4,i+8)==='IDAT')parts.push(png.subarray(i+8,i+8+n));i+=n+12;}
const width=png.readUInt32BE(16),height=png.readUInt32BE(20),raw=zlib.inflateSync(Buffer.concat(parts)),data=new Uint8ClampedArray(width*height*4);
for(let y=0;y<height;y++){assert.equal(raw[y*(width*4+1)],0);data.set(raw.subarray(y*(width*4+1)+1,(y+1)*(width*4+1)),y*width*4);}
assert.deepEqual(recognize({width,height,data}),draft);
const tempRoot=fs.realpathSync(os.tmpdir()),directory=fs.mkdtempSync(path.join(tempRoot,'knots-scan-'));
try{
  fs.writeFileSync(path.join(directory,'records.json'),JSON.stringify(records));
  fs.writeFileSync(path.join(directory,'invalid.json'),JSON.stringify(invalidReports.map(preprocessing=>({...draft,recognition:{...draft.recognition,preprocessing}}))));
  fs.writeFileSync(path.join(directory,'draft.json'),JSON.stringify(draft));
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
    except ValueError as error: assert 'scan preprocessing' in str(error)
    else: raise AssertionError('invalid report accepted')
try: write_traced_diagram(annotation_from_dict(json.loads((root/'draft.json').read_text())),root/'invalid')
except ValueError: pass
else: raise AssertionError('draft must not export')
assert not (root/'invalid').exists()
write_traced_diagram(annotation_from_dict(records[0]),root/'gallery')
metadata=json.loads((root/'gallery'/'trace.json').read_text())
assert metadata['source']=='reviewed_scan_annotation'
assert metadata['annotation']==records[0]
assert metadata['classification']['name'] in ('T(2,3)','mirror(T(2,3))')
print('Scan-to-grid: valid paths, exact turtle roundtrip, trefoil, draft rejection, report validation and provenance passed.')
`,directory],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);process.stdout.write(result.stdout);
  const gallery=spawnSync('node',[path.join(__dirname,'test_gallery_runtime.cjs'),path.join(directory,'gallery/index.html')],{encoding:'utf8'});
  assert.equal(gallery.status,0,gallery.stdout+gallery.stderr);
}finally{assert.equal(path.dirname(fs.realpathSync(directory)),tempRoot);fs.rmSync(directory,{recursive:true,force:true});}
async function testUI(){
  const elements={};let downloaded,current=image,previewDraws=0;
  class Element{
    constructor(id){this.id=id;this.value=({spacing:'24','origin-x':'0','origin-y':'0',threshold:'160','scan-radius':'24','scan-contrast':'30'})[id]??'';this.checked=id==='show-image';this.width=560;this.height=560;this.listeners={};this.dataset={};}
    addEventListener(name,fn){this.listeners[name]=fn;}setAttribute(name,value){this[name]=value;}
    getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
    getContext(){return new Proxy({getImageData:()=>current,createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),putImageData:()=>{previewDraws++;}},{get:(t,k)=>t[k]??(()=>{})});}
    fire(name,props={}){return this.listeners[name]?.(props);}click(){}
  }
  for(const m of html.matchAll(/\bid="([^"]+)"/g))elements[m[1]]=new Element(m[1]);
  Object.assign(box,{document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},
    Blob:class {constructor(parts){downloaded=parts.join('');}},Image:class {constructor(){this.naturalWidth=560;this.naturalHeight=560;}set src(v){this.onload();}},
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},setTimeout:fn=>fn()});
  vm.runInContext(scripts[1],box);
  assert.equal(elements['scan-preview'].disabled,true);assert.equal(elements['scan-recognize'].disabled,true);
  elements.image.files=[{name:'scan.png'}];elements.image.fire('change');
  elements['scan-preview'].fire('click');assert.equal(elements.status.dataset.error,'false');assert.equal(elements['show-scan'].checked,true);
  assert.equal(previewDraws,1);assert.equal(elements.draft.disabled,true,'preview does not replace drawing');
  elements['scan-recognize'].fire('click');assert.equal(elements.status.dataset.error,'false');
  assert.equal(elements.download.disabled,true);elements.draft.fire('click');const saved=JSON.parse(downloaded);
  assert.ok(saved.recognition.preprocessing);assert.equal(saved.source_image,'scan.png');
  current=noise;elements['scan-recognize'].fire('click');assert.equal(elements.status.dataset.error,'true');
  elements.draft.fire('click');assert.deepEqual(JSON.parse(downloaded),saved,'failed scan retains drawing and view');
  elements['scan-contrast'].value='0';elements['scan-preview'].fire('click');assert.equal(elements.status.dataset.error,'true');
  elements.draft.fire('click');assert.deepEqual(JSON.parse(downloaded),saved,'invalid parameters retain drawing');
  elements.import.files=[{text:async()=>JSON.stringify(saved)}];await elements.import.fire('change');
  assert.equal(elements['scan-recognize'].disabled,true);assert.equal(Number(elements['scan-contrast'].value),30);
  for(const c of box.model.intersections(saved.waypoints))elements.scene.fire('click',{clientX:c.coordinate[0]*3,clientY:-c.coordinate[1]*3});
  elements.download.fire('click');assert.equal(JSON.parse(downloaded).crossings.length,3);assert.ok(JSON.parse(downloaded).recognition.preprocessing);
  elements.spacing.value='2';elements.spacing.fire('change');elements.download.fire('click');assert.equal(JSON.parse(downloaded).recognition,undefined);
  console.log('Scan UI: preview, recognition, failure recovery, parameters, manual choices, save/load and provenance invalidation passed.');
}
testUI().catch(error=>{console.error(error);process.exitCode=1;});
