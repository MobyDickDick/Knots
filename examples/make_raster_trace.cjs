/* Rebuild an automatically recognized raster -> annotation -> grid/gallery example.
 * Run: node examples/make_raster_trace.cjs (Python and Node, no extra packages).
 */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),zlib=require('node:zlib');
const {spawnSync}=require('node:child_process');
const root=path.join(__dirname,'..'),target=path.join(__dirname,'raster_trace');
const png=fs.readFileSync(path.join(__dirname,'image_trace/trefoil_reference.png'));
const width=png.readUInt32BE(16),height=png.readUInt32BE(20),parts=[];
// The repository's reference PNG is RGB8 with unfiltered rows.
if(png[24]!==8||png[25]!==2)throw Error('Expected RGB8 reference PNG');
for(let i=8;i<png.length;){const size=png.readUInt32BE(i);if(png.toString('ascii',i+4,i+8)==='IDAT')parts.push(png.subarray(i+8,i+8+size));i+=size+12;}
const rgb=zlib.inflateSync(Buffer.concat(parts)),data=new Uint8ClampedArray(width*height*4);
for(let y=0;y<height;y++) {
  if(rgb[y*(1+width*3)]!==0)throw Error('Expected unfiltered reference PNG');
  for(let x=0;x<width;x++){const k=y*(1+width*3)+1+3*x;data.set([rgb[k],rgb[k+1],rgb[k+2],255],4*(y*width+x));}
}
const html=fs.readFileSync(path.join(root,'src/knots_grid/image_tracer.html'),'utf8');
const box={};vm.createContext(box);
vm.runInContext([...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1]+'\nglobalThis.raster=RasterTracer;',box);
const record=box.raster.recognizeAuto({data,width,height});
record.source_image='trefoil_reference.png';
if(record.draft)throw Error('Reference should have three unambiguous crossing gaps');
fs.mkdirSync(target,{recursive:true});
fs.writeFileSync(path.join(target,'annotation.json'),JSON.stringify(record,null,2)+'\n');
fs.writeFileSync(path.join(target,record.source_image),png);
const result=spawnSync('python',['-c',`
import json, sys
from pathlib import Path
from knots_grid.image_tracer import annotation_from_dict, write_traced_diagram, write_tracer_editor
target=Path(sys.argv[1])
annotation=annotation_from_dict(json.loads((target/'annotation.json').read_text()))
write_traced_diagram(annotation, target)
write_tracer_editor(target.parent/'image_tracer.html')
trace=json.loads((target/'trace.json').read_text())
print(f"Raster example: {trace['classification']['name']}, {trace['point_count']} grid vertices, {len(annotation.crossings)} inferred crossings")
`,target],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
if(result.status!==0)throw Error(result.stdout+result.stderr);
process.stdout.write(result.stdout);
