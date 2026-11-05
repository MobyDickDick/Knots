/* Rebuild a clean curved-image -> reviewed annotation -> grid/gallery example.
 * Run: node examples/make_curve_trace.cjs (Node and Python, no extra packages).
 * Crossing choices below are an explicit review step for this reference only.
 */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),zlib=require('node:zlib');
const {spawnSync}=require('node:child_process');
const {paintCurve}=require('./curve_fixture.cjs');
const root=path.join(__dirname,'..'),target=path.join(__dirname,'curve_trace');
const html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8'),box={};vm.createContext(box);
vm.runInContext([...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1]+'\nglobalThis.curve=CurveTracer;globalThis.model=TracerModel;',box);
const image=paintCurve(),draft=box.curve.recognize(image);
draft.source_image='curved_trefoil.png';
// This reference is reviewed as an alternating three-crossing trefoil. The
// recognizer deliberately supplies no over/under evidence for solid crossings.
const crossings=box.model.intersections(draft.waypoints);
const visits=crossings.flatMap(c=>c.segments.map(segment=>({c,segment}))).sort((a,b)=>a.segment-b.segment);
const record=JSON.parse(JSON.stringify(draft));delete record.draft;
record.crossings=visits.filter((_,i)=>i%2===0).map(({c,segment})=>({coordinate:c.coordinate,over_segment:segment}));
box.model.Drawing.load(record);
function png({data,width,height}){
  function crc(bytes){let c=0xffffffff;for(const b of bytes){c^=b;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
  function chunk(type,body){const tag=Buffer.from(type),length=Buffer.alloc(4),sum=Buffer.alloc(4);length.writeUInt32BE(body.length);sum.writeUInt32BE(crc(Buffer.concat([tag,body])));return Buffer.concat([length,tag,body,sum]);}
  const header=Buffer.alloc(13);header.writeUInt32BE(width);header.writeUInt32BE(height,4);header[8]=8;header[9]=6;
  const rows=Buffer.alloc(height*(width*4+1));
  for(let y=0;y<height;y++)rows.set(data.subarray(y*width*4,(y+1)*width*4),y*(width*4+1)+1);
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(rows)),chunk('IEND',Buffer.alloc(0))]);
}
fs.mkdirSync(target,{recursive:true});
fs.writeFileSync(path.join(target,'curved_trefoil.png'),png(image));
fs.writeFileSync(path.join(target,'draft.json'),JSON.stringify(draft,null,2)+'\n');
fs.writeFileSync(path.join(target,'annotation.json'),JSON.stringify(record,null,2)+'\n');
// A reproducible overlay for visual QA of the curve-to-grid approximation.
const overlay={...image,data:image.data.slice()},spacing=record.editor_view.spacing;
for(let i=0;i<record.waypoints.length;i++){
  const a=record.waypoints[i].map((v,k)=>(k?-v:v)*spacing),b=record.waypoints[(i+1)%record.waypoints.length].map((v,k)=>(k?-v:v)*spacing);
  const dx=Math.sign(b[0]-a[0]),dy=Math.sign(b[1]-a[1]);let [x,y]=a;
  while(true){if(x>=0&&y>=0&&x<image.width&&y<image.height)overlay.data.set([0,120,220,255],4*(y*image.width+x));if(x===b[0]&&y===b[1])break;x+=dx;y+=dy;}
}
fs.writeFileSync(path.join(target,'overlay.png'),png(overlay));
const result=spawnSync('python',['-c',`
import json, sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict, write_traced_diagram, write_tracer_editor
target=Path(sys.argv[1])
write_traced_diagram(annotation_from_dict(json.loads((target/'annotation.json').read_text())),target)
write_tracer_editor(target.parent/'image_tracer.html')
trace=json.loads((target/'trace.json').read_text())
assert trace['classification']['determinant']==3
print(f"Curve example: {trace['classification']['name']}, {trace['point_count']} grid vertices, 3 manually reviewed crossings")
`,target],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
if(result.status!==0)throw Error(result.stdout+result.stderr);
process.stdout.write(result.stdout);
