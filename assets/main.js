const root=document.documentElement,side=document.querySelector('nav.side');
const saved=localStorage.getItem('fs-theme');if(saved)root.dataset.theme=saved;
document.getElementById('theme').onclick=()=>{
  const dark=getComputedStyle(root).getPropertyValue('--bg').trim()==='#0b1720';
  root.dataset.theme=dark?'light':'dark';localStorage.setItem('fs-theme',root.dataset.theme)};
document.getElementById('menu').onclick=e=>{const o=side.classList.toggle('open');e.target.setAttribute('aria-expanded',o)};
side.addEventListener('click',e=>{if(e.target.tagName==='A')side.classList.remove('open')});
document.querySelectorAll('.code').forEach(b=>{
  const btn=document.createElement('button');btn.className='btn copy';btn.textContent='Copy';
  btn.onclick=async()=>{try{await navigator.clipboard.writeText(b.querySelector('pre').innerText);btn.textContent='Copied'}catch{btn.textContent='Press Ctrl+C'}setTimeout(()=>btn.textContent='Copy',1500)};
  b.appendChild(btn)});
const links=[...side.querySelectorAll('a')];
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){links.forEach(a=>a.classList.toggle('on',a.hash==='#'+e.target.id))}}),{rootMargin:'-20% 0px -70% 0px'});
document.querySelectorAll('main section').forEach(s=>io.observe(s));
