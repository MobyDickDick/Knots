const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const zlib = require('node:zlib');
const {spawnSync} = require('node:child_process');
const os = require('node:os');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'src/knots_grid/image_tracer.html'), 'utf8');
const box = {};
vm.createContext(box);
vm.runInContext([...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1] +
  '\nglobalThis.raster=RasterTracer;globalThis.model=TracerModel;', box);
const recognize = (image, options) => JSON.parse(JSON.stringify(box.raster.recognize(image, options)));

// Decode the actual dependency-free RGB example, including all IDAT chunks.
function referenceRaster() {
  const png = fs.readFileSync(path.join(root, 'examples/image_trace/trefoil_reference.png'));
  const width = png.readUInt32BE(16), height = png.readUInt32BE(20), parts = [];
  assert.equal(png[24], 8);assert.equal(png[25], 2);
  for (let i=8;i<png.length;) {
    const size=png.readUInt32BE(i);
    if(png.toString('ascii',i+4,i+8)==='IDAT')parts.push(png.subarray(i+8,i+8+size));
    i+=size+12;
  }
  const rgb=zlib.inflateSync(Buffer.concat(parts)), data=new Uint8ClampedArray(width*height*4);
  for(let y=0;y<height;y++) {
    assert.equal(rgb[y*(1+width*3)],0);
    for(let x=0;x<width;x++) {
      const k=y*(1+width*3)+1+3*x;
      data.set([rgb[k],rgb[k+1],rgb[k+2],255],4*(y*width+x));
    }
  }
  return {data,width,height};
}

function paint(points, {spacing=40,origin=[0,0],gaps=[],width=320,height=320,color=30,alpha=255}={}) {
  const data=new Uint8ClampedArray(width*height*4).fill(255);
  const image={data,width,height};
  function line(a,b,radius,shade) {
    const ax=origin[0]+a[0]*spacing,ay=origin[1]-a[1]*spacing;
    const bx=origin[0]+b[0]*spacing,by=origin[1]-b[1]*spacing;
    for(let y=Math.max(0,Math.ceil(Math.min(ay,by)-radius));y<=Math.min(height-1,Math.floor(Math.max(ay,by)+radius));y++)
      for(let x=Math.max(0,Math.ceil(Math.min(ax,bx)-radius));x<=Math.min(width-1,Math.floor(Math.max(ax,bx)+radius));x++) {
        const t=Math.max(0,Math.min(1,((x-ax)*(bx-ax)+(y-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2||1)));
        if((x-ax-t*(bx-ax))**2+(y-ay-t*(by-ay))**2<=radius**2)
          data.set([shade,shade,shade,shade===255?255:alpha],4*(y*width+x));
      }
  }
  for(let i=0;i<points.length;i++)line(points[i],points[(i+1)%points.length],Math.max(1,Math.floor(spacing*.04)),color);
  for(const {coordinate:[x,y],horizontal=false} of gaps) {
    const a=[x-(horizontal?.25:0),y-(horizontal?0:.25)],b=[x+(horizontal?.25:0),y+(horizontal?0:.25)];
    line(a,b,spacing*.125,255);line(a,b,Math.max(1,Math.floor(spacing*.04)),color);
  }
  return image;
}

const actual=recognize(referenceRaster(),{spacing:72});
assert.equal(actual.waypoints.length,10);
assert.equal(actual.crossings.length,3);
assert.equal(actual.recognition.unresolved_crossings,0);
assert.equal(actual.draft,undefined);
assert.deepEqual(recognize(referenceRaster(),{spacing:72}),actual,'raster recognition is deterministic');

const square=[[1,-1],[4,-1],[4,-4],[1,-4]];
for(const spacing of [8,24,40,72,100])for(const origin of [[0,0],[3,5]]) {
  const image=paint(square,{spacing,origin,width:600,height:550});
  const record=recognize(image,{spacing,origin});
  assert.equal(record.waypoints.length,4);
  assert.equal(record.crossings.length,0);
  assert.equal(record.recognition.grid_edges,12);
  assert.deepEqual(record.editor_view.pixel_origin,origin);
}
const fixture=JSON.parse(fs.readFileSync(path.join(root,'examples/image_trace/annotation.json'),'utf8'));
const pts=fixture.waypoints.map(([x,y])=>[x+2,y-2]);
const unresolved=recognize(paint(pts),{spacing:40});
assert.equal(unresolved.draft,true);
assert.equal(unresolved.recognition.unresolved_crossings,3);
assert.equal(unresolved.crossings.length,0,'continuous crosses have no inferred over-strand');
const drawing=box.model.Drawing.load(unresolved);
assert.throws(()=>drawing.record(),/jeder Kreuzung/);
assert.equal(drawing.record(true).draft,true);
for(const c of drawing.crossings())drawing.choose(c.coordinate);
assert.equal(drawing.record().draft,undefined,'review resolves a raster draft');
drawing.undo();assert.equal(drawing.recognition,null,'geometry edits discard stale recognition evidence');

const transparent=paint(square,{alpha:0});
assert.throws(()=>recognize(transparent),/Keine dunkle Linie/,'transparent black is white background');
const gray=paint(square,{color:180});
assert.throws(()=>recognize(gray),/Keine dunkle Linie/);
assert.equal(recognize(gray,{spacing:40,threshold:200}).waypoints.length,4);
const offGrid=paint(square,{origin:[10,10]});
assert.throws(()=>recognize(offGrid,{spacing:40}),/Raster|außerhalb/);
const noise=paint(square);noise.data.set([0,0,0,255],4*(280*320+280));
assert.throws(()=>recognize(noise,{spacing:40}),/außerhalb/);
const open=paint(square);
for(let y=30;y<=50;y++)for(let x=70;x<=90;x++)open.data.set([255,255,255,255],4*(y*320+x));
assert.throws(()=>recognize(open,{spacing:40}),/Offene|Unterbrochene/);
const two=paint(square);
const other=paint([[5,-5],[6,-5],[6,-6],[5,-6]]);
for(let i=0;i<two.data.length;i+=4)if(other.data[i]<160)two.data.set(other.data.subarray(i,i+4),i);
assert.throws(()=>recognize(two,{spacing:40}),/Mehrere/);
for(const options of [{spacing:7},{spacing:101},{spacing:8.5},{origin:[-1,0]},{origin:[24,0]},{threshold:0},{threshold:255}])
  assert.throws(()=>recognize(paint(square),options),/ungültig/);
assert.throws(()=>recognize({width:1201,height:1,data:new Uint8ClampedArray(1201*4)}),/höchstens/);
assert.throws(()=>recognize({width:10,height:10,data:[]}),/höchstens/);

// Exercise the full browser-recognition -> Python validation -> gallery pipeline.
const tempRoot=fs.realpathSync(os.tmpdir());
const directory=fs.mkdtempSync(path.join(tempRoot,'knots-raster-'));
try {
  const records=[actual];
  // Rotations and a mirror exercise both inferred over-strand axes and chirality.
  for(const mirror of [false,true])for(let turns=0;turns<4;turns++) {
    const transform=([x,y])=>{if(mirror)x=-x;for(let k=0;k<turns;k++)[x,y]=[-y,x];return [x+4,y-4];};
    const record=recognize(paint(fixture.waypoints.map(transform),{width:440,height:440,
      gaps:fixture.crossings.map(c=>({coordinate:transform(c.coordinate),horizontal:turns%2===1}))}),{spacing:40});
    assert.equal(record.crossings.length,3);
    records.push(record);
  }
  fs.writeFileSync(path.join(directory,'records.json'),JSON.stringify(records));
  fs.writeFileSync(path.join(directory,'draft.json'),JSON.stringify(unresolved));
  const result=spawnSync('python',['-c',`
import json, sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict, annotation_to_dict, trace_annotation, write_traced_diagram
from knots_grid.classification import classify_knot
from knots_grid.core import trace_turtle
from knots_grid.validator import validate_cycle
root=Path(sys.argv[1])
records=json.loads((root/'records.json').read_text())
names=[]
for record in records:
    annotation=annotation_from_dict(record)
    assert annotation_to_dict(annotation)==record
    trace=trace_annotation(annotation)
    assert validate_cycle(trace.points).is_valid
    assert trace_turtle(trace.code).points==trace.points
    names.append(classify_knot(trace.points).name)
assert len(set(names[:5]))==1 and names[0]=='T(2,3)', names
assert len(set(names[5:]))==1 and names[5]!=names[0], names
try:
    trace_annotation(annotation_from_dict(json.loads((root/'draft.json').read_text())))
except ValueError as error:
    assert 'missing over/under' in str(error)
else:
    raise AssertionError('incomplete draft must not trace')
write_traced_diagram(annotation_from_dict(records[0]), root/'gallery')
metadata=json.loads((root/'gallery'/'trace.json').read_text())
assert metadata['source']=='reviewed_raster_annotation'
assert metadata['classification']['name']=='T(2,3)'
print('Raster-to-grid pipeline: signed trefoil, rotations, mirror, draft rejection, turtle roundtrip and gallery passed.')
`,directory],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
  assert.equal(result.status,0,result.stdout+result.stderr);
  process.stdout.write(result.stdout);
  const gallery=spawnSync('node',[path.join(__dirname,'test_gallery_runtime.cjs'),path.join(directory,'gallery/index.html')],{encoding:'utf8'});
  assert.equal(gallery.status,0,gallery.stdout+gallery.stderr);
} finally {
  assert.equal(path.dirname(fs.realpathSync(directory)),tempRoot,'cleanup stays within the allocated temporary root');
  fs.rmSync(directory,{recursive:true,force:true});
}
console.log('Raster tracer: real PNG, grid origins, thresholds, unresolved choices, bounds and invalid inputs passed.');

async function testUI() {
  const elements={};let downloaded;
  class Element {
    constructor(id){this.id=id;this.value=({spacing:'24','origin-x':'0','origin-y':'0',threshold:'160'})[id]??'';
      this.checked=true;this.width=1104;this.height=720;this.listeners={};this.dataset={};}
    addEventListener(name,fn){this.listeners[name]=fn;}
    setAttribute(name,value){this[name]=value;}
    getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
    getContext(){return new Proxy({getImageData:()=>referenceRaster()},{get:(target,key)=>target[key]??(()=>{})});}
    fire(name,props={}){return this.listeners[name]?.(props);}
    click(){}
  }
  for(const m of html.matchAll(/\bid="([^"]+)"/g))elements[m[1]]=new Element(m[1]);
  Object.assign(box,{
    document:{getElementById:id=>elements[id],createElement:tag=>new Element(tag)},
    Blob:class {constructor(parts){downloaded=parts.join('');}},
    Image:class {constructor(){this.naturalWidth=576;this.naturalHeight=504;}set src(value){this.onload();}},
    URL:{createObjectURL:()=> 'blob:test',revokeObjectURL(){}},setTimeout:fn=>fn(),
  });
  vm.runInContext([...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][1][1],box);
  assert.equal(elements.recognize.disabled,true);
  elements.image.files=[{name:'trefoil_reference.png'}];elements.image.fire('change');
  assert.equal(elements.recognize.disabled,false);
  elements.spacing.value='72';elements.spacing.fire('change');elements.recognize.fire('click');
  assert.equal(elements.status.dataset.error,'false');
  assert.match(elements.status.textContent,/3 eindeutige.*0 offene/);
  assert.equal(elements.download.disabled,false);
  elements.download.fire('click');
  const saved=JSON.parse(downloaded);
  assert.equal(saved.recognition.inferred_crossings,3);
  assert.equal(saved.source_image,'trefoil_reference.png');
  assert.deepEqual(saved.waypoints,actual.waypoints);
  elements.threshold.value='0';elements.recognize.fire('click');
  assert.equal(elements.status.dataset.error,'true','recognition errors are visible');
  elements.download.fire('click');
  assert.deepEqual(JSON.parse(downloaded).waypoints,saved.waypoints,'failed recognition preserves previous drawing');
  elements.import.files=[{text:async()=>JSON.stringify(unresolved)}];await elements.import.fire('change');
  assert.equal(elements.download.disabled,true);
  assert.equal(elements.draft.disabled,false);
  assert.equal(elements.recognize.disabled,true,'import clears the old background image');
  elements.draft.fire('click');assert.equal(JSON.parse(downloaded).draft,true);
  const found=box.model.intersections(unresolved.waypoints);
  for(const c of found)elements.scene.fire('click',{clientX:c.coordinate[0]*40,clientY:-c.coordinate[1]*40});
  assert.equal(elements.download.disabled,false);
  elements.download.fire('click');assert.equal(JSON.parse(downloaded).crossings.length,3);
  assert.equal(JSON.parse(downloaded).draft,undefined);
  console.log('Raster UI: image load, recognition, report, failure recovery, draft import/download and manual completion passed.');
}
testUI().catch(error=>{console.error(error);process.exitCode=1;});
