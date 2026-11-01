// Exercise the exported viewer without a browser or external dependencies.
// This checks drawing/event contracts; it does not replace visual browser QA.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const html = fs.readFileSync(process.argv[2] || path.join(__dirname, '../examples/knot_gallery.html'), 'utf8');
const dataPattern = /\/\* KNOT_DATA_START \*\/([\s\S]*?)\/\* KNOT_DATA_END \*\//;
const payload = html.match(dataPattern)[1];
const source = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const knots = JSON.parse(payload);
let drawings = 0;

class Element {
  constructor(tag) {
    this.tag = tag;
    this.attributes = {};
    this.children = [];
    this.listeners = {};
    this.value = '';
    this.checked = false;
    this.rect = {width: tag === 'canvas' ? 760 : 350, height: 460};
    this.context = {
      lines: [],
      setTransform() {},
      beginPath() {},
      moveTo(x,y) { this.start = [x,y]; },
      lineTo(x,y) { this.end = [x,y]; },
      stroke() {
        assert.ok([...this.start,...this.end].every(Number.isFinite), 'finite canvas coordinates');
        this.lines.push([this.start,this.end,this.strokeStyle,this.lineWidth]);
        drawings++;
      },
    };
  }
  set width(value) { this.pixelWidth = value; this.context.lines = []; }
  set height(value) { this.pixelHeight = value; this.context.lines = []; }
  getContext() { return this.context; }
  getBoundingClientRect() { return this.rect; }
  setAttribute(key,value) { this.attributes[key] = value; }
  addEventListener(type,listener) { (this.listeners[type] ||= []).push(listener); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  querySelector(tag) { return this.children.find(child => child.tag === tag); }
  setPointerCapture(id) { this.captured = id; }
  fire(type, props = {}) {
    let prevented = false;
    const event = {preventDefault() { prevented = true; }, ...props};
    for (const listener of this.listeners[type] || []) listener(event);
    return prevented;
  }
}

function startViewer({data=payload, resizeSupport=true, canvasSupport=true} = {}) {
const elements = {};
for (const match of html.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="([^"]+)"[^>]*)>/g)) {
  const element = elements[match[3]] = new Element(match[1]);
  element.value = match[2].match(/\bvalue="([^"]+)"/)?.[1] || '';
  element.checked = /\bchecked\b/.test(match[2]);
}
for (const match of html.matchAll(/<a class="knot-card" href="([^"]+)"/g)) {
  const card = new Element('a');
  card.setAttribute('href',match[1]);
  elements.knots.append(card);
}
if (!canvasSupport) elements.scene.getContext = () => null;
const observers = [];
const windowListeners = {};
const context = {
  JSON: {parse() {throw new Error('DOM JSON parsing must not be needed');}},
  document: {
    getElementById(id) { assert.ok(elements[id], `known element ${id}`); return elements[id]; },
    createElement(tag) { return new Element(tag); },
    createTextNode(text) { return {textContent:text}; },
  },
  window: {devicePixelRatio:2, addEventListener(type,handler) {windowListeners[type]=handler;}},
  ResizeObserver: class {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe(element) { this.element = element; this.callback(); }
  },
};
if (!resizeSupport) delete context.ResizeObserver;
const script = source.replace(dataPattern, () => '/* KNOT_DATA_START */'+data+'/* KNOT_DATA_END */');
vm.runInNewContext(script, context);
return {elements,observers,windowListeners};
}

const {elements,observers} = startViewer();
assert.equal(elements['gallery-status'].hidden, true, 'viewer initialized without a hidden startup error');

const scene = elements.scene;
const snapshot = () => JSON.stringify(scene.context.lines);
const cards = elements.knots.children;
assert.equal(cards.length, knots.length);
assert.ok(drawings > 0);
assert.equal(elements['mode-3d'].attributes['aria-pressed'], 'true');

const initial = snapshot();
const selectedKnot=knots[knots.length>1?1:0];
if(selectedKnot.metadata?.source==='manual_image_annotation') {
  assert.equal(elements['version-control'].hidden,true);
  assert.equal(elements['classification-evidence'].hidden,false);
  assert.ok(elements['classification-evidence'].textContent.includes('Bildvorlage'));
  assert.ok(elements.details.children.some(child=>child.children.some(item=>item.textContent==='Bild-Abzeichner')));
}
if(selectedKnot.original_points) {
  assert.equal(elements['version-control'].hidden,false);
  elements['version-original'].fire('click');
  assert.equal(elements['version-original'].attributes['aria-pressed'],'true');
  assert.ok(elements.details.children.some(child=>child.children.some(
    item=>item.textContent===String(selectedKnot.original_points.length-1))), 'original point count displayed');
  if(JSON.stringify(selectedKnot.original_points)!==JSON.stringify(selectedKnot.points)) {
    assert.notEqual(snapshot(),initial,'original toggle draws original coordinates');
  }
  elements['version-best'].fire('click');
  assert.equal(snapshot(),initial,'best toggle restores result coordinates');
  assert.equal(elements['classification-evidence'].hidden,false);
}
scene.fire('pointerdown', {clientX:100,clientY:100,pointerId:1});
scene.fire('pointermove', {clientX:170,clientY:140,pointerId:1});
assert.notEqual(snapshot(), initial, 'drag rotates the drawing');
scene.fire('pointerup', {pointerId:1});
const afterDrag = snapshot();
scene.fire('pointermove', {clientX:200,clientY:160,pointerId:1});
assert.equal(snapshot(), afterDrag, 'released drag stops rotating');
assert.equal(scene.fire('keydown', {key:'ArrowLeft'}), true);
assert.notEqual(snapshot(), afterDrag, 'keyboard rotates');

const beforeZoom = snapshot();
assert.equal(scene.fire('wheel', {deltaY:-100}), true);
assert.notEqual(snapshot(), beforeZoom, 'wheel zooms');
elements.reset.fire('click');
assert.equal(snapshot(), initial, 'reset restores initial camera');

elements.gap.value = '3';
elements.gap.fire('input');
assert.notEqual(snapshot(), initial, 'layer gap changes the view');
assert.equal(elements['gap-value'].textContent, '3,0');
elements.reset.fire('click');

elements['mode-2d'].fire('click');
assert.equal(elements['gap-control'].hidden, true);
assert.equal(elements.gap.disabled, true);
const flat = snapshot();
scene.fire('pointerdown', {clientX:100,clientY:100,pointerId:2});
scene.fire('pointermove', {clientX:160,clientY:180,pointerId:2});
assert.equal(snapshot(), flat, '2-D mode does not orbit');
assert.equal(scene.fire('keydown', {key:'ArrowLeft'}), false);

cards[0].fire('click');
assert.equal(cards[0].attributes['aria-pressed'], 'true');
assert.equal(elements['selected-name'].textContent, knots[0].name==='unknown'?'Kandidat 001 · ungeklärt':knots[0].name==='0_1'?'0₁ · Unknoten':knots[0].name);
elements.grid.checked = false;
elements.grid.fire('change');
assert.equal(scene.context.lines.length, 2*(knots[0].points.length-1), 'grid toggle leaves every knot edge');
elements['mode-3d'].fire('click');
assert.equal(elements['gap-control'].hidden, false);

// Simulate resizing to a narrow drawing area and ensure finite output.
scene.rect = {width:320,height:350};
for (const observer of observers) observer.callback();
assert.equal(scene.pixelWidth, 640);
assert.equal(scene.pixelHeight, 700);
assert.equal(source.match(dataPattern)[1], payload, 'all source lattice points are unchanged');
const olderBrowser = startViewer({resizeSupport:false});
assert.equal(olderBrowser.elements['gallery-status'].hidden, true, 'ResizeObserver is optional');
assert.equal(typeof olderBrowser.windowListeners.resize, 'function');
olderBrowser.windowListeners.resize();

for (const options of [{data:'null'}, {canvasSupport:false}]) {
  const failed = startViewer(options).elements;
  assert.equal(failed['gallery-status'].hidden, false, 'startup error is visible');
  assert.match(failed['gallery-status'].textContent, /konnte nicht starten/);
  assert.equal(failed['static-preview'].hidden, false);
  assert.equal(failed['static-catalog'].hidden, false);
  assert.equal(failed.knots.children.length, knots.length, 'startup failure preserves the complete catalog');
  assert.ok(failed.knots.children.every(card => card.attributes.href?.startsWith('#static-knot-')));
  assert.equal(failed['mode-3d'].disabled, true);
}
console.log('Gallery runtime: selection, camera controls, resize, compatibility and startup-error fallbacks passed.');
