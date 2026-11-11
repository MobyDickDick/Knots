const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),zlib=require('node:zlib'),os=require('node:os');
const {spawnSync}=require('node:child_process');
const {paintShadow,shade}=require('../examples/shadow_fixture.cjs'),{paintCurve}=require('../examples/curve_fixture.cjs');
const root=path.join(__dirname,'..'),html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8');
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]),box={};vm.createContext(box);
vm.runInContext(scripts[0]+';globalThis.scan=ScanTracer;globalThis.pre=ScanPreprocessor;globalThis.model=TracerModel;',box);
const plain=v=>JSON.parse(JSON.stringify(v)),recognize=(im,opts={})=>plain(box.scan.recognize(im,{directional:true,...opts}));
const image=paintShadow(),original=image.data.slice(),draft=recognize(image),records=[];
assert.deepEqual(image.data,original);assert.deepEqual(recognize(image),draft);
assert.equal(draft.recognition.preprocessing.algorithm,'local-quadrant-v1');
assert.equal(draft.recognition.unresolved_crossings,3);assert.equal(draft.crossings.length,0);
assert.throws(()=>box.scan.recognize(image),/Komponenten|Bildrand/,'ordinary averaging retains a false shadow band');
assert.deepEqual(plain(box.model.Drawing.load(draft).record(true)),draft);
assert.throws(()=>box.model.Drawing.load(draft).record(),/oberen Strang/,'shadows do not supply crossing choices');
function review(r){
  r=plain(r);delete r.draft;
  const visits=box.model.intersections(r.waypoints).flatMap(c=>c.segments.map(segment=>({c,segment}))).sort((a,b)=>a.segment-b.segment);
  r.crossings=plain(visits.filter((_,i)=>i%2===0).map(({c,segment})=>({coordinate:c.coordinate,over_segment:segment})));return r;
}
// Independent clean ink is the oracle: no extra shadow pixels or missing stroke pixels.
for(const opts of [{},{axis:'horizontal'},{boundary:150},{boundary:400},{rotation:Math.PI/2},{rotation:.2},
  {mirror:true},{radius:1},{radius:5},{kind:'circle'}]){
  const im=paintShadow(opts),clean=paintCurve(opts),settings={directional:true,radius:opts.radius===5?40:24};
  assert.deepEqual(box.pre.prepare(im,settings).image.data,box.pre.prepare(clean,{radius:40}).image.data,'recover every original ink pixel');
  const r=recognize(im,settings);assert.equal(r.recognition.unresolved_crossings,opts.kind==='circle'?0:3);
  records.push({record:review(r),name:opts.kind==='circle'?'0_1':null});
}
// Rotate the actual photograph, including its lighting; compare the rotated clean mask.
function rotate(im){const out={...im,data:im.data.slice()};for(let y=0;y<im.height;y++)for(let x=0;x<im.width;x++)out.data.set(im.data.subarray(4*(y*im.width+x),4*(y*im.width+x)+4),4*(x*im.width+im.width-1-y));return out;}
assert.deepEqual(box.pre.prepare(rotate(image),{directional:true}).image.data,box.pre.prepare(rotate(paintCurve())).image.data);
assert.equal(recognize(rotate(image)).recognition.unresolved_crossings,3);
const gaps=recognize(paintShadow({gapIndices:[0,2,4]}),{gaps:true});assert.equal(gaps.recognition.inferred_crossings,3);records.push({record:gaps,name:'T(2,3)'});
records.push({record:recognize(paintShadow({gapIndices:[0,2,4],mirror:true}),{gaps:true}),name:'mirror(T(2,3))'});
const interrupted=paintShadow({straightBreak:true,lineGapHalf:22,lineBreaks:[0],gapIndices:[0,2,4]});
const lines=recognize(interrupted,{gaps:true,lineGaps:true,maxLineGap:64});
assert.equal(lines.recognition.inferred_crossings,3);assert.equal(lines.recognition.line_gaps.evidence.length,1);records.push({record:lines,name:'T(2,3)'});
const marked={...interrupted,data:interrupted.data.slice()};
for(const x0 of [20,50,80])for(let y=20;y<23;y++)for(let x=x0;x<x0+3;x++)marked.data.set([0,0,0,255],4*(y*marked.width+x));
const cleaned=recognize(marked,{gaps:true,lineGaps:true,maxLineGap:64,cleanup:16});
assert.equal(cleaned.recognition.preprocessing.cleanup.removed_pixels,27);records.push({record:cleaned,name:'T(2,3)'});
assert.throws(()=>recognize(marked,{gaps:true,lineGaps:true,maxLineGap:64}),/Komponenten|Fremdpixel/,'foreign ink is retained without cleanup');
assert.throws(()=>recognize(paintShadow({open:true})),/Offene|Lücke/,'no implicit gap closure');
assert.throws(()=>recognize(paintShadow({axis:'diagonal',boundary:560})),/Bildrand|Komponenten/,'a diagonal shadow at the border is outside this acceptance scope');
assert.throws(()=>recognize(paintShadow({dark:115})),/Offene|Lücke/,'insufficient local contrast must not bypass graph validation');
assert.throws(()=>recognize(paintShadow({texture:90})),/Bildrand|Komponenten|Fremdpixel|Offene/);
const alpha=paintCurve({alpha:220});assert.equal(recognize(shade(alpha,{dark:170})).recognition.unresolved_crossings,3);
const transparent={...image,data:image.data.slice()};for(let i=3;i<transparent.data.length;i+=4)transparent.data[i]=0;
assert.throws(()=>recognize(transparent),/Keine kontrastreiche/);
for(const directional of [1,0,'true',null,{},[]])assert.throws(()=>box.pre.prepare(image,{directional}),/Schalter/);
for(const opts of [{radius:7},{radius:81},{radius:true},{contrast:4},{contrast:101}])assert.throws(()=>recognize(image,opts),/ungültig/);
function small(w,h){const data=new Uint8ClampedArray(w*h*4);data.fill(255);data.set([0,0,0,255],4*(Math.floor(h/2)*w+Math.floor(w/2)));return {width:w,height:h,data};}
assert.equal(box.pre.prepare(small(17,17),{directional:true,radius:8}).report.foreground_pixels,1);
assert.throws(()=>box.pre.prepare(small(16,17),{directional:true,radius:8}),/mindestens/);
assert.throws(()=>box.pre.prepare(small(17,16),{directional:true,radius:8}),/mindestens/);
const edge=small(60,60);edge.data.set([0,0,0,255],0);assert.equal(box.pre.prepare(edge,{directional:true}).image.data[0],0,'border ink cannot hide in a clipped quadrant');
for(const im of [{width:1201,height:60,data:[]},{width:60,height:901,data:[]},small(1,1)])assert.throws(()=>recognize(im),/höchstens|mindestens/);
const many={width:1200,height:900,data:new Uint8ClampedArray(1200*900*4)};
for(let i=0;i<many.data.length;i+=4){const v=(i/4)%2?255:0;many.data.set([v,v,v,255],i);}
assert.throws(()=>recognize(many),/200000/);
// Altdaten behalten ihr Format; der neue Modus wird ausdrücklich berichtet.
assert.equal(box.pre.prepare(paintCurve()).report.algorithm,'local-mean-v1');
assert.deepEqual(box.pre.prepare(paintCurve()).report,box.pre.prepare(paintCurve(),{directional:false}).report);
const invalid=[...['unknown',null,[],true].map(algorithm=>({...draft,recognition:{...draft.recognition,preprocessing:{...draft.recognition.preprocessing,algorithm}}})),
  {...draft,editor_view:undefined},...[{width:48},{height:48},{width:1201},{height:901}].map(p=>({...draft,editor_view:{...draft.editor_view,...p}}))];
for(const r of invalid)assert.throws(()=>box.model.Drawing.load(r),/Scan-Aufbereitungsbericht/);
// Read the checked-in PNG, not just the fixture painter.
const bytes=fs.readFileSync(path.join(root,'examples/shadow_trace/abrupt_shadow.png')),parts=[];
for(let i=8;i<bytes.length;){const n=bytes.readUInt32BE(i);if(bytes.toString('ascii',i+4,i+8)==='IDAT')parts.push(bytes.subarray(i+8,i+8+n));i+=n+12;}
assert.equal(bytes[24],8);assert.equal(bytes[25],6);
const w=bytes.readUInt32BE(16),h=bytes.readUInt32BE(20),raw=zlib.inflateSync(Buffer.concat(parts)),data=new Uint8ClampedArray(w*h*4);
for(let y=0;y<h;y++){assert.equal(raw[y*(w*4+1)],0);data.set(raw.subarray(y*(w*4+1)+1,(y+1)*(w*4+1)),y*w*4);}
assert.deepEqual(recognize({width:w,height:h,data}),draft);
const tempRoot=fs.realpathSync(os.tmpdir()),directory=fs.mkdtempSync(path.join(tempRoot,'knots-shadow-'));
try{
  fs.writeFileSync(path.join(directory,'records.json'),JSON.stringify(records));fs.writeFileSync(path.join(directory,'invalid.json'),JSON.stringify(invalid));
  fs.writeFileSync(path.join(directory,'draft.json'),JSON.stringify(draft));
  const result=spawnSync('python',['-c',`
import json,sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict,annotation_to_dict,trace_annotation,write_traced_diagram
from knots_grid.validator import validate_cycle
from knots_grid.core import trace_turtle
from knots_grid.classification import classify_knot
root=Path(sys.argv[1]);records=json.loads((root/'records.json').read_text())
for item in records:
    record=item['record'];annotation=annotation_from_dict(record)
    assert annotation_to_dict(annotation)==record
    trace=trace_annotation(annotation)
    assert validate_cycle(trace.points).is_valid
    assert trace_turtle(trace.code).points==trace.points
    classification=classify_knot(trace.points)
    if item['name'] is None:
        assert classification.name in ('T(2,3)','mirror(T(2,3))')
    else: assert classification.name==item['name'], (classification.name,item['name'])
for record in json.loads((root/'invalid.json').read_text()):
    try: annotation_from_dict(record)
    except ValueError as error: assert 'scan preprocessing' in str(error)
    else: raise AssertionError('invalid report accepted')
try: write_traced_diagram(annotation_from_dict(json.loads((root/'draft.json').read_text())),root/'invalid')
except ValueError: pass
else: raise AssertionError('draft exported')
assert not (root/'invalid').exists()
write_traced_diagram(annotation_from_dict(records[0]['record']),root/'gallery')
assert 'Gerichtete Schattenkorrektur' in (root/'gallery/index.html').read_text(encoding='utf-8')
assert json.loads((root/'gallery/trace.json').read_text())['annotation']==records[0]['record']
print('Shadow-to-grid: masks, names and mirrors, exact turtle, reports, provenance and draft gate passed.')
`,directory],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);process.stdout.write(result.stdout);
}finally{assert.equal(path.dirname(fs.realpathSync(directory)),tempRoot);fs.rmSync(directory,{recursive:true,force:true});}
async function testUI(){
  const elements={};let downloaded,current=image,lastDraw;
  class Element{
    constructor(id){this.id=id;this.value=({'spacing':'24','origin-x':'0','origin-y':'0','threshold':'160','scan-radius':'24','scan-contrast':'30','scan-cleanup':'0'})[id]??'';this.checked=id==='show-image';this.width=560;this.height=560;this.listeners={};this.dataset={};}
    addEventListener(name,fn){this.listeners[name]=fn;}setAttribute(name,value){this[name]=value;}
    getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
    getContext(){return new Proxy({getImageData:()=>current,createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),drawImage:im=>{lastDraw=im;}},{get:(t,k)=>t[k]??(()=>{})});}
    fire(name,props={}){return this.listeners[name]?.(props);}click(){}
  }
  for(const m of html.matchAll(/\bid="([^"]+)"/g))elements[m[1]]=new Element(m[1]);
  Object.assign(box,{document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},Blob:class {constructor(parts){downloaded=parts.join('');}},
    Image:class {constructor(){this.naturalWidth=560;this.naturalHeight=560;}set src(v){this.onload();}},URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},setTimeout:fn=>fn()});
  vm.runInContext(scripts[1],box);
  assert.equal(elements['scan-directional'].checked,false);
  const load=()=>{elements.image.files=[{name:'shadow.png'}];elements.image.fire('change');};load();
  elements['scan-directional'].checked=true;elements['scan-directional'].fire('change');
  elements['scan-preview'].fire('click');assert.equal(elements.status.dataset.error,'false');assert.equal(lastDraw.id,'canvas');
  elements['scan-recognize'].fire('click');assert.equal(elements.status.dataset.error,'false');assert.equal(elements.download.disabled,true);
  elements.draft.fire('click');const saved=JSON.parse(downloaded);assert.equal(saved.recognition.preprocessing.algorithm,'local-quadrant-v1');
  elements['scan-directional'].checked=false;elements['scan-directional'].fire('change');assert.notEqual(lastDraw.id,'canvas','parameter change clears preview');
  elements.draft.fire('click');assert.deepEqual(JSON.parse(downloaded),saved,'parameter change retains established provenance');
  elements['scan-recognize'].fire('click');assert.equal(elements.status.dataset.error,'true');elements.draft.fire('click');assert.deepEqual(JSON.parse(downloaded),saved);
  elements.import.files=[{text:async()=>JSON.stringify(saved)}];await elements.import.fire('change');assert.equal(elements['scan-directional'].checked,true);
  const legacy={...saved,recognition:{...saved.recognition,preprocessing:{...saved.recognition.preprocessing,algorithm:'local-mean-v1'}}};
  elements.import.files=[{text:async()=>JSON.stringify(legacy)}];await elements.import.fire('change');assert.equal(elements['scan-directional'].checked,false);
  elements.import.files=[{text:async()=>JSON.stringify(saved)}];await elements.import.fire('change');
  for(const c of box.model.intersections(saved.waypoints))elements.scene.fire('click',{clientX:c.coordinate[0]*3,clientY:-c.coordinate[1]*3});
  elements.download.fire('click');assert.equal(JSON.parse(downloaded).crossings.length,3);
  elements.spacing.value='2';elements.spacing.fire('change');elements.download.fire('click');assert.equal(JSON.parse(downloaded).recognition,undefined);
  for(const [id,im] of [['scan-gap-recognize',paintShadow({gapIndices:[0,2,4]})],['scan-line-gap-recognize',interrupted]]){
    current=im;load();elements['long-line-gaps'].checked=true;elements[id].fire('click');assert.equal(elements.status.dataset.error,'false');
    elements.download.fire('click');const r=JSON.parse(downloaded);assert.equal(r.recognition.preprocessing.algorithm,'local-quadrant-v1');assert.equal(r.crossings.length,3);
  }
  console.log('Shadow UI: opt-in, preview, all scan modes, parameter and error recovery, import, choices and provenance invalidation passed.');
}
testUI().catch(error=>{console.error(error);process.exitCode=1;});
