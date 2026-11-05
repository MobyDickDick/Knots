const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const os=require('node:os'),zlib=require('node:zlib'),{spawnSync}=require('node:child_process');
const {paintCurve}=require('../examples/curve_fixture.cjs');
const root=path.join(__dirname,'..'),html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]),box={};vm.createContext(box);
vm.runInContext(scripts[0]+'\nglobalThis.curve=CurveTracer;globalThis.model=TracerModel;',box);
const plain=v=>JSON.parse(JSON.stringify(v)),recognize=(image,options)=>plain(box.curve.recognize(image,options));
const circle=recognize(paintCurve({kind:'circle'}));
assert.equal(circle.recognition.unresolved_crossings,0);
assert.ok(circle.waypoints.length>=4);
const trefoil=recognize(paintCurve());
assert.equal(trefoil.recognition.unresolved_crossings,3);
assert.equal(trefoil.draft,true);
assert.deepEqual(recognize(paintCurve()),trefoil,'recognition must be deterministic');
const records=[circle];
for(const mirror of [false,true])for(const rotation of [0,Math.PI/2,Math.PI,3*Math.PI/2,.2]){
  const record=recognize(paintCurve({mirror,rotation}));
  assert.equal(record.recognition.unresolved_crossings,3);
  assert.equal(record.recognition.inferred_crossings,0,'solid crossing pixels supply no over/under evidence');
  assert.equal(record.crossings.length,0);
  const drawing=box.model.Drawing.load(record);
  assert.deepEqual(plain(drawing.record(true)),record,'draft and origin roundtrip');
  assert.throws(()=>drawing.record(),/oberen Strang/);
  // An explicit simulated review: alternating over/under around this trefoil.
  const found=box.model.intersections(record.waypoints);
  const visits=found.flatMap(c=>c.segments.map(segment=>({c,segment}))).sort((a,b)=>a.segment-b.segment);
  const reviewed={...record,crossings:visits.filter((_,i)=>i%2===0).map(({c,segment})=>({coordinate:plain(c.coordinate),over_segment:segment}))};
  delete reviewed.draft;box.model.Drawing.load(reviewed);records.push(reviewed);
  if(!mirror&&rotation===0){
    const inverse={...reviewed,crossings:reviewed.crossings.map(c=>({coordinate:c.coordinate,
      over_segment:plain(found.find(f=>f.coordinate.join()===c.coordinate.join()).segments).find(s=>s!==c.over_segment)}))};
    records.push(inverse);
  }
}
for(const options of [{radius:1},{radius:2},{radius:5},{scale:60},{color:180}]){
  const record=recognize(paintCurve(options),options.color?{threshold:200}:undefined);
  assert.equal(record.recognition.unresolved_crossings,3);
}
const fineGrid=recognize(paintCurve({scale:20,radius:2}));
assert.equal(fineGrid.recognition.sample_size,4,'failed coarse graph checks must fall back to a finer grid');
assert.equal(fineGrid.editor_view.spacing,1);
const fineVisits=box.model.intersections(fineGrid.waypoints).flatMap(c=>c.segments.map(segment=>({c,segment}))).sort((a,b)=>a.segment-b.segment);
fineGrid.crossings=fineVisits.filter((_,i)=>i%2===0).map(({c,segment})=>({coordinate:plain(c.coordinate),over_segment:segment}));
delete fineGrid.draft;records.push(fineGrid);
assert.throws(()=>recognize(paintCurve({open:true})),/Offene|Lücke/);
assert.throws(()=>recognize(paintCurve({alpha:0})),/Keine dunkle/);
assert.throws(()=>recognize(paintCurve({color:180})),/Keine dunkle/);
assert.throws(()=>recognize(paintCurve(),{threshold:0}),/ungültig/);
assert.throws(()=>recognize({width:1201,height:10,data:[]}),/höchstens/);
assert.throws(()=>recognize({width:10,height:10,data:[]}),/höchstens/);
const noise=paintCurve();noise.data.set([0,0,0,255],4*(20*noise.width+20));
assert.throws(()=>recognize(noise),/isolierte|Fremdpixel|Komponenten/);
const smallNoise=paintCurve();
for(const [x,y] of [[20,20],[21,20],[20,21],[21,21]])smallNoise.data.set([0,0,0,255],4*(y*smallNoise.width+x));
assert.throws(()=>recognize(smallNoise),/Fremdpixel|Komponenten/,'a small component must not silently disappear during thinning');
assert.throws(()=>recognize(paintCurve({offset:[100,0]})),/Bildrand|Offene/);
function combine(a,b){for(let i=0;i<a.data.length;i+=4)if(b.data[i]<160)a.data.set(b.data.subarray(i,i+4),i);return a;}
const separate=combine(paintCurve({kind:'circle',scale:35,offset:[-130,0]}),paintCurve({kind:'circle',scale:35,offset:[130,0]}));
assert.throws(()=>recognize(separate),/Komponenten/);
const link=combine(paintCurve({kind:'circle'}),paintCurve({kind:'circle',rotation:Math.PI/2}));
assert.throws(()=>recognize(link),/Stränge|Kreuzungs|Berührung/,'connected ink may still describe a two-component link');
const touching=combine(paintCurve({kind:'circle',scale:40,offset:[-80,0]}),paintCurve({kind:'circle',scale:40,offset:[80,0]}));
assert.throws(()=>recognize(touching),/Verzweigung|Kreuzungs|Berührung/);
const solid={width:600,height:500,data:new Uint8ClampedArray(600*500*4)};
for(let i=3;i<solid.data.length;i+=4)solid.data[i]=255;
assert.throws(()=>recognize(solid),/200000/);
// The stored PNG, not just the synthetic pixel buffer, is exercised here.
const png=fs.readFileSync(path.join(root,'examples/curve_trace/curved_trefoil.png')),parts=[];
assert.equal(png[25],6);assert.equal(png[24],8);
for(let i=8;i<png.length;){const n=png.readUInt32BE(i);if(png.toString('ascii',i+4,i+8)==='IDAT')parts.push(png.subarray(i+8,i+8+n));i+=n+12;}
const width=png.readUInt32BE(16),height=png.readUInt32BE(20),raw=zlib.inflateSync(Buffer.concat(parts)),data=new Uint8ClampedArray(width*height*4);
for(let y=0;y<height;y++){assert.equal(raw[y*(width*4+1)],0);data.set(raw.subarray(y*(width*4+1)+1,(y+1)*(width*4+1)),y*width*4);}
assert.deepEqual(recognize({width,height,data}),trefoil);
for(const report of [{...trefoil.recognition,sample_size:3},{...trefoil.recognition,skeleton_pixels:0},
  {...trefoil.recognition,thinning_iterations:129},{...trefoil.recognition,inferred_crossings:1},
  {...trefoil.recognition,grid_detection:{}}])assert.throws(()=>box.model.Drawing.load({...trefoil,recognition:report}),/Kurven-Erkennungsbericht/);
const tempRoot=fs.realpathSync(os.tmpdir()),directory=fs.mkdtempSync(path.join(tempRoot,'knots-curve-'));
try{
  fs.writeFileSync(path.join(directory,'records.json'),JSON.stringify(records));
  fs.writeFileSync(path.join(directory,'draft.json'),JSON.stringify(trefoil));
  const result=spawnSync('python',['-c',`
import json,sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict,annotation_to_dict,trace_annotation,write_traced_diagram
from knots_grid.validator import validate_cycle
from knots_grid.core import trace_turtle
from knots_grid.classification import classify_knot
root=Path(sys.argv[1]);records=json.loads((root/'records.json').read_text());names=[]
for i,record in enumerate(records):
    annotation=annotation_from_dict(record)
    assert annotation_to_dict(annotation)==record
    trace=trace_annotation(annotation)
    assert validate_cycle(trace.points).is_valid
    assert trace_turtle(trace.code).points==trace.points
    classification=classify_knot(trace.points);names.append(classification.name)
    assert classification.determinant==(1 if i==0 else 3)
    assert classification.name in ('0_1','T(2,3)','mirror(T(2,3))'),classification
assert names[1]!=names[2],names
try:
    write_traced_diagram(annotation_from_dict(json.loads((root/'draft.json').read_text())),root/'invalid')
except ValueError as error:
    assert 'missing over/under' in str(error)
else:
    raise AssertionError('draft must not export')
assert not (root/'invalid').exists()
write_traced_diagram(annotation_from_dict(records[1]),root/'gallery')
metadata=json.loads((root/'gallery'/'trace.json').read_text())
assert metadata['source']=='reviewed_curve_annotation'
assert metadata['annotation']==records[1]
print('Curve-to-grid: rotations, mirrors, known trefoil, exact turtle roundtrip, draft rejection and provenance passed.')
`,directory],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);process.stdout.write(result.stdout);
  const gallery=spawnSync('node',[path.join(__dirname,'test_gallery_runtime.cjs'),path.join(directory,'gallery/index.html')],{encoding:'utf8'});
  assert.equal(gallery.status,0,gallery.stdout+gallery.stderr);
}finally{
  assert.equal(path.dirname(fs.realpathSync(directory)),tempRoot);
  fs.rmSync(directory,{recursive:true,force:true});
}
async function testUI(){
  const elements={};let downloaded,current=paintCurve();
  class Element{
    constructor(id){this.id=id;this.value=({spacing:'24','origin-x':'0','origin-y':'0',threshold:'160'})[id]??'';this.checked=true;this.width=560;this.height=560;this.listeners={};this.dataset={};}
    addEventListener(name,fn){this.listeners[name]=fn;}setAttribute(name,value){this[name]=value;}
    getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
    getContext(){return new Proxy({getImageData:()=>current},{get:(t,k)=>t[k]??(()=>{})});}
    fire(name,props={}){return this.listeners[name]?.(props);}click(){}
  }
  for(const m of html.matchAll(/\bid="([^"]+)"/g))elements[m[1]]=new Element(m[1]);
  Object.assign(box,{document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},
    Blob:class {constructor(parts){downloaded=parts.join('');}},Image:class {constructor(){this.naturalWidth=560;this.naturalHeight=560;}set src(v){this.onload();}},
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},setTimeout:fn=>fn()});
  vm.runInContext(scripts[1],box);
  assert.equal(elements['curve-recognize'].disabled,true);
  elements.image.files=[{name:'curve.png'}];elements.image.fire('change');
  assert.equal(elements['curve-recognize'].disabled,false);elements['curve-recognize'].fire('click');
  assert.equal(elements.status.dataset.error,'false');assert.equal(elements.download.disabled,true);assert.equal(elements.draft.disabled,false);
  assert.equal(Number(elements.spacing.value),3);
  elements.draft.fire('click');const saved=JSON.parse(downloaded);
  assert.equal(saved.draft,true);assert.equal(saved.recognition.algorithm,'skeleton-orthogonal-v1');
  current=noise;elements['curve-recognize'].fire('click');assert.equal(elements.status.dataset.error,'true');
  elements.draft.fire('click');assert.deepEqual(JSON.parse(downloaded),saved,'errors preserve the entire previous drawing and view');
  elements.import.files=[{text:async()=>JSON.stringify(saved)}];await elements.import.fire('change');
  assert.equal(elements['curve-recognize'].disabled,true);assert.equal(Number(elements.spacing.value),3);
  for(const c of box.model.intersections(saved.waypoints))elements.scene.fire('click',{clientX:c.coordinate[0]*3,clientY:-c.coordinate[1]*3});
  assert.equal(elements.download.disabled,false);elements.download.fire('click');
  assert.equal(JSON.parse(downloaded).crossings.length,3);assert.equal(JSON.parse(downloaded).draft,undefined);
  elements.spacing.value='2';elements.spacing.fire('change');elements.download.fire('click');
  assert.equal(JSON.parse(downloaded).recognition,undefined,'alignment changes discard curve provenance');
  console.log('Curve UI: loading, recognition, failure recovery, fine grid, drafts, manual crossing choices and stale report invalidation passed.');
}
testUI().catch(error=>{console.error(error);process.exitCode=1;});
