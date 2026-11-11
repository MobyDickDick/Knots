/* AP-09 acceptance: a long interrupted trefoil, crossing evidence and scan variant. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {spawnSync}=require('node:child_process');
const {paintCurve}=require('./curve_fixture.cjs'),{paintScan,png}=require('./scan_fixture.cjs');
const root=path.join(__dirname,'..'),target=path.join(__dirname,'long_line_gap_trace');
const html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8'),box={};vm.createContext(box);
vm.runInContext([...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1]+';globalThis.curve=CurveTracer;globalThis.scan=ScanTracer;globalThis.model=TracerModel;',box);
const options={straightBreak:true,lineGapHalf:22,lineBreaks:[0],gapIndices:[0,2,4]},recognition={gaps:true,lineGaps:true,maxLineGap:64};
const image=paintCurve(options),record=box.curve.recognize(image,recognition);record.source_image='interrupted_trefoil.png';box.model.Drawing.load(record);
const partialImage=paintCurve({straightBreak:true,lineGapHalf:22,lineBreaks:[0]}),partial=box.curve.recognize(partialImage,recognition);partial.source_image='partial_trefoil.png';
const scan=paintScan(options),scanRecord=box.scan.recognize(scan,recognition);scanRecord.source_image='simulated_scan.png';
fs.mkdirSync(target,{recursive:true});
for(const [name,value] of [['interrupted_trefoil.png',image],['partial_trefoil.png',partialImage],['simulated_scan.png',scan]])fs.writeFileSync(path.join(target,name),png(value));
for(const [name,value] of [['annotation.json',record],['draft.json',partial],['scan_annotation.json',scanRecord]])fs.writeFileSync(path.join(target,name),JSON.stringify(value,null,2)+'\n');
const overlay={...image,data:image.data.slice()},spacing=record.editor_view.spacing;
function line(a,b,color){
  const n=Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1]));
  for(let i=0;i<=n;i++){
    const [x,y]=a.map((v,k)=>Math.round(v+(b[k]-v)*i/n));
    if(x>=0&&y>=0&&x<image.width&&y<image.height)overlay.data.set(color,4*(y*image.width+x));
  }
}
for(let i=0;i<record.waypoints.length;i++)line(record.waypoints[i].map((v,k)=>(k?-v:v)*spacing),record.waypoints[(i+1)%record.waypoints.length].map((v,k)=>(k?-v:v)*spacing),[0,120,220,255]);
for(const e of record.recognition.line_gaps.evidence){
  line(...e.endpoints,[215,40,35,255]);
  for(const [x,y] of e.endpoints)for(let dy=-3;dy<=3;dy++)for(let dx=-3;dx<=3;dx++)overlay.data.set([215,40,35,255],4*((y+dy)*image.width+x+dx));
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
assert trace['source']=='reviewed_line_gap_annotation'
assert len(trace['annotation']['recognition']['line_gaps']['evidence'])==1
print(f"Long line gap example: {trace['classification']['name']}, {trace['point_count']} grid vertices, 1 line repair, 3 pixel-evidenced crossings")
`,target],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
if(result.status!==0)throw Error(result.stdout+result.stderr);process.stdout.write(result.stdout);
