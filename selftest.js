// Runs the page's own #selftest in Node, so CI checks the same settle() the game uses
// instead of a reimplementation that would drift. The DOM stub is a Proxy: any method
// the page starts calling later resolves to a no-op instead of breaking the harness.
const fs = require('fs');

const el = () => {
  const o = {
    textContent: '', className: '', value: '', style: {}, hidden: false,
    tabIndex: 0, firstChild: null,
    classList: { add() {}, remove() {}, contains: () => false },
    appendChild(c) { return c }, querySelectorAll: () => [], querySelector: () => null,
    set innerHTML(_) { throw new Error('index.html must not use innerHTML') },
  };
  return new Proxy(o, { get: (t, k) => (k in t ? t[k] : () => {}), set: (t, k, v) => (t[k] = v, true) });
};

const html = fs.readFileSync(`${__dirname}/index.html`, 'utf8');
const bank = html.match(/id="bank">([\s\S]*?)<\/script>/)[1];
const code = html.match(/<script>\n'use strict';([\s\S]*?)<\/script>/)[1];
const out = el();

global.document = {
  getElementById: id => (id === 'bank' ? { textContent: bank } : id === 'stOut' ? out : el()),
  createElement: el, createElementNS: el, addEventListener() {},
};
global.location = { hash: '#selftest' };

new Function("'use strict';" + code)();
const report = out.textContent;
console.log(report);
process.exit(/失敗 0 項/.test(report) ? 0 : 1);
