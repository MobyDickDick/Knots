/* Reproducible AP-06: pixels with crossing gaps -> evidence -> grid/gallery.
 * No manual crossing choices are supplied by this generator.
 */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {spawnSync}=require('node:child_process');
const {paintCurve}=require('./curve_fixture.cjs'),{paintScan,png}=require('./scan_fixture.cjs');
const root=path.join(__dirname,'..'),target=path.join(__dirname,'gap_trace');
const html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8'),box={};vm.createContext(box);
vm.runInContext([...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1]+'\nglobalThis.curve=CurveTracer;globalThis.scan=ScanTracer;globalThis.model=TracerModel;',box);
const image=paintCurve({gapIndices:[0,2,4]}),record=box.curve.recognize(image,{gaps:true});
record.source_image='gapped_trefoil.png';box.model.Drawing.load(record);
const partial=box.curve.recognize(paintCurve({gapIndices:[0]}),{gaps:true});partial.source_image='partial_trefoil.png';
const scan=paintScan({gapIndices:[0,2,4]}),scanRecord=box.scan.recognize(scan,{gaps:true});scanRecord.source_image='simulated_scan.png';
fs.mkdirSync(target,{recursive:true});
for(const [name,value] of [['gapped_trefoil.png',image],['partial_trefoil.png',paintCurve({gapIndices:[0]})],['simulated_scan.png',scan]])
  fs.writeFileSync(path.join(target,name),png(value));
for(const [name,value] of [['annotation.json',record],['draft.json',partial],['scan_annotation.json',scanRecord]])
  fs.writeFileSync(path.join(target,name),JSON.stringify(value,null,2)+'\n');
const overlay={...image,data:image.data.slice()},spacing=record.editor_view.spacing;
for(let i=0;i<record.waypoints.length;i++){
  const a=record.waypoints[i].map((v,k)=>(k?-v:v)*spacing),b=record.waypoints[(i+1)%record.waypoints.length].map((v,k)=>(k?-v:v)*spacing);
  const dx=Math.sign(b[0]-a[0]),dy=Math.sign(b[1]-a[1]);let [x,y]=a;
  while(true){if(x>=0&&y>=0&&x<image.width&&y<image.height)overlay.data.set([0,120,220,255],4*(y*image.width+x));if(x===b[0]&&y===b[1])break;x+=dx;y+=dy;}
}
// Red pixels show the original skeleton endpoints and crossing evidence.
for(const e of record.recognition.crossing_gaps.evidence)for(const [x,y] of [...e.endpoints,e.crossing_pixel])
  for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++)overlay.data.set([215,40,35,255],4*((y+dy)*image.width+x+dx));
fs.writeFileSync(path.join(target,'overlay.png'),png(overlay));
const result=spawnSync('python',['-c',`
import json,sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict,write_traced_diagram,write_tracer_editor
target=Path(sys.argv[1])
write_traced_diagram(annotation_from_dict(json.loads((target/'annotation.json').read_text())),target)
write_tracer_editor(target.parent/'image_tracer.html')
trace=json.loads((target/'trace.json').read_text())
assert trace['classification']['determinant']==3
assert trace['annotation']['recognition']['inferred_crossings']==3
print(f"Gap example: {trace['classification']['name']}, {trace['point_count']} grid vertices, 3 pixel-evidenced crossings")
`,target],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
if(result.status!==0)throw Error(result.stdout+result.stderr);
process.stdout.write(result.stdout);
