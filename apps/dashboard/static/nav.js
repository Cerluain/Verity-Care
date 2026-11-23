// Floating view switcher (bottom-left) shared by every page.
// Include with: <script src="/static/nav.js" defer></script>
(function () {
  const views = [
    { href: '/',         icon: '🕵️', label: 'Investigator', match: p => p === '/' },
    { href: '/guardian', icon: '👪', label: 'Guardian',     match: p => p.startsWith('/guardian') },
    { href: '/staff',    icon: '🩺', label: 'Staff',        match: p => p.startsWith('/staff') },
    { href: '/facility', icon: '🏥', label: 'Facility',     match: p => p.startsWith('/facility') },
    { href: '/pitch',    icon: '▶',  label: 'Pitch',        match: p => p.startsWith('/pitch') },
  ];
  const path = location.pathname;
  const css = `
    #vc-nav{position:fixed;left:16px;bottom:16px;z-index:60;display:flex;flex-direction:column;gap:6px;
      background:rgba(15,23,42,.92);backdrop-filter:blur(8px);padding:8px;border-radius:16px;
      box-shadow:0 10px 30px rgba(15,23,42,.35);font:500 12px -apple-system,system-ui,sans-serif}
    #vc-nav a{display:flex;align-items:center;justify-content:center;width:44px;height:44px;border-radius:12px;
      color:#e2e8f0;text-decoration:none;font-size:20px;position:relative;transition:background .15s}
    #vc-nav a:hover{background:rgba(255,255,255,.12)}
    #vc-nav a.on{background:#fff;color:#0f172a}
    #vc-nav a span{position:absolute;left:54px;white-space:nowrap;background:#0f172a;color:#fff;font-size:12px;
      padding:4px 8px;border-radius:6px;opacity:0;pointer-events:none;transition:opacity .15s}
    #vc-nav a:hover span{opacity:1}
    @media (max-width:640px){#vc-nav{flex-direction:row;left:50%;transform:translateX(-50%);bottom:10px;padding:5px;gap:4px;border-radius:14px}
      #vc-nav a{width:38px;height:38px;font-size:17px}#vc-nav a span{display:none}}`;
  const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);
  const nav = document.createElement('nav'); nav.id = 'vc-nav'; nav.setAttribute('aria-label', 'Switch view');
  nav.innerHTML = views.map(v =>
    `<a href="${v.href}" class="${v.match(path) ? 'on' : ''}" aria-label="${v.label}">${v.icon}<span>${v.label}</span></a>`).join('');
  document.body.appendChild(nav);
})();
