/* Nova Prime — world map (prerendered, antimeridian-clean) with routes converging to Japan */
(function(){
  var canvas = document.getElementById('worldmap-canvas');
  if(!canvas) return;
  var ctx = canvas.getContext('2d');
  var IMGW = 2400, IMGH = 1200;           // source map ratio 2:1
  var dpr, W, H, sW, sH, ox, oy;

  var img = new Image();
  var ready = false;
  img.onload = function(){ ready = true; };
  img.src = 'img/worldmap.png';

  var TOKYO = [139, 36];
  var ORIGINS = [
    [-74,40.7],[-118,34],[-0.1,51.5],[2.3,48.9],[9.2,45.5],[12.5,41.9],
    [55.3,25.2],[103.8,1.3],[151.2,-33.9],[-46.6,-23.5],[127,37.5]
  ];

  function resize(){
    dpr = Math.min(window.devicePixelRatio||1, 2);
    W = canvas.clientWidth*dpr; H = canvas.clientHeight*dpr;
    canvas.width = W; canvas.height = H;
    var scale = Math.max(W/IMGW, H/IMGH);   // cover
    sW = IMGW*scale; sH = IMGH*scale;
    ox = (W-sW)/2; oy = (H-sH)/2;
  }

  function project(lon, lat){
    return [ ox + (lon+180)/360*sW, oy + (90-lat)/180*sH ];
  }

  function arcPath(a, b, lift){
    var pa = project(a[0],a[1]), pb = project(b[0],b[1]);
    var mx = (pa[0]+pb[0])/2, my = (pa[1]+pb[1])/2;
    var dx = pb[0]-pa[0], dy = pb[1]-pa[1];
    var dist = Math.sqrt(dx*dx+dy*dy) || 1;
    var nx = -dy/dist, ny = dx/dist;
    if(ny > 0){ nx=-nx; ny=-ny; }            // bias curve upward
    return { pa:pa, pb:pb, cx:mx+nx*dist*lift, cy:my+ny*dist*lift };
  }

  var ARCS = ORIGINS.map(function(o,i){ return { o:o, lift:0.18+(i%3)*0.07, phase:(i*7)%40 }; });
  var t = 0;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function frame(){
    ctx.clearRect(0,0,W,H);
    if(ready){
      ctx.globalAlpha = 0.5;
      ctx.drawImage(img, ox, oy, sW, sH);
      ctx.globalAlpha = 1;
    }

    var hub = project(TOKYO[0],TOKYO[1]);

    for(var i=0;i<ARCS.length;i++){
      var A = ARCS[i], p = arcPath(A.o, TOKYO, A.lift);
      ctx.beginPath(); ctx.moveTo(p.pa[0],p.pa[1]); ctx.quadraticCurveTo(p.cx,p.cy,p.pb[0],p.pb[1]);
      ctx.lineWidth = Math.max(1, dpr*0.7); ctx.strokeStyle = 'rgba(215,180,106,0.20)'; ctx.setLineDash([]); ctx.stroke();

      ctx.beginPath(); ctx.moveTo(p.pa[0],p.pa[1]); ctx.quadraticCurveTo(p.cx,p.cy,p.pb[0],p.pb[1]);
      ctx.lineWidth = Math.max(1.2, dpr*1.1); ctx.strokeStyle = 'rgba(241,220,168,0.9)';
      ctx.setLineDash([2*dpr, 12*dpr]); ctx.lineDashOffset = reduce ? 0 : -(t*2 + A.phase)*dpr; ctx.stroke();

      ctx.setLineDash([]);
      var pulse = reduce ? 1 : (0.6+0.4*Math.sin((t*0.06)+i));
      ctx.beginPath(); ctx.arc(p.pa[0],p.pa[1], dpr*2.4, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(215,180,106,'+(0.5*pulse+0.3)+')'; ctx.fill();
    }

    var hp = reduce ? 1 : (0.7+0.3*Math.sin(t*0.08));
    ctx.beginPath(); ctx.arc(hub[0],hub[1], dpr*9*hp, 0, Math.PI*2);
    ctx.strokeStyle='rgba(241,220,168,'+(0.4*hp)+')'; ctx.lineWidth=dpr; ctx.stroke();
    ctx.beginPath(); ctx.arc(hub[0],hub[1], dpr*4.5, 0, Math.PI*2);
    ctx.fillStyle='#f1dca8'; ctx.shadowColor='rgba(241,220,168,0.9)'; ctx.shadowBlur=dpr*16; ctx.fill(); ctx.shadowBlur=0;

    t += 1;
    if(!reduce) requestAnimationFrame(frame);
  }

  resize();
  window.addEventListener('resize', resize);
  // wait for image, then start
  if(img.complete) ready = true;
  requestAnimationFrame(frame);
  if(reduce){ img.addEventListener('load', function(){ frame(); }); }
})();
