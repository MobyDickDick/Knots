// Synthetic abrupt shadow boundaries, independent of the underlying ink geometry.
const {paintCurve}=require('./curve_fixture.cjs');
function shade(image,{axis='vertical',boundary=280,dark=150,bright=245,texture=3}={}){
  const result={...image,data:image.data.slice()};
  for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++){
    const i=4*(y*image.width+x),position=axis==='horizontal'?y:axis==='diagonal'?x+y:x;
    const paper=(position<boundary?dark:bright)+texture*(Math.sin(x*.73+y*.37)+Math.cos(x*.17-y*.61))/2;
    for(let c=0;c<3;c++)result.data[i+c]=Math.round(paper*(.2+.8*image.data[i+c]/255));
  }
  return result;
}
function paintShadow({axis,boundary,dark,bright,texture,...curve}={}){
  return shade(paintCurve(curve),{axis,boundary,dark,bright,texture});
}
module.exports={shade,paintShadow};
