// Optional real-browser regression test: NODE_PATH=/path/to/node_modules node web/browser-smoke.cjs
// Requires Playwright and its Chromium installation, not needed to run the game.
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');

(async () => {
  const server = spawn(process.env.PYTHON || 'python3', ['browser.py', '--no-browser', '--port', '18767']);
  let browser;
  try {
    for (let n = 0; n < 60; n++) {
      try { if ((await fetch('http://127.0.0.1:18767/api/state')).ok) break; } catch {}
      await new Promise(r => setTimeout(r, 100));
    }
    browser = await chromium.launch({headless: true});
    const page = await browser.newPage({viewport: {width: 1440, height: 900}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:18767');
    await page.getByRole('button', {name: '[Enter] New studio', exact: true}).click();
    await page.locator('#week-progress').waitFor();
    await page.evaluate(() => document.fonts.ready);
    assert(await page.evaluate(() => document.fonts.check('14px "Studio Mono"')), 'Bundled font did not load');
    assert.equal((await page.request.get('http://127.0.0.1:18767/fonts/JetBrainsMono-Regular.woff2')).status(), 200);
    assert.equal(await page.locator('.studio-summary .metric').count(), 4);
    assert.equal(await page.locator('.studio-summary').getByText('Team',{exact:true}).count(),0,'Team count belongs in Team Condition');
    assert.equal(await page.locator('.command-card').count(), 2);
    assert.equal(await page.locator('.work-actions').count(), 0, 'Redundant action strip returned');
    assert.equal(await page.getByRole('columnheader',{name:'Status'}).count(), 0, 'Availability column returned');
    assert.match(await page.locator('footer').innerText(), /PTrust 0\.0 \| CTrust 0\.0/);
    for(const name of ['[N] Explore ideas','[J] Contracts']) {
      await page.getByRole('button',{name,exact:true}).waitFor();
    }
    assert.equal(await page.getByRole('button',{name:'[U] Research',exact:true}).count(),0);
    assert.equal(await page.getByRole('button',{name:'[P] Catalogue',exact:true}).count(),0);
    assert.equal(await page.locator('.command-card').evaluateAll(cards=>new Set(cards.map(x=>Math.round(x.getBoundingClientRect().top))).size),1,'Game and Contract are not side-by-side');
    assert.equal(await page.locator('.studio-glance > section').evaluateAll(cards=>new Set(cards.map(x=>Math.round(x.getBoundingClientRect().top))).size),1,'Team and Market are not side-by-side');
    for (const weight of ['Regular', 'SemiBold', 'Bold']) {
      assert.equal((await page.request.get(`http://127.0.0.1:18767/fonts/JetBrainsMono-${weight}.woff2`)).status(), 200);
    }
    await page.getByRole('button', {name:'[J] Contracts', exact:true}).waitFor();
    await page.getByRole('table').waitFor();
    await page.waitForFunction(() => !busy);
    await page.keyboard.press('Space');
    await page.waitForFunction(() => !busy && state.clock.speed === 0);
    if (process.env.SCREENSHOT) await page.screenshot({path:process.env.SCREENSHOT});
    for (const [width, height] of [[1440,900],[1024,768],[800,600],[390,844]]) {
      await page.setViewportSize({width,height});
      for (const key of ['h','g','t','b','s']) {
        await page.keyboard.press(key);
        assert.equal(await page.evaluate(() => document.documentElement.scrollHeight > innerHeight), false);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
        assert(await page.locator('main').evaluate(m => m.scrollHeight <= m.clientHeight + 1), `Main overflow at ${width}x${height}, page ${key}`);
        const panelsFit = await page.locator('.panel').evaluateAll(panels => panels.every(p => p.scrollHeight <= p.clientHeight + 1));
         assert(panelsFit, `Panel overflow at ${width}x${height}, page ${key}`);
        if (key === 'h') {
          const problems = await page.evaluate(() => {
            const issues=[];
            for(const selector of ['.studio-dashboard','.studio-command','.command-card','.studio-release-table','.studio-intelligence','.studio-glance','.team-panel','.studio-pulse','.activity-panel','header','footer']) {
              for(const el of document.querySelectorAll(selector)) {
                if(el.scrollHeight>el.clientHeight+1 || el.scrollWidth>el.clientWidth+1) issues.push(`${selector} overflows ${el.scrollWidth}x${el.scrollHeight} / ${el.clientWidth}x${el.clientHeight}`);
              }
            }
            const left=document.querySelector('.studio-command').getBoundingClientRect();
            const right=document.querySelector('.studio-intelligence').getBoundingClientRect();
            if(Math.min(left.right,right.right)>Math.max(left.left,right.left)+1 && Math.min(left.bottom,right.bottom)>Math.max(left.top,right.top)+1) issues.push('columns overlap');
            return issues;
          });
          assert.deepEqual(problems, [], `Studio geometry at ${width}x${height}`);
        }
      }
    }
    await page.setViewportSize({width:1440,height:900});
    await page.keyboard.press('h');
    // Synchronous view-model fixtures cannot advance or save the real game.
    await page.evaluate(() => {
      const original=state;
      const geometry=()=>[...document.querySelectorAll('.work-row,.team-panel,.activity-panel')].map(el=>{
        const r=el.getBoundingClientRect(); return [r.x,r.y,r.width,r.height];
      });
      render(true);
      const before=JSON.stringify(geometry());
      try {
        state=structuredClone(state);
        state.studio.team=Array.from({length:8},(_,i)=>({...state.studio.team[0],name:'Employee '+i,fatigue:[8,45,85][i%3]}));
        state.studio.contract={title:'A very long client commitment '.repeat(8),pay:50000,weeks_left:8,work_done:10,required_work:100};
        state.studio.active_research={name:'Research '.repeat(20),effect:'Capability work',progress:0.5};
        render(true);
        if(JSON.stringify(geometry())!==before) throw Error('Studio sections shifted with active work / larger team');
        const colors=[...document.querySelectorAll('.fatigue-num')].slice(0,3).map(el=>getComputedStyle(el).color);
        if(new Set(colors).size!==3) throw Error('Fatigue severity colors missing');
        if(document.querySelector('main').textContent.includes('undefined')) throw Error('Missing display field');
      } finally { state=original; render(true); }
    });
    await page.keyboard.press('n');
    await page.getByRole('dialog').waitFor();
    await page.waitForFunction(() => !busy);
    await page.getByRole('button',{name:'Explore idea',exact:true}).first().click();
    await page.waitForFunction(() => !busy && !dialog.open);
    await page.keyboard.press('g');
    await page.getByRole('button',{name:'[Enter] Experiment',exact:true}).click();
    await page.getByRole('button',{name:'Run experiment',exact:true}).first().click();
    await page.waitForFunction(() => !busy && !dialog.open && !!state.studio.current_project.active_experiment);
    await page.keyboard.press('Space');
    await page.waitForFunction(() => !busy && state.clock.speed === 1);
    const before = await page.locator('#week-progress').evaluate(p => p.value);
    const frameValues = await page.evaluate(async () => {
      const values=[];
      for(let i=0;i<20;i++){
        await new Promise(requestAnimationFrame);
        values.push(document.querySelector('#week-progress').value);
      }
      return values;
    });
    assert(new Set(frameValues).size > 4, 'Meter is still stepping at HTTP polling frequency');
    await page.waitForTimeout(650);
    assert.notEqual(await page.locator('#week-progress').evaluate(p => p.value), before);
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !busy && dialog.open && state.clock.held === 'Popup open');
    const held = await page.evaluate(() => state.clock.progress);
    await page.waitForTimeout(650);
    assert.equal(await page.evaluate(() => state.clock.progress), held);
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !busy && !dialog.open && state.clock.speed === 1);
    await page.keyboard.press('ArrowRight');
    await page.waitForFunction(() => !busy && state.clock.speed === 2);
    await page.keyboard.press('Space');
    await page.waitForFunction(() => !busy && state.clock.speed === 0);
    await page.keyboard.press('u');
    await page.waitForFunction(() => !busy && dialog.open);
    assert.equal(await page.locator('dialog .pager').count(), 0);
    assert.equal(await page.locator('dialog .dialog-card').count(), await page.evaluate(()=>state.research.length));
    assert(await page.locator('.dialog-body').evaluate(el=>el.scrollHeight>el.clientHeight), 'Research list should scroll');
    await page.locator('.dialog-body').evaluate(el=>el.scrollTop=el.scrollHeight);
    assert(await page.locator('.dialog-body').evaluate(el=>el.scrollTop>0));
    await page.keyboard.press('Backspace');
    await page.waitForFunction(() => !busy && !dialog.open);
    assert.equal(await page.evaluate(() => state.clock.speed), 0);
    // Finish the prototype with explicit simulation steps, then exercise the
    // actual Design shortcut and native form controls in the browser.
    await page.evaluate(async () => { for(let i=0;i<3;i++) await act('advance',0,{week:true}); });
    await page.keyboard.press('g');
    await page.keyboard.press('e');
    await page.waitForFunction(() => !busy && dialog.open && modal === 'plan');
    const select = page.locator('select').first();
    assert.equal(await select.evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(36, 37, 58)');
    if(await page.evaluate(()=>CSS.supports('appearance','base-select'))){
      assert.equal(await select.evaluate(el=>getComputedStyle(el,'::picker(select)').backgroundColor),'rgb(36, 37, 58)');
      await select.click();
      if(process.env.PICKER_SCREENSHOT)await page.screenshot({path:process.env.PICKER_SCREENSHOT});
      await page.keyboard.press('Escape');
      assert(await page.locator('dialog').isVisible());
    }
    await select.focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.evaluate(() => modal), 'plan');
    await page.getByRole('button',{name:'Next',exact:true}).click();
    await page.getByRole('button',{name:'Commit to production',exact:true}).click();
    await page.waitForFunction(() => modal === 'confirm');
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => !busy && !dialog.open);
    assert.equal(await page.evaluate(() => state.studio.current_project.stage), 'design');
    await page.keyboard.press('Space');
    await page.waitForFunction(()=>!busy && state.clock.speed>0 && !state.clock.held);
    const designProgress=await page.evaluate(()=>state.clock.progress);
    await page.waitForTimeout(500);
    assert.notEqual(await page.evaluate(()=>state.clock.progress),designProgress,'Design must not freeze time');
    await page.keyboard.press('Space');
    await page.waitForFunction(()=>!busy&&state.clock.speed===0);
    for(const name of ['contracts','applicants','team','competitors','activity','loans','presentation','findings','charts','ledger']){
      await page.evaluate(name=>showModal(name),name);
      assert.equal(await page.locator('dialog .pager').count(),0,`${name} still has pages`);
      assert.equal(await page.locator('.dialog-body').evaluate(el=>getComputedStyle(el).scrollbarWidth),'thin');
      assert(await page.locator('.dialog-body').evaluate(el=>el.getBoundingClientRect().bottom<=innerHeight),`${name} extends below viewport`);
      if(name==='applicants'){
        assert.equal(await page.locator('.candidate-row').count(),await page.evaluate(()=>state.studio.applicants.length));
        assert(await page.locator('.candidate-row').evaluateAll(rows=>rows.every(row=>row.querySelectorAll('.candidate-strongest').length>=1)),'Every applicant needs a strongest skill');
        assert(await page.locator('.candidate-stats').evaluateAll(groups=>[0,1,2,3].every(column=>groups.some(group=>group.children[column].classList.contains('candidate-best')))),'Every skill column needs a highlighted best applicant');
        assert(await page.locator('.candidate-row').evaluateAll(rows=>rows.every(row=>{const card=row.getBoundingClientRect(),button=row.querySelector('button').getBoundingClientRect();return button.right<=card.right&&button.left>card.left+card.width/2&&card.height<=70;})),'Applicant rows should be compact with Hire at right');
        if(process.env.APPLICANT_SCREENSHOT)await page.screenshot({path:process.env.APPLICANT_SCREENSHOT});
      }
      await page.evaluate(()=>closeModal());
    }
    await page.setViewportSize({width:390,height:844});
    await page.evaluate(()=>showModal('applicants'));
    assert(await page.locator('.candidate-row').evaluateAll(rows=>rows.every(row=>row.scrollWidth<=row.clientWidth+1)),'Mobile applicant rows overflow');
    if(process.env.APPLICANT_MOBILE_SCREENSHOT)await page.screenshot({path:process.env.APPLICANT_MOBILE_SCREENSHOT});
    await page.evaluate(()=>closeModal());
    assert.deepEqual(errors, []);
    console.log('PASS: four viewport sizes; experiments, keyboard, scrollable lists, staged plan, running Design clock and popup pause/resume work in Chromium.');
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
