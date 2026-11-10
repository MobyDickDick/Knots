// Small isolated ink marks on a simulated scan; no semantic text recognition.
const {paintScan}=require('./scan_fixture.cjs');
function paintCleanupScan(options={}){
  const image=paintScan(options);
  for(const [x0,y0] of [[20,20],[50,20],[80,20]])
    for(let y=y0;y<y0+3;y++)for(let x=x0;x<x0+3;x++)image.data.set([0,0,0,255],4*(y*image.width+x));
  return image;
}
module.exports={paintCleanupScan};
