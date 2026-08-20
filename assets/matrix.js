/* Faint Matrix-style digital rain, drawn behind the page content. */
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) return;

  var canvas = document.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  canvas.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;z-index:-1;pointer-events:none;';
  (document.body || document.documentElement).appendChild(canvas);
  var ctx = canvas.getContext('2d');

  var chars = '0123456789ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆABCDEF<>/{}[]=+*'.split('');
  var fontSize = 15, cols = 0, drops = [];

  function reset() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    cols = Math.floor(canvas.width / fontSize);
    drops = [];
    for (var i = 0; i < cols; i++) drops[i] = Math.floor(Math.random() * -80);
    ctx.fillStyle = '#0b0d11';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  window.addEventListener('resize', reset);
  reset();

  var last = 0;
  function draw(t) {
    requestAnimationFrame(draw);
    if (t - last < 60) return;          // ~16 fps: calm, low CPU
    last = t;

    // fade the previous frame toward the background — leaves a soft trail
    ctx.fillStyle = 'rgba(11,13,17,0.075)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.font = fontSize + 'px "JetBrains Mono", monospace';
    for (var i = 0; i < cols; i++) {
      var ch = chars[(Math.random() * chars.length) | 0];
      var x = i * fontSize;
      var y = drops[i] * fontSize;
      // leading glyph a touch brighter, the rest faint green
      ctx.fillStyle = Math.random() > 0.975 ? 'rgba(140,240,175,0.45)' : 'rgba(80,210,130,0.22)';
      ctx.fillText(ch, x, y);
      if (y > canvas.height && Math.random() > 0.97) drops[i] = 0;
      drops[i]++;
    }
  }
  requestAnimationFrame(draw);
})();
