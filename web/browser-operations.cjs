// Real HTTP actions against an isolated, populated post-release simulation.
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
(async()=>{
 const setup=`
import browser
import simulation as sim
Original = browser.BrowserGame
class FixtureGame(Original):
 def __init__(self, path):
  super().__init__(path)
  self.action({'action':'new'})
  self.action({'action':'speed','index':0})
  for _ in range(16): self.action({'action':'advance','week':True})
  s = self.state.studio
  s.cash = 1000000
  s.completed_research = [n['key'] for n in sim.RESEARCH_NODES]
  s.reputation = 40
  g = sim.ReleasedGame(1, 'Ironbound', 'Adventure', 'Space', 'Steam', 75, '2026-09-06', units_sold=4000, net_revenue=28000, production_cost=15000, hype=45, known_bugs=8, monthly_players=900, user_rating=72, press_rating=75, sales_history=[1200,950,700,500,400])
  s.catalog.append(g)
  s.active_sales.append(sim.ActiveSale(g.title,'Steam',75,9.99,.3,.05,400,30,game_id=1,week_units=125))
browser.BrowserGame = FixtureGame
browser.serve(port=18769,save_path='/tmp/opencode/operations-never-saved.json',open_browser=False)
`;
 const server=spawn('python3',['-c',setup]);let browser;
 try{
  for(let n=0;n<60;n++){try{if((await fetch('http://127.0.0.1:18769/api/state')).ok)break;}catch{}await new Promise(r=>setTimeout(r,100));}
  browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:18769');
  await page.locator('.studio-release-table tbody tr').waitFor();
  assert.match(await page.locator('.studio-release-table').innerText(),/400/);
  assert.deepEqual(await page.locator('.studio-release-table th').allTextContents(),['Game','Sales/wk','Lifetime','Hype','Revenue','Profit','Bugs','Players','Support']);
  assert.equal(await page.locator('.studio-release-table').getByRole('button',{name:'Manage'}).count(),0);
  assert(await page.locator('.studio-release-table td').first().evaluate(el=>parseFloat(getComputedStyle(el).fontSize)>=13&&Number(getComputedStyle(el).fontWeight)>=600));
  assert(await page.locator('.command-card p').first().evaluate(el=>parseFloat(getComputedStyle(el).fontSize)>=14&&Number(getComputedStyle(el).fontWeight)>=600));
  assert(await page.evaluate(()=>Math.abs(document.querySelector('.studio-command').clientHeight-document.querySelector('.studio-release-table').clientHeight)<=1),'Studio Command and Released Games are not half-and-half');
  assert.match(await page.locator('.studio-command').innerText(),/Original game[\s\S]*Client work/i);
  assert.equal(await page.locator('.studio-command').getByRole('button',{name:/Research|Catalogue/}).count(),0);
  assert.equal(await page.locator('.studio-pulse .rank-row').count(),10);
  assert.equal(await page.locator('.studio-pulse .rank-game small').first().evaluate(el=>getComputedStyle(el).display),'block');
  if(process.env.SCREENSHOT_DIR)await page.screenshot({path:process.env.SCREENSHOT_DIR+'/operations-studio.png'});
  await page.locator('.studio-release-table [data-select-release]').click();
  await page.waitForFunction(()=>document.querySelector('.game-command')?.textContent.includes('Ironbound')&&!dialog.open);
  assert.equal(await page.locator('.release-select-row.selected').count(),1);
  await page.locator('[name="studio-update-size"]').selectOption('0');
  if(process.env.SCREENSHOT_DIR)await page.screenshot({path:process.env.SCREENSHOT_DIR+'/operations-selected.png'});
  await page.getByRole('button',{name:'Queue update',exact:true}).click();
  await page.waitForFunction(()=>!busy&&state.studio.active_update?.size==='Hotfix');
  await page.getByRole('button',{name:'Marketing · community · details',exact:true}).click();
  await page.waitForFunction(()=>!busy&&modal==='management');
  assert.match(await page.locator('.release-metrics').innerText(),/TRACKED PROFIT\s+\$9,500/);
  assert.equal(await page.locator('.sales-history rect').count(),5);
  if(process.env.SCREENSHOT_DIR)await page.screenshot({path:process.env.SCREENSHOT_DIR+'/operations-detail.png'});
  await page.getByRole('button',{name:'Fund campaign',exact:true}).click();
  await page.waitForFunction(()=>!busy&&state.studio.active_promotions.length===1);
  await page.getByRole('button',{name:'Start community action',exact:true}).click();
  await page.waitForFunction(()=>!busy&&state.studio.active_community_actions.length===1);
  await page.getByRole('dialog').getByRole('button',{name:'Support: Active',exact:true}).click();
  await page.waitForFunction(()=>!busy&&state.studio.catalog[0].support_level!=='Active');
  await page.getByRole('button',{name:'− Price',exact:true}).click();
  await page.waitForFunction(()=>!busy&&state.studio.catalog[0].price!==9.99);
  assert(await page.locator('.operation-queues').innerText().then(x=>x.includes('Hotfix')&&x.includes('Social media push')));
  await page.evaluate(()=>closeModal());
  for(const [width,height] of [[1440,900],[1024,768],[800,600],[390,844]]){
   await page.setViewportSize({width,height});
   await page.keyboard.press('h');
   const issues=await page.evaluate(()=>[...document.querySelectorAll('main,.studio-dashboard,.studio-command,.command-card,.studio-release-table,.studio-intelligence,.studio-glance,.studio-pulse,.team-panel,.activity-panel')].filter(el=>el.scrollHeight>el.clientHeight+1||el.scrollWidth>el.clientWidth+1).map(el=>`${el.className}: ${el.scrollWidth}x${el.scrollHeight} / ${el.clientWidth}x${el.clientHeight}`));
   assert.deepEqual(issues,[],`Populated Studio ${width}x${height}`);
   await page.keyboard.press('s');
    assert.equal(await page.locator('.market-workspace .rank-row').count(),await page.evaluate(()=>state.market_chart.length),'Market shows the whole chart');
    assert.equal(await page.locator('.market-workspace').getByRole('button',{name:'Full chart',exact:true}).count(),0);
  }
  await page.setViewportSize({width:1440,height:900});await page.keyboard.press('h');
  await page.getByRole('button',{name:'Original game',exact:true}).click();
  assert.equal(await page.locator('.release-select-row.selected').count(),0);
  assert.match(await page.locator('.game-command').innerText(),/Original game/i);
  assert.deepEqual(errors,[]);console.log('PASS: post-release metrics, updates, marketing, community, support, pricing, ten-row pulse and full market chart.');
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
