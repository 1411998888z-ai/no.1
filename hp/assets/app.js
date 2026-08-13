// モバイルメニュー
var t=document.getElementById('navToggle'),m=document.getElementById('menu');
t&&t.addEventListener('click',function(){m.classList.toggle('open')});
m&&m.querySelectorAll('a').forEach(function(a){a.addEventListener('click',function(){m.classList.remove('open')})});
// スクロール表示
var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}})},{threshold:.12});
document.querySelectorAll('.reveal,.sec-head').forEach(function(el){io.observe(el)});
