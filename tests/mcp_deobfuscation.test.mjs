import assert from 'node:assert/strict';
import {test} from 'node:test';
import vm from 'node:vm';
import {Deobfuscator} from '../vendor/js-reverse-mcp/build/src/modules/deobfuscator/Deobfuscator.js';
import {PackerDeobfuscator} from '../vendor/js-reverse-mcp/build/src/modules/deobfuscator/PackerDeobfuscator.js';
import {JSVMPDeobfuscator} from '../vendor/js-reverse-mcp/build/src/modules/deobfuscator/JSVMPDeobfuscator.js';

// Execute only these trusted synthetic fixtures, never caller-supplied decoder input.
function observedValue(code) {
  const context={};
  vm.runInNewContext(code,context,{timeout:1000});
  return JSON.stringify(context.result);
}

async function assertEquivalent(code, options={}, decoder=new Deobfuscator()) {
  const result=await decoder.deobfuscate({code,...options});
  assert.equal(observedValue(result.code),observedValue(code),result.code);
  return result;
}

test('sequential requests never reuse another source string table',async()=>{
  const decoder=new Deobfuscator();
  await assertEquivalent("const _0xabc=['previous-job'];globalThis.result=_0xabc[0];",{},decoder);
  await assertEquivalent("function read(_0xabc){return _0xabc[0];}globalThis.result=read(['current-job']);",{},decoder);
});

test('concurrent requests and their cached results keep independent string tables',async()=>{
  const decoder=new Deobfuscator();
  const sources=['first','second','third'].map(value=>`const _0xabc=['${value}'];globalThis.result=_0xabc[0];`);
  await Promise.all(sources.map(code=>assertEquivalent(code,{},decoder)));
  await Promise.all(sources.map(code=>assertEquivalent(code,{},decoder)));
});

test('double negation retains boolean value and type',async()=>{
  await assertEquivalent("const values=['hello',0,null,{},[]];globalThis.result=values.map(value=>[!!value,typeof !!value]);");
});

for(const [name,code] of [
  ['mixed indexes',"const _0xabc=[7,'a'];globalThis.result=[_0xabc[0],_0xabc[1]];"],
  ['reverse mutation',"const _0xabc=['a','b'];_0xabc.reverse();globalThis.result=_0xabc[0];"],
  ['index assignment',"const _0xabc=['a','b'];_0xabc[0]='changed';globalThis.result=_0xabc[0];"],
  ['shadowed binding',"const _0xabc=['outer'];function read(_0xabc){return _0xabc[0]}globalThis.result=read(['inner']);"],
]) test(`string tables preserve ${name}`,()=>assertEquivalent(code));

test('parsed string values retain literal backslashes and ordinary escapes',async()=>{
  await assertEquivalent(String.raw`globalThis.result=['\\x41','\\u0041','\x41','\u0041'];`);
});

test('renaming preserves object properties, shorthand and pre-existing names',async()=>{
  for(const code of [
    "const _0xabc=1;const obj={_0xabc:7};globalThis.result=obj['_0xabc'];",
    "const _0xabc=7;const obj={_0xabc};globalThis.result=obj['_0xabc'];",
    "const var_0=9;const _0xabc=7;globalThis.result=[var_0,_0xabc];",
  ]) await assertEquivalent(code,{renameVariables:true});
});

test('default deobfuscation keeps AAEncode input out of the host', async () => {
  delete globalThis.__spider_audit__;
  const code="('゜-゜',globalThis.__spider_audit__=37,'var decoded=1;')";
  const result=await new Deobfuscator().deobfuscate({code});
  assert.equal(globalThis.__spider_audit__, undefined);
  assert.ok(result.warnings.some(warning=>warning.includes('dynamic decoding disabled')));
});

test('Packer arguments are parsed as data and valid literal packs still decode', async () => {
  delete globalThis.__spider_audit__;
  const unpacker=new PackerDeobfuscator();
  await unpacker.deobfuscate({code:"eval(function(p,a,c,k,e,d){}(globalThis.__spider_audit__=37,2,0,''))"});
  assert.equal(globalThis.__spider_audit__,undefined);
  const result=await unpacker.deobfuscate({code:"eval(function(p,a,c,k,e,d){}('0 1',2,2,'hello|world',0,{}))"});
  assert.equal(result.code,'hello world');
});

test('JSVMP decoding never executes string arrays or JSFuck/JJEncode input', async () => {
  const decoder=new JSVMPDeobfuscator();
  for(const method of ['restoreJSFuck','restoreJJEncode']) {
    delete globalThis.__spider_audit__;
    await decoder[method]("(globalThis.__spider_audit__=37)",[]);
    assert.equal(globalThis.__spider_audit__,undefined,method);
  }
  delete globalThis.__spider_audit__;
  await decoder.restoreObfuscatorIO('var _0xabc = [globalThis.__spider_audit__=37];',false,[],[]);
  assert.equal(globalThis.__spider_audit__,undefined);
});

test('cache distinguishes complete code and output-affecting options', async () => {
  const deobfuscator=new Deobfuscator();
  const prefix='// '+'same-prefix-'.repeat(100)+'\n';
  const first=await deobfuscator.deobfuscate({code:prefix+"const value='A';",auto:false});
  const second=await deobfuscator.deobfuscate({code:prefix+"const value='B';",auto:false});
  assert.notEqual(first.code,second.code);
  const code='const a = 1; console.log(a);';
  const plain=await deobfuscator.deobfuscate({code,auto:false,renameVariables:false});
  const renamed=await deobfuscator.deobfuscate({code,auto:false,renameVariables:true});
  assert.notStrictEqual(plain,renamed);
  assert.strictEqual(await deobfuscator.deobfuscate({code,auto:false,renameVariables:false}),plain);
});
