const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname,'../src/knots_grid/image_tracer.html'),'utf8');
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(scripts[0]+'\nglobalThis.model=TracerModel;',sandbox);
const {Drawing,intersections} = sandbox.model;
const plain = value=>JSON.parse(JSON.stringify(value));
const fixture = {
  schema_version:1,source_image:null,
  waypoints:[[0,0],[3,0],[3,-2],[1,-2],[1,1],[4,1],[4,-1],[2,-1],[2,-3],[0,-3]],
  crossings:[{coordinate:[1,0],over_segment:3},{coordinate:[2,-2],over_segment:7},{coordinate:[3,-1],over_segment:1}],
};
const drawing = Drawing.load(fixture);
assert.deepEqual(plain(drawing.record()),fixture,'load/save preserves all annotation data');
assert.equal(drawing.crossings().length,3);
drawing.choose([1,0]);
assert.equal(drawing.record().crossings[0].over_segment,0,'click toggles over-strand');
drawing.choose([1,0]);
assert.equal(drawing.record().crossings[0].over_segment,3);
const restored=Drawing.load(JSON.parse(JSON.stringify(drawing.record())));
assert.deepEqual(plain(restored.record()),fixture);
restored.undo();
assert.equal(restored.closed,false);
assert.equal(restored.points.length,9);
assert.equal(restored.choices.size,0,'point edits invalidate crossing choices');
assert.throws(()=>restored.record(),/schließen/);
assert.throws(()=>Drawing.load({...fixture,crossings:[]}),/jeder Kreuzung/);
assert.throws(()=>Drawing.load({...fixture,crossings:[...fixture.crossings,fixture.crossings[0]]}),/passt nicht/);
assert.throws(()=>Drawing.load({...fixture,crossings:[{coordinate:[1,0],over_segment:7}]}),/passt nicht/);
assert.throws(()=>Drawing.load({...fixture,schema_version:true}),/Version 1/);
assert.throws(()=>intersections([[0,0],[3,0],[1,0],[1,2],[0,2]]),/überlappen/);
assert.throws(()=>intersections([[0,0],[4,0],[4,4],[2,4],[2,0],[1,0],[1,-2],[0,-2]]),/Endpunkt/);
assert.throws(()=>intersections([[0,0],[2,1],[2,2],[0,2]]),/waagerecht/);
const view={spacing:24,width:800,height:600,offset:[2,3]};
assert.deepEqual(plain(Drawing.load({...fixture,editor_view:view}).record().editor_view),view);
assert.throws(()=>Drawing.load({...fixture,editor_view:{...view,width:50000}}),/Einstellungen/);
const square=new Drawing();
square.add([0,0]);square.add([3,1]);square.add([4,3]);square.add([0,4]);
assert.deepEqual(plain(square.points),[[0,0],[3,0],[3,3],[0,3]],'clicks snap to orthogonal segments');
assert.throws(()=>square.record(),/schließen/);
square.close();
assert.equal(square.record().crossings.length,0);
assert.throws(()=>square.add([0,0]),/zurücknehmen/);
assert.throws(()=>square.choose([1,1]),/Keine Kreuzung/);
console.log('Image tracer model: annotation editing, crossing choices, invalid geometry and JSON roundtrip passed.');

// Run the UI and its actual click handlers against a small browser API double.
const elements={};
class Element {
  constructor(id){this.id=id;this.value=id==='spacing'?'24':'';this.checked=true;this.width=1104;this.height=720;this.listeners={};this.dataset={};}
  addEventListener(name,fn){this.listeners[name]=fn;}
  setAttribute(name,value){this[name]=value;}
  getBoundingClientRect(){return {left:0,top:0,width:this.width,height:this.height};}
  getContext(){return new Proxy({}, {get(target,key){return target[key]??(()=>{});}});}
  fire(name,props={}){return this.listeners[name]?.(props);}
  click(){this.clicked=true;}
}
for(const match of html.matchAll(/\bid="([^"]+)"/g))elements[match[1]]=new Element(match[1]);
let downloaded;
Object.assign(sandbox,{
  document:{getElementById(id){assert.ok(elements[id],id);return elements[id];},createElement(){return new Element('link');}},
  Blob:class {constructor(parts){downloaded=parts.join('');}},
  URL:{createObjectURL(){return 'blob:test';},revokeObjectURL(){}},setTimeout(fn){fn();},
});
vm.runInContext(scripts[1],sandbox);
const canvas=elements.scene;
for(const [clientX,clientY] of [[24,24],[120,24],[120,120],[24,120]])canvas.fire('click',{clientX,clientY});
elements.close.fire('click');
assert.equal(elements.download.disabled,false,'closed crossing-free drawing can be saved');
elements.download.fire('click');
const saved=JSON.parse(downloaded);
assert.deepEqual(saved.waypoints,[[0,0],[4,0],[4,-4],[0,-4]]);
assert.equal(saved.editor_view.spacing,24,'pixel alignment is saved');
elements.undo.fire('click');
assert.equal(elements.download.disabled,true);
elements.clear.fire('click');
elements.close.fire('click');
assert.equal(elements.status.dataset.error,'true','invalid closure is visible');
assert.equal(elements.download.disabled,true);
console.log('Image tracer UI: click-to-draw, closure, download, undo and visible errors passed.');
