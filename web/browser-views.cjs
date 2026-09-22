// Optional populated-view checks. Uses a fresh, temporary save path.
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const {mkdtempSync}=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const directory=mkdtempSync('/tmp/opencode/gamedev-views-');
 const server=spawn('python3',['browser.py','--no-browser','--port','18768','--save-file',`${directory}/test.json`]);
 let browser;
 try{
  for(let n=0;n<60;n++){try{if((await fetch('http://127.0.0.1:18768/api/state')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true});
  const tab=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
  tab.on('pageerror',e=>errors.push(e.message));
  await tab.goto('http://127.0.0.1:18768');
  await tab.getByRole('button',{name:'[Enter] New studio',exact:true}).click();
  await tab.waitForFunction(()=>!busy&&state.started);
  await tab.evaluate(async()=>{await act('speed',0);for(let n=0;n<16;n++)await act('advance',0,{week:true});await act('idea',0);});
  await tab.waitForFunction(()=>!busy);
  // Stop polling during isolated rendering fixtures, retaining generated sales
  // and ledger data. No fixture is posted to the server or saved.
  await tab.evaluate(()=>{
   busy=true;
   state.studio.team=Array.from({length:8},(_,i)=>({...state.studio.team[0],name:`Employee ${i}`,fatigue:i*12,morale:90-i*7}));
   state.studio.current_project.title='A long but plausible production title';
   state.studio.current_project.gdd.findings=Array.from({length:3},()=>({text:'The prototype shows the central mechanic works, but the scope needs careful review before production.'}));
   state.studio.idea_shelf=Array.from({length:5},(_,i)=>({title:`New idea ${i}`,fantasy:'Explore a world with a team and discover what the audience responds to.'}));
    state.studio.catalog=Array.from({length:3},(_,i)=>({title:`Released game ${i}`,units_sold:10000-i*2000,monthly_players:1000,net_revenue:40000,score:80}));
    state.studio.contract_offers=Array.from({length:8},(_,i)=>({title:`Contract offer ${i+1}`,client:`Client ${i+1}`,focus:['Art','Code','Design','Research'][i%4],difficulty:i%4+1,quality_target:55+i*4,required_work:35+i*12,weeks_left:3+i,expires_week:20+i,reputation_required:i*5,pay:12000+i*6500}));
  });
  for(const [width,height] of [[1440,900],[1024,768],[800,600],[390,844]]){
   await tab.setViewportSize({width,height});
   for(const name of ['Projects','People','Business','Market']){
    await tab.evaluate(name=>{page=name;render(true);document.querySelector('#notice').style.display='none';},name);
    const issues=await tab.evaluate(()=>{
     const issues=[];
     for(const el of document.querySelectorAll('header,footer,main,.view-section,.employee-card,.employee-grid,.project-hero,.project-board,.people-board,.business-board,.market-board')){
      if(el.scrollHeight>el.clientHeight+1||el.scrollWidth>el.clientWidth+1)issues.push(`${el.className||el.tagName} overflow ${el.scrollWidth}x${el.scrollHeight} / ${el.clientWidth}x${el.clientHeight}`);
      const r=el.getBoundingClientRect();
      if(r.left<0||r.right>innerWidth+1||r.bottom>innerHeight+1)issues.push(`${el.className||el.tagName} outside viewport`);
     }
     if(/undefined|NaN/.test(document.querySelector('main').textContent))issues.push('Missing data');
     return issues;
    });
    if(process.env.SCREENSHOT_DIR)await tab.screenshot({path:`${process.env.SCREENSHOT_DIR}/${name}-${width}.png`});
    assert.deepEqual(issues,[],`${name} ${width}x${height}`);
   }
   }
   await tab.setViewportSize({width:390,height:844});
   await tab.evaluate(()=>{modal='contracts';drawModal();dialog.showModal();});
   assert.equal(await tab.locator('.contract-table tbody tr').count(),8);
   assert(await tab.locator('dialog .dialog-body').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Contract board overflows horizontally on mobile');
   assert.equal(await tab.locator('.contract-table tbody tr').first().getByRole('button',{name:'Accept',exact:true}).count(),1);
   assert.deepEqual(errors,[]);
  console.log('PASS: populated workspaces fit four viewports; charts use generated ledger and market data.');
 }finally{if(browser)await browser.close();server.kill();}
})().catch(error=>{console.error(error);process.exitCode=1;});
