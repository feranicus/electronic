# -*- coding: utf-8 -*-
"""The page template for build_attack_globe.py. Kept separate so the DATA and the PRESENTATION
have one home each - the same reason the GEOPOL builder keeps skeleton.html apart from content."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>The Footprint - what actually hits cybergod.ai</title>
<meta name="description" content="A measured record of 156,511 requests, 2,253 sources and 604 scanner-like origins against one small server. Detected, counted, and read.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Unbounded:wght@600;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#05080e; --bg2:#0a111d; --ink:#E9F1FA; --mut:#8A9BB4;
  --hl:#00D7BD; --vio:#9E86FF; --red:#FF3B57; --amb:#FFC33C; --org:#FF7A33;
  --blu:#37C8FF; --grn:#26D98A; --line:rgba(140,170,210,.16);
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
  font-family:"Inter",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
body{overflow-x:hidden}
#gl,#fb{position:fixed;inset:0;width:100vw;height:100vh;display:block;z-index:0}
#fb{display:none}
.vig{position:fixed;inset:0;z-index:1;pointer-events:none;
  background:radial-gradient(ellipse at 50% 45%,transparent 30%,rgba(5,8,14,.55) 78%,rgba(5,8,14,.92) 100%)}
main{position:relative;z-index:2}
.scene{min-height:100vh;display:flex;align-items:center;padding:9vh 6vw;
  opacity:0;transform:translateY(26px);transition:opacity .9s ease,transform .9s ease}
.scene.on{opacity:1;transform:none}
.card{max-width:660px;background:linear-gradient(180deg,rgba(10,17,29,.86),rgba(5,8,14,.72));
  border:1px solid var(--line);border-radius:18px;padding:30px 32px;
  backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  box-shadow:0 30px 90px rgba(0,0,0,.55)}
.right{margin-left:auto}
.eyebrow{font-family:"JetBrains Mono",monospace;font-size:11.5px;letter-spacing:.18em;
  text-transform:uppercase;color:var(--hl);margin-bottom:14px}
h1{font-family:"Unbounded",sans-serif;font-weight:800;font-size:clamp(30px,4.6vw,54px);
  line-height:1.05;margin:0 0 16px;letter-spacing:-.02em}
h1 .g{background:linear-gradient(92deg,var(--hl),var(--blu) 45%,var(--vio));
  -webkit-background-clip:text;background-clip:text;color:transparent}
h2{font-family:"Unbounded",sans-serif;font-weight:600;font-size:clamp(22px,2.9vw,34px);
  line-height:1.12;margin:0 0 14px}
p{font-size:16.5px;line-height:1.62;color:#C7D5E6;margin:0 0 14px}
p.lede{font-size:18.5px;color:var(--ink)}
.mut{color:var(--mut);font-size:14px;line-height:1.6}
b{color:var(--ink);font-weight:600}
.hl{color:var(--hl)} .red{color:var(--red)} .amb{color:var(--amb)} .grn{color:var(--grn)}
.vio{color:var(--vio)}
.statbar{display:flex;flex-wrap:wrap;gap:26px;margin:22px 0 6px;padding-top:20px;
  border-top:1px solid var(--line)}
.stat .n{font-family:"Unbounded",sans-serif;font-weight:800;font-size:clamp(26px,3.4vw,40px);
  line-height:1;letter-spacing:-.02em}
.stat .l{font-family:"JetBrains Mono",monospace;font-size:10.5px;letter-spacing:.13em;
  text-transform:uppercase;color:var(--mut);margin-top:7px}
.bars{margin:20px 0 4px}
.bar{display:grid;grid-template-columns:118px 1fr 44px;align-items:center;gap:12px;margin:7px 0}
.bar .k{font-family:"JetBrains Mono",monospace;font-size:11.5px;color:#B9C8DC}
.bar .t{height:9px;border-radius:6px;background:rgba(255,255,255,.06);overflow:hidden}
.bar .f{height:100%;width:0;border-radius:6px;transition:width 1.3s cubic-bezier(.2,.8,.2,1)}
.bar .v{font-family:"JetBrains Mono",monospace;font-size:12px;text-align:right;color:#B9C8DC}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 4px}
.chip{font-family:"JetBrains Mono",monospace;font-size:11.5px;padding:6px 11px;border-radius:999px;
  border:1px solid var(--line);color:#C7D5E6;background:rgba(255,255,255,.03)}
.chip.r{border-color:rgba(255,59,87,.45);color:#FFB0BB;background:rgba(255,59,87,.09)}
.chip.g{border-color:rgba(38,217,138,.42);color:#9affc9;background:rgba(38,217,138,.08)}
.tape{font-family:"JetBrains Mono",monospace;font-size:12px;color:var(--mut);
  border-left:2px solid var(--line);padding-left:14px;margin:16px 0;min-height:96px}
.tape div{opacity:0;animation:tin .5s forwards}
@keyframes tin{to{opacity:1}}
.note{margin-top:18px;padding:13px 15px;border-radius:12px;font-size:13.5px;line-height:1.55;
  border:1px solid rgba(255,195,60,.3);background:rgba(255,195,60,.07);color:#FFE3A8}
.note.t{border-color:rgba(0,215,189,.28);background:rgba(0,215,189,.07);color:#A8F5EA}
.panel{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:18px 0 4px}
.mod{border:1px solid var(--line);border-radius:12px;padding:12px 13px;background:rgba(255,255,255,.03)}
.mod .m{font-family:"JetBrains Mono",monospace;font-size:12.5px;color:var(--ink)}
.mod .r{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--mut);margin-top:5px}
.legend{position:fixed;left:22px;bottom:22px;z-index:3;display:flex;flex-direction:column;gap:6px;
  opacity:0;transition:opacity .6s}
.legend.on{opacity:1}
.legend i{display:flex;align-items:center;gap:8px;font-family:"JetBrains Mono",monospace;
  font-size:10.5px;color:var(--mut);font-style:normal}
.legend i s{width:16px;height:2px;border-radius:2px;text-decoration:none}
.hud{position:fixed;right:22px;top:22px;z-index:3;text-align:right;
  font-family:"JetBrains Mono",monospace;font-size:10.5px;letter-spacing:.12em;color:var(--mut)}
.hud b{display:block;font-size:13px;color:var(--hl);letter-spacing:.16em}
.scroll{position:fixed;left:50%;bottom:20px;transform:translateX(-50%);z-index:3;
  font-family:"JetBrains Mono",monospace;font-size:10.5px;letter-spacing:.2em;color:var(--mut);
  animation:bob 2.4s ease-in-out infinite;transition:opacity .5s}
@keyframes bob{0%,100%{transform:translateX(-50%) translateY(0)}50%{transform:translateX(-50%) translateY(7px)}}
footer{position:relative;z-index:2;padding:60px 6vw 80px;border-top:1px solid var(--line);
  background:linear-gradient(180deg,rgba(5,8,14,.5),rgba(5,8,14,.95))}
footer .w{max-width:900px}
footer h3{font-family:"Unbounded",sans-serif;font-weight:600;font-size:17px;margin:0 0 12px}
footer p{font-size:13.5px;color:var(--mut)}
.src{font-family:"JetBrains Mono",monospace;font-size:11.5px;color:var(--mut);line-height:1.85}
.brand{font-family:"Unbounded",sans-serif;font-weight:800;font-size:15px;letter-spacing:-.01em}
@media(max-width:720px){
  .scene{padding:8vh 5vw;min-height:auto;padding-top:12vh;padding-bottom:12vh}
  .card{padding:22px 20px;max-width:none}
  .right{margin-left:0}
  .legend{left:14px;bottom:14px}
  .hud{right:14px;top:14px}
  .panel{grid-template-columns:1fr}
  .bar{grid-template-columns:96px 1fr 38px}
}
@media(prefers-reduced-motion:reduce){
  .scene{opacity:1;transform:none;transition:none}
  .scroll{animation:none}
}
</style>
</head>
<body>
<canvas id="gl"></canvas>
<canvas id="fb"></canvas>
<div class="vig"></div>

<div class="hud"><b>THE FOOTPRINT</b>cybergod.ai &middot; 10-11 AUG 2026</div>
<div class="legend" id="lg">
  <i><s style="background:#FF3B57"></s>scanner / probe</i>
  <i><s style="background:#FFC33C"></s>alerted, then blocked</i>
  <i><s style="background:#26D98A"></s>a real visitor</i>
  <i><s style="background:#00D7BD"></s>our server, FRA1</i>
  <i style="margin-top:6px;max-width:250px;line-height:1.5;opacity:.8">5 origins are geolocated in
    our data and labelled. The rest is drawn as unattributed traffic - we do not publish a country
    map we cannot evidence.</i>
  <i style="opacity:.8">604 sources were DETECTED, not stopped: the shield shipped after this
    measurement window.</i>
</div>
<div class="scroll" id="sc">SCROLL</div>

<main>

<section class="scene" data-s="0">
  <div class="card">
    <div class="eyebrow">Scene 01 &middot; the survey nobody watches</div>
    <h1>We pointed our own product<br>at <span class="g">our own server</span></h1>
    <p class="lede">Then we read all 156,511 lines of the log, which we had never actually done.
      604 strangers were already having a look around.</p>
    <p>None of it was a breach. It is what the public internet does to anything with a DNS record.
      What bothered us was the assuming.</p>
    <div class="statbar">
      <div class="stat"><div class="n hl" data-c="156511">0</div><div class="l">http events</div></div>
      <div class="stat"><div class="n" data-c="2253">0</div><div class="l">distinct sources</div></div>
      <div class="stat"><div class="n red" data-c="604">0</div><div class="l">scanner-like</div></div>
    </div>
    <div class="note t"><b>Read this precisely.</b> 604 were <b>detected</b> over the period the
      log covers. Not stopped. The shield shipped afterwards, and on a security page a number you
      cannot support is worse than no number.</div>
  </div>
</section>

<section class="scene" data-s="1">
  <div class="card right">
    <div class="eyebrow">Scene 02 &middot; what was knocking</div>
    <h2>483 sources hunting WordPress.<br>We do not run WordPress.</h2>
    <p>Every bar is a count of <b>distinct sources</b>, not requests. The long tail is the
      interesting part: three separate origins asked for <span class="vio">/DOCS.md</span> and
      <span class="vio">/IAM.md</span>, which are files that live in repositories, not on websites.</p>
    <div class="bars" id="bars"></div>
    <p class="mut">Favourite of the set: a webshell campaign spread across four cloud providers,
      uploading <b>alfa.php</b>, <b>lock360.php</b> and, we promise this is real,
      <b>this_is_a_new_hello_world.php</b>.</p>
  </div>
</section>

<section class="scene" data-s="2">
  <div class="card">
    <div class="eyebrow">Scene 03 &middot; the tape</div>
    <h2>This is a normal Tuesday</h2>
    <p>Real paths, taken from the log. Nothing here is unusual, and that is the whole point:
      this arrives at every server with a name, continuously, for free.</p>
    <div class="tape" id="tape"></div>
    <div class="chips">
      <span class="chip r">path_probe &times;212</span>
      <span class="chip r">dir_bruteforce &times;208</span>
      <span class="chip r">authz_probe &times;85</span>
      <span class="chip r">ip_burst &times;71</span>
    </div>
  </div>
</section>

<section class="scene" data-s="3">
  <div class="card right">
    <div class="eyebrow">Scene 04 &middot; 10 Aug, 19:05:55 UTC</div>
    <h2>One address. Two seconds.<br><span class="g">Six different browsers.</span></h2>
    <p>195.178.110.199, geolocated to Andorra, asked for <b>/</b>, then <b>//slug</b>,
      <b>/DOCS.md</b>, <b>/IAM.md</b> and <b>/[workspace]/</b> - each request announcing a
      different client.</p>
    <div class="chips" id="uas"></div>
    <p>Those are template placeholders and repository files. It was not someone trying to break in.
      It was someone checking whether we had published our own internal documentation and
      identity model by accident.</p>
    <div class="note"><b>The evasion became the evidence.</b> We had been identifying visitors
      partly by their browser, so one scanner rotating user agents read as six separate people
      arriving. Now, several fingerprints from one address inside seconds is treated as a scanner,
      because no real visitor ever does that.</div>
  </div>
</section>

<section class="scene" data-s="4">
  <div class="card">
    <div class="eyebrow">Scene 05 &middot; the shield</div>
    <h2>Detection is arithmetic,<br>and it sits inline</h2>
    <p>Microseconds, deterministic, in the request path. On 11 August it saw 136.67.108.237 ask
      for <span class="vio">/.vite/manifest.json</span> and <span class="vio">/api/graphql</span>,
      tarpitted it, then blocked it for fifteen minutes, and put six options on a phone.</p>
    <div class="chips">
      <span class="chip">tarpit</span><span class="chip">block 15 min</span>
      <span class="chip">hold 24h</span><span class="chip">block /24</span>
      <span class="chip">report abuse</span><span class="chip g">false alarm - release</span>
    </div>
    <p class="mut">Five safety rails, each proven by breaking it on purpose and watching the build
      fail: never blocks <b>/.well-known/</b> (that turns a scanner into a certificate outage),
      never blocks our own routes, fails open on any internal error, every block expires, and a
      blast cap refuses a mass block. The firewall is never touched - a VPN shares this host.</p>
  </div>
</section>

<section class="scene" data-s="5">
  <div class="card right">
    <div class="eyebrow">Scene 06 &middot; four vendors, out of band</div>
    <h2>The models review. The code decides.</h2>
    <div class="panel" id="panel"></div>
    <p>They read every block after the fact, write the incident report, and may adjust six
      thresholds inside limits that live in committed code. They cannot block an address, change
      the limits, or empty the allow-list.</p>
    <div class="note"><b>They are not in the request path, deliberately.</b> A model call takes
      300ms to a minute. Put one in front of an incoming request and you have not built a defence,
      you have built an expensive way to take your own site down.</div>
  </div>
</section>

<section class="scene" data-s="6">
  <div class="card">
    <div class="eyebrow">Scene 07 &middot; what we nearly got wrong</div>
    <h2>The two loudest addresses<br>were <span class="grn">real people</span></h2>
    <p>A visitor in Germany and one in Israel, <b>439</b> and <b>362</b> not-found responses
      between them. On a naive 404 threshold we would have locked both out of our own product
      while feeling rather pleased about the security.</p>
    <p>What separates them from a scanner is not volume. It is <b>variety</b>. A person misses
      the same three stale links repeatedly. A scanner misses hundreds of different ones.</p>
    <div class="statbar">
      <div class="stat"><div class="n grn" data-c="0">0</div><div class="l">real visitors blocked</div></div>
      <div class="stat"><div class="n amb" data-c="29">0</div><div class="l">classes known before</div></div>
      <div class="stat"><div class="n hl" data-c="48">0</div><div class="l">classes known after</div></div>
    </div>
    <p class="mut" style="margin-top:16px">We had built the rules from a single incident and
      assumed the job was done. Reading the log properly found 19 gaps in an afternoon. Attacker
      tooling updates weekly and your product grows new routes every sprint, so rules that were
      right in July go quietly wrong in August and nothing tells you.</p>
  </div>
</section>

</main>

<footer><div class="w">
  <h3>Where these numbers come from</h3>
  <p>Every figure on this page was produced by <b>analyse_attacks.py</b> reading colt-web's own
  event log, or taken from the operator's Telegram alerts, 10-11 August 2026. Nothing is modelled
  and nothing is projected.</p>
  <div class="src">
    156,511 http events &middot; 2,253 distinct sources &middot; 604 scanner-like<br>
    class counts are DISTINCT SOURCES per class, not request volume<br>
    48/48 known attack-path classes recognised after the fix, 29/48 before<br>
    <span class="amb">Geography: only five sources in this data are geolocated, and they are the
    five labelled on the globe. The remaining traffic is drawn as unattributed arcs. We do not
    publish a country heat map we cannot evidence.</span><br>
    <span class="grn">The 604 were DETECTED. They were not stopped: the shield shipped after the
    measurement window.</span>
  </div>
  <p style="margin-top:26px"><span class="brand">cybergod.ai</span>
    <span class="mut"> &middot; Cybergod LLC / S4biz Group &middot; read your own logs</span></p>
</div></footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
(function(){
"use strict";
var D={totals:__TOTALS__,classes:__CLASSES__,known:__KNOWN__,target:__TARGET__,
       models:__MODELS__,alerts:__ALERTS__,uas:__UAS__,apaths:__APATHS__,tape:__TAPE__};
var RM=window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- DOM content that is data, not markup ---------------------------------------- */
var bars=document.getElementById("bars");
D.classes.forEach(function(c){
  var r=document.createElement("div"); r.className="bar";
  r.innerHTML='<div class="k">'+c[0]+'</div><div class="t"><div class="f" style="background:'+
    c[2]+'"></div></div><div class="v">'+c[1]+'</div>';
  r.setAttribute("data-w",Math.max(3,c[1]/483*100)); bars.appendChild(r);
});
var uas=document.getElementById("uas");
D.uas.forEach(function(u){var s=document.createElement("span");s.className="chip r";s.textContent=u;uas.appendChild(s);});
var panel=document.getElementById("panel");
D.models.forEach(function(m){
  var d=document.createElement("div"); d.className="mod";
  d.innerHTML='<div class="m">'+m[0]+'</div><div class="r">'+m[1]+'</div>'; panel.appendChild(d);
});

/* ---------- count-ups + scene reveal ----------------------------------------------------- */
function countUp(el){
  var t=+el.getAttribute("data-c"), d=1200, s=performance.now();
  if(t===0){el.textContent="0";return;}
  function f(n){var p=Math.min(1,(n-s)/d), e=1-Math.pow(1-p,3);
    el.textContent=Math.round(t*e).toLocaleString("en-US");
    if(p<1)requestAnimationFrame(f);} requestAnimationFrame(f);
}
var scenes=[].slice.call(document.querySelectorAll(".scene")), cur=0;
var io=new IntersectionObserver(function(es){
  es.forEach(function(e){
    if(!e.isIntersecting)return;
    e.target.classList.add("on");
    cur=+e.target.getAttribute("data-s");
    setScene(cur);
    [].slice.call(e.target.querySelectorAll("[data-c]")).forEach(function(n){
      if(!n.dataset.done){n.dataset.done=1;countUp(n);}});
    [].slice.call(e.target.querySelectorAll(".bar")).forEach(function(b,i){
      var f=b.querySelector(".f");
      setTimeout(function(){f.style.width=b.getAttribute("data-w")+"%";},60*i);
    });
    if(cur===2)startTape();
  });
},{threshold:.35});
scenes.forEach(function(s){io.observe(s);});
document.addEventListener("scroll",function(){
  var sc=document.getElementById("sc"); sc.style.opacity=window.scrollY>200?0:1;
},{passive:true});

var tapeStarted=false;
function startTape(){
  if(tapeStarted)return; tapeStarted=true;
  var el=document.getElementById("tape"), i=0;
  setInterval(function(){
    var p=D.tape[i%D.tape.length], t=new Date(Date.now()-((D.tape.length-i)*1373)%86400000);
    var d=document.createElement("div");
    d.textContent=t.toISOString().substr(11,8)+"  GET "+p+"  -> 404";
    el.appendChild(d); if(el.children.length>5)el.removeChild(el.firstChild); i++;
  },900);
}

/* ---------- 3D ---------------------------------------------------------------------------- */
var cv=document.getElementById("gl"), lg=document.getElementById("lg");
var W=innerWidth,H=innerHeight, ok=(typeof THREE!=="undefined");
if(ok){ try{ init(); }catch(e){ ok=false; console.warn("webgl init failed",e);} }
if(!ok) fallback2d();

function ll(lat,lon,r){                       /* lat/lon -> xyz on a sphere of radius r */
  var p=(90-lat)*Math.PI/180, t=(lon+180)*Math.PI/180;
  return new THREE.Vector3(-r*Math.sin(p)*Math.cos(t), r*Math.cos(p), r*Math.sin(p)*Math.sin(t));
}
function glowTex(){                            /* soft round sprite - the whole look depends on it */
  var c=document.createElement("canvas"); c.width=c.height=64;
  var g=c.getContext("2d").createRadialGradient(32,32,0,32,32,32);
  g.addColorStop(0,"rgba(255,255,255,1)"); g.addColorStop(.25,"rgba(255,255,255,.65)");
  g.addColorStop(1,"rgba(255,255,255,0)");
  var x=c.getContext("2d"); x.fillStyle=g; x.fillRect(0,0,64,64);
  return new THREE.CanvasTexture(c);
}

var scene,cam,rnd,globe,arcs=[],heads,shield,target,rot={x:0.18,y:-1.7223},drag=null,vel=0.00075;
var R=100, camTarget={z:385,y:46}, sceneN=0;

function init(){
  rnd=new THREE.WebGLRenderer({canvas:cv,antialias:true,alpha:false});
  rnd.setPixelRatio(Math.min(devicePixelRatio,2)); rnd.setSize(W,H);
  rnd.setClearColor(0x05080e,1);
  scene=new THREE.Scene(); scene.fog=new THREE.FogExp2(0x05080e,0.0016);
  cam=new THREE.PerspectiveCamera(42,W/H,1,3000); cam.position.set(0,46,385);

  var tex=glowTex();

  /* stars */
  var sg=new THREE.BufferGeometry(), sp=[];
  for(var i=0;i<1400;i++){
    var v=new THREE.Vector3((Math.random()-.5),(Math.random()-.5),(Math.random()-.5)).normalize()
      .multiplyScalar(700+Math.random()*900);
    sp.push(v.x,v.y,v.z);
  }
  sg.setAttribute("position",new THREE.Float32BufferAttribute(sp,3));
  scene.add(new THREE.Points(sg,new THREE.PointsMaterial({color:0x9fb4cc,size:2.2,map:tex,
    transparent:true,opacity:.5,blending:THREE.AdditiveBlending,depthWrite:false})));

  globe=new THREE.Group(); scene.add(globe);

  /* the ocean sphere - slightly smaller so land dots sit proud of it */
  globe.add(new THREE.Mesh(new THREE.SphereGeometry(R*0.985,64,48),
    new THREE.MeshBasicMaterial({color:0x071624})));

  /* atmosphere: fresnel rim, BackSide. This is what makes it look expensive. */
  globe.add(new THREE.Mesh(new THREE.SphereGeometry(R*1.16,64,48),
    new THREE.ShaderMaterial({
      uniforms:{c:{value:new THREE.Color(0x00d7bd)}},
      vertexShader:"varying vec3 vN;void main(){vN=normalize(normalMatrix*normal);"+
        "gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}",
      fragmentShader:"uniform vec3 c;varying vec3 vN;void main(){"+
        "float i=pow(.72-dot(vN,vec3(0,0,1.)),3.2);gl_FragColor=vec4(c,1.)*i*1.15;}",
      side:THREE.BackSide,blending:THREE.AdditiveBlending,transparent:true,depthWrite:false})));

  /* graticule */
  for(var la=-60;la<=60;la+=30) ring(la,true);
  for(var lo=-150;lo<=180;lo+=30) ring(lo,false);
  function ring(v,isLat){
    var pts=[],i;
    for(i=0;i<=96;i++){
      pts.push(isLat ? ll(v, i/96*360-180, R*1.002)
                     : ll(-90+i/96*180, v, R*1.002));
    }
    globe.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({color:0x1d4a5c,transparent:true,opacity:.30})));
  }

  /* land dots, sampled from the embedded mask */
  var img=new Image();
  img.onload=function(){
    var c=document.createElement("canvas"); c.width=img.width; c.height=img.height;
    var x=c.getContext("2d"); x.drawImage(img,0,0);
    var px=x.getImageData(0,0,c.width,c.height).data, pos=[], col=[], base=new THREE.Color(0x00d7bd);
    var STEP=3;
    for(var yy=0;yy<c.height;yy+=STEP){
      for(var xx=0;xx<c.width;xx+=STEP){
        if(px[(yy*c.width+xx)*4]<128) continue;
        var lat=90-(yy/c.height)*180, lon=(xx/c.width)*360-180;
        var v=ll(lat,lon,R*1.004); pos.push(v.x,v.y,v.z);
        var t=0.55+0.45*Math.random();
        col.push(base.r*t,base.g*t,base.b*t);
      }
    }
    var g=new THREE.BufferGeometry();
    g.setAttribute("position",new THREE.Float32BufferAttribute(pos,3));
    g.setAttribute("color",new THREE.Float32BufferAttribute(col,3));
    globe.add(new THREE.Points(g,new THREE.PointsMaterial({size:2.05,map:tex,vertexColors:true,
      transparent:true,opacity:.95,blending:THREE.AdditiveBlending,depthWrite:false,
      sizeAttenuation:true})));
  };
  img.src="data:image/png;base64,__MASK__";

  /* the target: our droplet */
  var tv=ll(D.target[0],D.target[1],R*1.01);
  target=new THREE.Group(); target.position.copy(tv); globe.add(target);
  target.add(new THREE.Mesh(new THREE.SphereGeometry(2.9,20,20),
    new THREE.MeshBasicMaterial({color:0x00ffe4})));
  var rings=[];
  for(var k=0;k<3;k++){
    var rg=new THREE.Mesh(new THREE.RingGeometry(4.2,4.9,48),
      new THREE.MeshBasicMaterial({color:0x00d7bd,transparent:true,opacity:.7,
        side:THREE.DoubleSide,blending:THREE.AdditiveBlending,depthWrite:false}));
    rg.lookAt(tv.clone().multiplyScalar(2)); rg.userData.p=k/3; target.add(rg); rings.push(rg);
  }
  target.userData.rings=rings;

  /* shield shell - revealed in scene 05 */
  shield=new THREE.Mesh(new THREE.IcosahedronGeometry(R*1.09,2),
    new THREE.MeshBasicMaterial({color:0x00d7bd,wireframe:true,transparent:true,opacity:0,
      blending:THREE.AdditiveBlending,depthWrite:false}));
  globe.add(shield);

  /* arcs */
  var headPos=[],headCol=[];
  function slerpArc(a,b,seg){
    /* Great circle + sine altitude. Radius is R*(1+alt*sin(pi t)) so the curve can never enter
       the sphere - measured worst case 1.000 of R against the quadratic form's 0.859. */
    var A=a.clone().normalize(), B=b.clone().normalize();
    var om=Math.acos(Math.max(-1,Math.min(1,A.dot(B))));
    var alt=0.16+0.38*(om/Math.PI), so=Math.sin(om), out=[];
    for(var i=0;i<=seg;i++){
      var t=i/seg, v;
      if(so<1e-6){ v=A.clone(); }
      else{ v=A.clone().multiplyScalar(Math.sin((1-t)*om)/so)
                .add(B.clone().multiplyScalar(Math.sin(t*om)/so)); }
      out.push(v.normalize().multiplyScalar(R*(1.006+alt*Math.sin(Math.PI*t))));
    }
    return out;
  }
  function addArc(lat,lon,colour,kind,labelled){
    var a=ll(lat,lon,R*1.01), b=tv.clone();
    var pts=slerpArc(a,b,64);
    var g=new THREE.BufferGeometry().setFromPoints(pts);
    var m=new THREE.LineBasicMaterial({color:new THREE.Color(colour),transparent:true,
      opacity:labelled?.34:.13,blending:THREE.AdditiveBlending,depthWrite:false});
    var line=new THREE.Line(g,m); globe.add(line);
    var c=new THREE.Color(colour); headPos.push(0,0,0); headCol.push(c.r,c.g,c.b);
    arcs.push({pts:pts,line:line,mat:m,t:Math.random(),
      sp:(kind==="human"?0.0032:0.0052)+Math.random()*0.0035,
      kind:kind,labelled:labelled,colour:c,blocked:false});
    return arcs.length-1;
  }
  /* the five we can actually attribute */
  D.known.forEach(function(k){ addArc(k[0],k[1],k[5],k[6],true); });
  /* the bulk: unattributed, and the page says so */
  var bulkCols=["#FF3B57","#FF7A33","#FFC33C","#9E86FF","#37C8FF"];
  for(var n=0;n<150;n++){
    var la=(Math.random()*2-1); la=Math.asin(la)*180/Math.PI*1.05;
    var lo=Math.random()*360-180;
    addArc(la,lo,bulkCols[n%bulkCols.length],"scanner",false);
  }
  var hg=new THREE.BufferGeometry();
  hg.setAttribute("position",new THREE.Float32BufferAttribute(headPos,3));
  hg.setAttribute("color",new THREE.Float32BufferAttribute(headCol,3));
  heads=new THREE.Points(hg,new THREE.PointsMaterial({size:5.2,map:tex,vertexColors:true,
    transparent:true,opacity:.95,blending:THREE.AdditiveBlending,depthWrite:false}));
  globe.add(heads);

  addEventListener("resize",onResize);
  cv.addEventListener("pointerdown",function(e){drag={x:e.clientX,y:e.clientY};});
  addEventListener("pointerup",function(){drag=null;});
  addEventListener("pointermove",function(e){
    if(!drag)return;
    rot.y+=(e.clientX-drag.x)*0.005; rot.x+=(e.clientY-drag.y)*0.003;
    rot.x=Math.max(-1.0,Math.min(1.0,rot.x)); drag={x:e.clientX,y:e.clientY}; vel=0.0004;
  });
  setTimeout(function(){lg.classList.add("on");},900);
  tick();
}

function onResize(){ W=innerWidth;H=innerHeight; if(!cam)return;
  cam.aspect=W/H; cam.updateProjectionMatrix(); rnd.setSize(W,H); }

function setScene(n){
  sceneN=n;
  camTarget.z = [385,440,455,410,425,450,440][n] || 440;
  camTarget.y = [46,30,14,-4,22,44,34][n] || 34;
}

var clock=0;
function tick(){
  requestAnimationFrame(tick);
  clock+=1;
  if(!drag) rot.y+=vel, vel=Math.min(0.00075,vel*1.01+0.0000025);
  globe.rotation.y=rot.y; globe.rotation.x=rot.x;

  cam.position.z+=(camTarget.z-cam.position.z)*0.045;
  cam.position.y+=(camTarget.y-cam.position.y)*0.045;
  cam.lookAt(0,0,0);

  /* target rings pulse */
  if(target){ target.userData.rings.forEach(function(r,i){
    var p=((clock*0.006)+r.userData.p)%1;
    r.scale.setScalar(1+p*3.4); r.material.opacity=(1-p)*0.55;
  });}

  /* shield appears in scene 05 and stops the arcs */
  var want = (sceneN>=4)?0.20:0.0;
  shield.material.opacity += (want-shield.material.opacity)*0.05;

  /* arc heads travel; under the shield they stop short and fade */
  var pos=heads.geometry.attributes.position.array;
  for(var i=0;i<arcs.length;i++){
    var a=arcs[i];
    a.t+=a.sp;
    var stop = (sceneN>=4 && a.kind!=="human") ? 0.72 : 1.0;
    if(a.t>stop){ a.t=0; }
    var f=a.t*(a.pts.length-1), i0=Math.floor(f), fr=f-i0;
    var p0=a.pts[i0], p1=a.pts[Math.min(i0+1,a.pts.length-1)];
    pos[i*3]=p0.x+(p1.x-p0.x)*fr;
    pos[i*3+1]=p0.y+(p1.y-p0.y)*fr;
    pos[i*3+2]=p0.z+(p1.z-p0.z)*fr;
    /* the labelled five brighten as their scene arrives */
    var base=a.labelled?0.34:0.13;
    var boost=(sceneN===3&&a.labelled)?0.55:(sceneN===6&&a.kind==="human"?0.6:base);
    a.mat.opacity += (boost-a.mat.opacity)*0.06;
  }
  heads.geometry.attributes.position.needsUpdate=true;
  rnd.render(scene,cam);
}

/* ---------- 2D fallback: never show a blank rectangle ------------------------------------ */
function fallback2d(){
  var f=document.getElementById("fb"); cv.style.display="none"; f.style.display="block";
  var x=f.getContext("2d"), w,h,pts=[];
  function size(){ w=f.width=innerWidth*devicePixelRatio; h=f.height=innerHeight*devicePixelRatio;
    f.style.width=innerWidth+"px"; f.style.height=innerHeight+"px"; }
  size(); addEventListener("resize",size);
  for(var i=0;i<90;i++) pts.push({a:Math.random()*Math.PI*2,r:Math.random(),t:Math.random(),
    s:0.002+Math.random()*0.004,c:["#FF3B57","#FF7A33","#FFC33C","#9E86FF"][i%4]});
  (function loop(){
    requestAnimationFrame(loop);
    x.fillStyle="rgba(5,8,14,.28)"; x.fillRect(0,0,w,h);
    var cx=w/2, cy=h/2, R=Math.min(w,h)*0.3;
    x.strokeStyle="rgba(0,215,189,.30)"; x.lineWidth=1.5*devicePixelRatio;
    x.beginPath(); x.arc(cx,cy,R,0,Math.PI*2); x.stroke();
    pts.forEach(function(p){
      p.t+=p.s; if(p.t>1)p.t=0;
      var sx=cx+Math.cos(p.a)*R*(1.7-p.t*0.7), sy=cy+Math.sin(p.a)*R*(1.7-p.t*0.7)*0.6;
      var ex=cx, ey=cy;
      var px=sx+(ex-sx)*p.t, py=sy+(ey-sy)*p.t - Math.sin(p.t*Math.PI)*R*0.35;
      x.fillStyle=p.c; x.globalAlpha=0.85*(1-p.t*0.5);
      x.beginPath(); x.arc(px,py,2.6*devicePixelRatio,0,Math.PI*2); x.fill(); x.globalAlpha=1;
    });
    x.fillStyle="#00ffe4"; x.beginPath(); x.arc(cx,cy,4*devicePixelRatio,0,Math.PI*2); x.fill();
  })();
  document.getElementById("lg").classList.add("on");
}
})();
</script>
</body>
</html>
"""
