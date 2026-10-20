const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const vm = require('node:vm');

function value(code) {
  const context = {};
  vm.runInNewContext(code, context, {timeout:1000});
  return JSON.stringify(context.result);
}

for (const [index, code] of [
  'if(true){let hidden=7;}globalThis.result=typeof hidden;',
  'let x=1;if(true){let x=2;}globalThis.result=x;',
  'const x=1;if(false){}else{const x=2;}globalThis.result=x;',
  'let read;if(true){let x=2;read=()=>x;}let x=1;globalThis.result=[read(),x];',
].entries()) for (const entry of ['prune-fake-branches.js', 'run-pipeline.js']) {
  test(`${entry} preserves lexical block fixture ${index}`, t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'spider-branch-regression-'));
    t.after(() => fs.rmSync(root, {recursive:true, force:true}));
    const input = path.join(root, `input-${index}.js`);
    fs.writeFileSync(input, code);
    const output = path.join(root, `${entry}-${index}`);
    const run = spawnSync(process.execPath, [path.join(__dirname, entry), input, output, 'generic'],
                          {encoding:'utf8', timeout:30000});
    assert.equal(run.status, 0, run.stderr);
    let final = output;
    if (entry === 'run-pipeline.js') {
      assert.equal(JSON.parse(run.stdout).status, 'ok', run.stdout);
      final = path.join(output, 'final.js');
    }
    assert.equal(value(fs.readFileSync(final, 'utf8')), value(code), `${entry}: ${code}`);
  });
}

for (const timedOut of [false, true]) {
  test(`pipeline ${timedOut ? 'timeout' : 'step failure'} keeps evidence and exits nonzero`, t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'spider-pipeline-failure-'));
    t.after(() => fs.rmSync(root, {recursive:true, force:true}));
    const input = path.join(root, 'input.js');
    const output = path.join(root, 'output');
    fs.writeFileSync(input, 'globalThis.result = 1;');
    const good = path.join(root, 'good.js');
    fs.writeFileSync(good, `require('node:fs').writeFileSync(process.argv[3], 'globalThis.result = 2;');`);
    const failed = path.join(root, 'failed.js');
    fs.writeFileSync(failed, timedOut ? 'setInterval(()=>{},1000);' : 'process.exit(7);');
    const never = path.join(root, 'never.js');
    const marker = path.join(root, 'should-not-run');
    fs.writeFileSync(never, `require('node:fs').writeFileSync(${JSON.stringify(marker)}, 'wrong');`);
    const preload = path.join(root, 'preload.cjs');
    const steps = [
      {id:'fixture_good',script:'good.js',scriptPath:good,timeoutMs:10000},
      {id:'fixture_failure',script:'failed.js',scriptPath:failed,timeoutMs:timedOut ? 250 : 10000},
      {id:'fixture_never',script:'never.js',scriptPath:never,timeoutMs:10000},
    ];
    fs.writeFileSync(preload, `require(${JSON.stringify(path.join(__dirname, 'pipeline-config.js'))}).buildPipeline = () => ${JSON.stringify(steps)};`);
    const run = spawnSync(process.execPath, ['--require', preload,
      path.join(__dirname, 'run-pipeline.js'), input, output, 'generic'],
      {encoding:'utf8',timeout:30000});
    const report = JSON.parse(fs.readFileSync(path.join(output, 'pipeline-report.json'), 'utf8'));
    const status = timedOut ? 'timed_out' : 'failed';
    assert.equal(report.status, status);
    assert.equal(JSON.parse(run.stdout).status, status);
    assert.equal(report.failedStep, 'fixture_failure');
    assert.equal(report.steps.length, 2);
    assert.equal(report.lastGoodFile, '01_fixture_good.js');
    assert.equal(fs.readFileSync(path.join(output, 'final.js'), 'utf8'),
                 fs.readFileSync(path.join(output, report.lastGoodFile), 'utf8'));
    assert.equal(value(fs.readFileSync(path.join(output, 'final.js'), 'utf8')), '2');
    assert.equal(fs.existsSync(marker), false);
    assert.notEqual(run.status, 0, run.stdout + run.stderr);
    assert.equal(run.signal, null);
  });
}
