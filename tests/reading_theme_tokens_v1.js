/* Pure Node WCAG 2.2 contrast audit for the final V1 colour tokens.
 * Does not require npm, external API, visual judgement or private keys.
 */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const css=fs.readFileSync('site/reading-theme-v1.css','utf8');
function tokens(selector){
  const escaped=selector.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const block=css.match(new RegExp(escaped+'\\s*\\{([^}]+)\\}'));
  assert.ok(block,'Missing palette '+selector);
  const result=Object.create(null);
  for(const [,name,value] of block[1].matchAll(/--([a-z0-9-]+):\s*(#[a-f0-9]{6})\s*;/gi))
    result[name]=value.toUpperCase();
  return result;
}
function relativeLuminance(hex){
  const channels=hex.slice(1).match(/../g).map(c=>parseInt(c,16)/255)
    .map(c=>c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4));
  return channels[0]*0.2126+channels[1]*0.7152+channels[2]*0.0722;
}
function contrast(a,b){
  const x=relativeLuminance(a),y=relativeLuminance(b);
  return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05);
}
const palettes=[['Paper Calm',tokens(':root.light')],['Soft Graphite',tokens(':root')]];
const tests=[
  ['reader body AAA','text','reader-paper',7],
  ['secondary reader text AA','muted','reader-paper',4.5],
  ['secondary sidebar text AA','muted','side',4.5],
  ['secondary toolbar text AA','muted','surface2',4.5],
  ['link text AAA','link','reader-paper',7],
  ['brand labels AAA','accent','reader-paper',7],
  ['word highlight text AA','accent','accent-low',4.5],
  ['button label AA','on-accent','accent',4.5],
  ['error text AA','danger','reader-paper',4.5],
  ['warning text AA','warning','reader-paper',4.5],
  ['success text AA','success','reader-paper',4.5],
  ['focus ring non-text','focus-ring','reader-paper',3],
  ['form boundary non-text','input-border','reader-paper',3],
  ['form boundary on toolbar','input-border','surface2',3],
  ['selected navigation outline','nav-border','side',3]
];
for(const [name,pal] of palettes){
  for(const [description,fore,back,min] of tests){
    assert.ok(pal[fore]&&pal[back],name+': undefined '+fore+'/'+back);
    const ratio=contrast(pal[fore],pal[back]);
    assert.ok(ratio>=min, name+' '+description+': '+ratio.toFixed(2)+':1 below '+min+':1');
    console.log('PASS',name,description,ratio.toFixed(2)+':1 >='+min+':1');
  }
  assert.equal(pal['panel'],pal['surface'],'Password input must follow active theme');
}
assert.ok(css.includes('@media print'),'White ink-on-paper print override missing');
assert.ok(css.includes('color: var(--on-accent)'),'Accent button text colour must not inherit page background');
console.log('V1 THEME TOKENS PASSED:',tests.length*palettes.length,'WCAG contrast checks, default themes and print tokens');
