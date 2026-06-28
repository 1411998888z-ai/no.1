/* Nova Prime — world map with global routes converging to Japan (equirectangular, real coastlines) */
(function(){
  var canvas = document.getElementById('worldmap-canvas');
  if(!canvas || typeof window.LAND === 'undefined') return;
  var LAND = window.LAND;
  var ctx = canvas.getContext('2d');
  var dpr, W, H, mapW, mapH, ox, oy, off, octx;

  // global origins -> all converge to Japan
  var TOKYO = [139, 36];
  var ORIGINS = [
    [-74, 40.7],   // New York
    [-118, 34],    // Los Angeles
    [-0.1, 51.5],  // London
    [2.3, 48.9],   // Paris
    [9.2, 45.5],   // Milan
    [12.5, 41.9],  // Rome
    [55.3, 25.2],  // Dubai
    [103.8, 1.3],  // Singapore
    [151.2, -33.9],// Sydney
    [-46.6, -23.5],// Sao Paulo
    [127, 37.5]    // Seoul
  ];

  function project(lon, lat){
    return [ ox + (lon+180)/360*mapW, oy + (90-lat)/180*mapH ];
  }

  function buildMap(){
    off = document.createElement('canvas');
    off.width = W; off.height = H;
    octx = off.getContext('2d');
    octx.clearRect(0,0,W,H);
    // faint land
    octx.beginPath();
    for(var r=0;r<LAND.length;r++){
      var ring = LAND[r], p;
      for(var i=0;i<ring.length;i++){
        p = project(ring[i][0], ring[i][1]);
        if(i===0) octx.moveTo(p[0],p[1]); else octx.lineTo(p[0],p[1]);
      }
      octx.closePath();
    }
    octx.fillStyle = 'rgba(215,180,106,0.24)';
    octx.fill('evenodd');
    octx.lineWidth = Math.max(0.6, dpr*0.5);
    octx.strokeStyle = 'rgba(231,200,140,0.45)';
    octx.stroke();
  }

  function resize(){
    dpr = Math.min(window.devicePixelRatio||1, 2);
    W = canvas.clientWidth*dpr; H = canvas.clientHeight*dpr;
    canvas.width = W; canvas.height = H;
    // cover fit (map natural ratio 2:1)
    mapH = Math.max(H, W/2); mapW = mapH*2;
    ox = (W-mapW)/2; oy = (H-mapH)/2;
    buildMap();
  }

  function arcPath(a, b, lift){
    var pa = project(a[0],a[1]), pb = project(b[0],b[1]);
    var mx = (pa[0]+pb[0])/2, my = (pa[1]+pb[1])/2;
    var dx = pb[0]-pa[0], dy = pb[1]-pa[1];
    var dist = Math.sqrt(dx*dx+dy*dy);
    // perpendicular lift (upward bias) for a flight-path curve
    var nx = -dy/dist, ny = dx/dist;
    if(ny > 0){ nx=-nx; ny=-ny; }            // bias curve upward
    var cx = mx + nx*dist*lift, cy = my + ny*dist*lift;
    return { pa:pa, pb:pb, cx:cx, cy:cy };
  }

  var ARCS = ORIGINS.map(function(o,i){ return { o:o, lift:0.18+ (i%3)*0.07, phase:(i*7)%40 }; });
  var t = 0;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function frame(){
    ctx.clearRect(0,0,W,H);
    ctx.drawImage(off,0,0);

    var hub = project(TOKYO[0],TOKYO[1]);

    // routes
    for(var i=0;i<ARCS.length;i++){
      var A = ARCS[i], path = arcPath(A.o, TOKYO, A.lift);
      // base faint line
      ctx.beginPath();
      ctx.moveTo(path.pa[0],path.pa[1]);
      ctx.quadraticCurveTo(path.cx,path.cy,path.pb[0],path.pb[1]);
      ctx.lineWidth = Math.max(1, dpr*0.7);
      ctx.strokeStyle = 'rgba(215,180,106,0.18)';
      ctx.setLineDash([]); ctx.stroke();
      // flowing dashes toward Japan
      ctx.beginPath();
      ctx.moveTo(path.pa[0],path.pa[1]);
      ctx.quadraticCurveTo(path.cx,path.cy,path.pb[0],path.pb[1]);
      ctx.lineWidth = Math.max(1.2, dpr*1.1);
      ctx.strokeStyle = 'rgba(241,220,168,0.85)';
      ctx.setLineDash([2*dpr, 12*dpr]);
      ctx.lineDashOffset = reduce ? 0 : -(t*2 + A.phase)*dpr;
      ctx.stroke();
      // origin node
      ctx.setLineDash([]);
      var pulse = reduce ? 1 : (0.6+0.4*Math.sin((t*0.06)+i));
      ctx.beginPath();
      ctx.arc(path.pa[0],path.pa[1], dpr*2.4, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(215,180,106,'+(0.5*pulse+0.3)+')';
      ctx.fill();
    }

    // Japan hub glow
    var hp = reduce ? 1 : (0.7+0.3*Math.sin(t*0.08));
    ctx.beginPath(); ctx.arc(hub[0],hub[1], dpr*9*hp, 0, Math.PI*2);
    ctx.strokeStyle = 'rgba(241,220,168,'+(0.4*hp)+')'; ctx.lineWidth = dpr; ctx.stroke();
    ctx.beginPath(); ctx.arc(hub[0],hub[1], dpr*4.5, 0, Math.PI*2);
    ctx.fillStyle = '#f1dca8';
    ctx.shadowColor = 'rgba(241,220,168,0.9)'; ctx.shadowBlur = dpr*16;
    ctx.fill(); ctx.shadowBlur = 0;

    t += 1;
    if(!reduce) requestAnimationFrame(frame);
  }

  resize();
  window.addEventListener('resize', resize);
  requestAnimationFrame(frame);
})();
