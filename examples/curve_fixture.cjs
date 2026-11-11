// Deterministic clean curved diagrams for the example and runtime acceptance.
// No image libraries: paint sampled parametric curves with round strokes.
function paintCurve({kind='trefoil',width=560,height=560,scale=75,radius=3,
  rotation=0,mirror=false,color=25,alpha=255,open=false,offset=[0,0],gapIndices=[],gapHalf=15,lineBreaks=[],lineGapHalf=11,straightBreak=false}={}) {
  const data=new Uint8ClampedArray(width*height*4);data.fill(255);
  const samples=[];
  for(let i=0;i<=2400;i++){
    const t=i*2*Math.PI/2400;
    let x,y;
    if(kind==='circle'){x=2*Math.cos(t);y=1.7*Math.sin(t);}
    else {x=(2+Math.cos(3*t))*Math.cos(2*t);y=(2+Math.cos(3*t))*Math.sin(2*t);}
    // AP-09 fixture: a genuinely straight arc around t=0, smoothly joined.
    if(straightBreak){const angle=Math.abs(Math.atan2(Math.sin(t),Math.cos(t)));
      if(angle<.3){const weight=Math.min(1,Math.max(0,(angle-.2)/.1));x=3+(x-3)*weight;}}
    if(mirror)x=-x;
    [x,y]=[x*Math.cos(rotation)-y*Math.sin(rotation),x*Math.sin(rotation)+y*Math.cos(rotation)];
    const p=[width/2+scale*x+offset[0],height/2+scale*y+offset[1]];samples.push(p);
    if(open&&i>80&&i<200)continue;
    if(lineBreaks.some(angle=>Math.abs(Math.atan2(Math.sin(t-angle),Math.cos(t-angle)))<lineGapHalf/(5*scale)))continue;
    if(kind==='trefoil'&&gapIndices.some(n=>Math.abs(Math.atan2(Math.sin(t-(Math.PI/6+n*Math.PI/3)),Math.cos(t-(Math.PI/6+n*Math.PI/3))))<gapHalf/(5*scale)))continue;
    const [cx,cy]=p;
    for(let y=Math.max(0,Math.floor(cy-radius));y<=Math.min(height-1,Math.ceil(cy+radius));y++)
      for(let x=Math.max(0,Math.floor(cx-radius));x<=Math.min(width-1,Math.ceil(cx+radius));x++)
        if((x-cx)**2+(y-cy)**2<=radius**2)data.set([color,color,color,alpha],4*(y*width+x));
  }
  return {width,height,data};
}
module.exports={paintCurve};
