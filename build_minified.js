/**
 * build_minified.js
 * -----------------
 * Reads journal_generator.html, minifies CSS (clean-css),
 * obfuscates inline JS (javascript-obfuscator), minifies HTML,
 * and writes journal_generator.min.html.
 */

const fs = require('fs');
const path = require('path');
const CleanCSS = require('clean-css');
const JavaScriptObfuscator = require('javascript-obfuscator');

const INPUT  = path.join(__dirname, 'journal_generator.html');
const OUTPUT = path.join(__dirname, 'journal_generator.min.html');

// -- 1. Read the source HTML --
const html = fs.readFileSync(INPUT, 'utf-8');

// -- 2. Extract CSS from <style>...</style> --
const styleMatch = html.match(/<style>([\s\S]*?)<\/style>/);
if (!styleMatch) {
  console.error('ERROR: Could not find <style> tag in HTML.');
  process.exit(1);
}
const originalCSS = styleMatch[1];

// -- 3. Extract inline JS (the second <script> - not the CDN one) --
const scriptBlocks = [];
const scriptRegex = /<script(?:\s[^>]*)?>[\s\S]*?<\/script>/g;
let m;
while ((m = scriptRegex.exec(html)) !== null) {
  if (!m[0].match(/<script\s[^>]*src\s*=/)) {
    scriptBlocks.push({
      full: m[0],
      index: m.index,
      content: m[0].replace(/^<script[^>]*>/, '').replace(/<\/script>$/, '')
    });
  }
}

if (scriptBlocks.length === 0) {
  console.error('ERROR: Could not find inline <script> tag in HTML.');
  process.exit(1);
}

// Use the last inline script block (the main application code)
const inlineScript = scriptBlocks[scriptBlocks.length - 1];
const originalJS = inlineScript.content;

console.log('-- Source analysis --');
console.log('  CSS size : ' + Buffer.byteLength(originalCSS, 'utf-8').toLocaleString() + ' bytes');
console.log('  JS  size : ' + Buffer.byteLength(originalJS, 'utf-8').toLocaleString() + ' bytes');

// -- 4. Minify CSS with clean-css --
const cssResult = new CleanCSS({ level: 2 }).minify(originalCSS);

if (cssResult.errors.length > 0) {
  console.error('CSS minification errors:', cssResult.errors);
  process.exit(1);
}
const minifiedCSS = cssResult.styles;
console.log('  CSS minified : ' + Buffer.byteLength(minifiedCSS, 'utf-8').toLocaleString() + ' bytes');

// -- 5. Obfuscate & minify JS with javascript-obfuscator --
const obfuscationResult = JavaScriptObfuscator.obfuscate(originalJS, {
  compact: true,
  controlFlowFlattening: true,
  controlFlowFlatteningThreshold: 0.75,
  deadCodeInjection: true,
  deadCodeInjectionThreshold: 0.4,
  stringArray: true,
  stringArrayEncoding: ['base64'],
  stringArrayThreshold: 0.75,
  renameGlobals: false,
  identifierNamesGenerator: 'hexadecimal',
  selfDefending: false,
  target: 'browser',
  reservedNames: [
    'parseAndPreview',
    'generateExcel',
    'downloadFile',
    'generateVouchers',
    'goStep'
  ]
});

const obfuscatedJS = obfuscationResult.getObfuscatedCode();
console.log('  JS  obfuscated : ' + Buffer.byteLength(obfuscatedJS, 'utf-8').toLocaleString() + ' bytes');

// -- 6. Reassemble the HTML --
let outputHTML = html;

// Replace CSS
outputHTML = outputHTML.replace(
  /<style>[\s\S]*?<\/style>/,
  '<style>' + minifiedCSS + '</style>'
);

// Replace inline script
outputHTML = outputHTML.replace(
  inlineScript.full,
  '<script>' + obfuscatedJS + '</script>'
);

// -- 7. Minify HTML structure --
// Protect <style> and <script> blocks from HTML minification
const protectedBlocks = [];
let protectIndex = 0;

outputHTML = outputHTML.replace(/<style>[\s\S]*?<\/style>/g, function(match) {
  const placeholder = '___PROTECTED_' + protectIndex + '___';
  protectedBlocks.push({ placeholder: placeholder, content: match });
  protectIndex++;
  return placeholder;
});

outputHTML = outputHTML.replace(/<script[\s\S]*?<\/script>/g, function(match) {
  const placeholder = '___PROTECTED_' + protectIndex + '___';
  protectedBlocks.push({ placeholder: placeholder, content: match });
  protectIndex++;
  return placeholder;
});

// Remove HTML comments
outputHTML = outputHTML.replace(/<!--[\s\S]*?-->/g, '');

// Collapse whitespace between tags
outputHTML = outputHTML.replace(/>\s+</g, '><');

// Remove leading/trailing whitespace on each line, then join
outputHTML = outputHTML
  .split('\n')
  .map(function(line) { return line.trim(); })
  .filter(function(line) { return line.length > 0; })
  .join('');

// Restore protected blocks
for (var i = 0; i < protectedBlocks.length; i++) {
  outputHTML = outputHTML.replace(protectedBlocks[i].placeholder, protectedBlocks[i].content);
}

// -- 8. Write output --
fs.writeFileSync(OUTPUT, outputHTML, 'utf-8');

const originalSize = fs.statSync(INPUT).size;
const minifiedSize = fs.statSync(OUTPUT).size;
const ratio = ((1 - minifiedSize / originalSize) * 100).toFixed(1);

console.log('');
console.log('-- Result --');
console.log('  Original  : ' + originalSize.toLocaleString() + ' bytes  (' + INPUT + ')');
console.log('  Minified  : ' + minifiedSize.toLocaleString() + ' bytes  (' + OUTPUT + ')');
console.log('  Reduction : ' + ratio + '%');
console.log('  Done.');
