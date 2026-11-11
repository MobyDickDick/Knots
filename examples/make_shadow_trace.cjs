// AP-10: abrupt synthetic shadow -> mask -> reviewed trefoil -> offline gallery.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),{spawnSync}=require('node:child_process');
const {paintShadow}=require('./shadow_fixture.cjs'),{png}=require('./scan_fixture.cjs');
const root=path.join(__dirname,'..'),target=path.join(__dirname,'shadow_trace'),box={};vm.createContext(box);
const html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8');
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1]+';globalThis.scan=ScanTracer;globalThis.pre=ScanPreprocessor;globalThis.model=TracerModel;',box);
const image=paintShadow(),prepared=box.pre.prepare(image,{directional:true}),draft=box.scan.recognize(image,{directional:true});
draft.source_image='abrupt_shadow.png';
// Explicit review for this particular alternating trefoil, not inferred from shading.
const visits=box.model.intersections(draft.waypoints).flatMap(c=>c.segments.map(segment=>({c,segment}))).sort((a,b)=>a.segment-b.segment);
const record=JSON.parse(JSON.stringify(draft));delete record.draft;
record.crossings=visits.filter((_,i)=>i%2===0).map(({c,segment})=>({coordinate:c.coordinate,over_segment:segment}));box.model.Drawing.load(record);
fs.mkdirSync(target,{recursive:true});
for(const [name,value] of [['draft',draft],['annotation',record]])fs.writeFileSync(path.join(target,name+'.json'),JSON.stringify(value,null,2)+'\n');
fs.writeFileSync(path.join(target,'abrupt_shadow.png'),png(image));fs.writeFileSync(path.join(target,'mask.png'),png(prepared.image));
const overlay={...image,data:image.data.slice()},spacing=record.editor_view.spacing;
for(let i=0;i<record.waypoints.length;i++){
  const a=record.waypoints[i].map((v,k)=>(k?-v:v)*spacing),b=record.waypoints[(i+1)%record.waypoints.length].map((v,k)=>(k?-v:v)*spacing);
  const dx=Math.sign(b[0]-a[0]),dy=Math.sign(b[1]-a[1]);let [x,y]=a;
  while(true){if(x>=0&&y>=0&&x<image.width&&y<image.height)overlay.data.set([0,120,220,255],4*(y*image.width+x));if(x===b[0]&&y===b[1])break;x+=dx;y+=dy;}
}
fs.writeFileSync(path.join(target,'overlay.png'),png(overlay));
const result=spawnSync('python',['-c',`
import json,sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict,write_traced_diagram,write_tracer_editor
target=Path(sys.argv[1])
write_traced_diagram(annotation_from_dict(json.loads((target/'annotation.json').read_text())),target)
write_tracer_editor(target.parent/'image_tracer.html')
trace=json.loads((target/'trace.json').read_text())
assert trace['classification']['name']=='T(2,3)'
assert trace['annotation']['recognition']['preprocessing']['algorithm']=='local-quadrant-v1'
print(f"Shadow example: {trace['classification']['name']}, {trace['point_count']} vertices, 3 manually reviewed crossings")
`,target],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
if(result.status!==0)throw Error(result.stdout+result.stderr);process.stdout.write(result.stdout);
