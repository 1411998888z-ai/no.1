/* Nova Prime — realistic rotating orthographic globe (real Natural Earth coastlines, 110m) */
(function(){
  var canvas = document.getElementById('globe-canvas');
  if(!canvas || typeof LAND === 'undefined') return;
  var ctx = canvas.getContext('2d');
  var DEG = Math.PI/180;
  var centerLat = 20 * DEG;            // view tilt
  var sinP0 = Math.sin(centerLat), cosP0 = Math.cos(centerLat);
  var rot = -100 * DEG;                // current longitude rotation (start over Atlantic/Americas)
  var R, cx, cy, dpr;

  function resize(){
    dpr = Math.min(window.devicePixelRatio||1, 2);
    var size = canvas.clientWidth;
    canvas.width = size*dpr; canvas.height = size*dpr;
    R = size*dpr*0.47; cx = canvas.width/2; cy = canvas.height/2;
  }

  // project lon/lat(deg) -> {x,y,front}; back points clamped to rim
  function project(lon, lat){
    var lam = lon*DEG + rot, phi = lat*DEG;
    var cphi = Math.cos(phi), sphi = Math.sin(phi), clam = Math.cos(lam), slam = Math.sin(lam);
    var cosc = sinP0*sphi + cosP0*cphi*clam;
    var x = cphi*slam;
    var y = cosP0*sphi - sinP0*cphi*clam;
    if(cosc < 0){ var m = Math.sqrt(x*x+y*y)||1; x/=m; y/=m; }
    return { x: cx + R*x, y: cy - R*y, front: cosc >= 0 };
  }

  function drawGraticule(){
    ctx.lineWidth = Math.max(1, dpr*0.6);
    ctx.strokeStyle = 'rgba(215,180,106,0.28)';
    var lat, lon, p, started, i;
    // parallels
    for(lat=-60; lat<=60; lat+=30){
      ctx.beginPath(); started=false;
      for(lon=-180; lon<=180; lon+=4){
        p = project(lon, lat);
        if(!p.front){ started=false; continue; }
        if(!started){ ctx.moveTo(p.x,p.y); started=true; } else ctx.lineTo(p.x,p.y);
      }
      ctx.stroke();
    }
    // meridians
    for(lon=-180; lon<180; lon+=30){
      ctx.beginPath(); started=false;
      for(lat=-90; lat<=90; lat+=4){
        p = project(lon, lat);
        if(!p.front){ started=false; continue; }
        if(!started){ ctx.moveTo(p.x,p.y); started=true; } else ctx.lineTo(p.x,p.y);
      }
      ctx.stroke();
    }
  }

  function frame(){
    ctx.clearRect(0,0,canvas.width,canvas.height);

    // clip to sphere
    ctx.save();
    ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2); ctx.clip();

    // ocean
    var g = ctx.createRadialGradient(cx-R*0.3, cy-R*0.35, R*0.1, cx, cy, R);
    g.addColorStop(0, '#241f33'); g.addColorStop(1, '#0b0b13');
    ctx.fillStyle = g; ctx.fillRect(cx-R,cy-R,R*2,R*2);

    // land
    ctx.beginPath();
    for(var r=0; r<LAND.length; r++){
      var ring = LAND[r], p;
      for(var i=0; i<ring.length; i++){
        p = project(ring[i][0], ring[i][1]);
        if(i===0) ctx.moveTo(p.x,p.y); else ctx.lineTo(p.x,p.y);
      }
      ctx.closePath();
    }
    ctx.fillStyle = 'rgba(217,182,110,0.82)';
    ctx.fill('evenodd');
    ctx.lineWidth = Math.max(0.6, dpr*0.4);
    ctx.strokeStyle = 'rgba(247,225,170,0.55)';
    ctx.stroke();

    drawGraticule();
    ctx.restore();

    // rim + glow
    ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2);
    ctx.lineWidth = Math.max(1, dpr*1.1);
    ctx.strokeStyle = 'rgba(217,182,110,0.9)';
    ctx.shadowColor = 'rgba(217,182,110,0.5)'; ctx.shadowBlur = dpr*14;
    ctx.stroke(); ctx.shadowBlur = 0;

    rot += 0.0016; // spin speed
    requestAnimationFrame(frame);
  }

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  resize();
  window.addEventListener('resize', resize);
  if(reduce){ frame = (function(f){ return function(){ /* draw once */ }; })(); 
    // draw a single static frame
    (function once(){ ctx.clearRect(0,0,canvas.width,canvas.height);
      ctx.save(); ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2); ctx.clip();
      var g=ctx.createRadialGradient(cx-R*0.3,cy-R*0.35,R*0.1,cx,cy,R);
      g.addColorStop(0,'#241f33'); g.addColorStop(1,'#0b0b13'); ctx.fillStyle=g; ctx.fillRect(cx-R,cy-R,R*2,R*2);
      ctx.beginPath(); for(var r=0;r<LAND.length;r++){var ring=LAND[r],p;for(var i=0;i<ring.length;i++){p=project(ring[i][0],ring[i][1]); if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);}ctx.closePath();}
      ctx.fillStyle='rgba(217,182,110,0.82)'; ctx.fill('evenodd');
      ctx.strokeStyle='rgba(247,225,170,0.55)'; ctx.stroke(); drawGraticule(); ctx.restore();
      ctx.beginPath(); ctx.arc(cx,cy,R,0,Math.PI*2); ctx.lineWidth=Math.max(1,dpr*1.1); ctx.strokeStyle='rgba(217,182,110,0.9)'; ctx.stroke();
    })();
  } else {
    requestAnimationFrame(frame);
  }
})();
