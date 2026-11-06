// A simulated scan with a broad shadow and deterministic, weak paper texture.
const {paintCurve}=require('./curve_fixture.cjs');
const zlib=require('node:zlib');
function paintScan({texture=6,shadow=100,...options}={}){
  const clean=paintCurve(options),image={...clean,data:clean.data.slice()};
  for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++){
    const i=4*(y*image.width+x),paper=245-shadow*(1-x/(image.width-1))
      +texture*(Math.sin(x*.73+y*.37)+Math.cos(x*.17-y*.61))/2;
    const value=Math.round(paper*(.25+.75*clean.data[i]/255));
    image.data.set([value,value,value,255],i);
  }
  return image;
}
function png({data,width,height}){
  function crc(bytes){let c=0xffffffff;for(const b of bytes){c^=b;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
  function chunk(type,body){const tag=Buffer.from(type),length=Buffer.alloc(4),sum=Buffer.alloc(4);length.writeUInt32BE(body.length);sum.writeUInt32BE(crc(Buffer.concat([tag,body])));return Buffer.concat([length,tag,body,sum]);}
  const header=Buffer.alloc(13);header.writeUInt32BE(width);header.writeUInt32BE(height,4);header[8]=8;header[9]=6;
  const rows=Buffer.alloc(height*(width*4+1));
  for(let y=0;y<height;y++)rows.set(data.subarray(y*width*4,(y+1)*width*4),y*(width*4+1)+1);
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(rows)),chunk('IEND',Buffer.alloc(0))]);
}
module.exports={paintScan,png};
