'use strict';
let state, page='Studio', busy=false, modal=null, modalPage=0, lastRender='', connected=true, shownDecision='';
const app=document.querySelector('#app');
const dialog=document.createElement('dialog');
dialog.setAttribute('aria-labelledby','dialog-title');
document.body.append(dialog);
let returnFocus=null;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(v||0);
const btn=(text,action,index=0,primary=false)=>`<button data-action="${action}" data-index="${index}" class="${primary?'primary':''}">${esc(text)}</button>`;
const open=(text,name,primary=false)=>`<button data-open="${name}" class="${primary?'primary':''}">${esc(name==='loans'?text.replace('[B]','[F]'):text)}</button>`;
const record=(title,body)=>`<article class="dialog-card"><h3>${esc(title)}</h3>${body}</article>`;
function notify(text){const n=document.querySelector('#notice');n.textContent=text;n.style.display='block';clearTimeout(notify.timer);notify.timer=setTimeout(()=>n.style.display='none',5000);}

async function act(action,index=0,extra={}){
 if(busy)return false;
 busy=true;
 try{
  const response=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json','X-Game-Token':state.token},body:JSON.stringify({action,index,...extra})});
  const next=await response.json();if(!response.ok)throw Error(next.error||'Request failed.');
  state=next;connected=true;render(true);
  if(!['overlay','speed','pause'].includes(action))notify(action==='save'?'Studio saved.':state.logs?.[0]||'Done.');
  return true;
 }catch(e){notify(e.message);return false;}finally{busy=false;}
}
function heading(title,sub){return `<div class="page-heading"><h1>${esc(title)}</h1><span class="muted small">${esc(sub)}</span></div>`;}
function projectSummary(){const p=state.studio.current_project;if(!p)return '<p>No original game in progress. Explore an idea when the studio is ready.</p><div class="actions">'+open('[N] Explore ideas','ideas',true)+'</div>';
 const stages=['concept','design','development','testing','gold'];
 let body=`<div class="stage">${stages.map(x=>`<span class="${p.stage===x?'current':''}">${x==='gold'?'RELEASE':x.toUpperCase()}</span>`).join('')}</div><h3>${esc(p.title)}</h3>`;
 if(p.stage==='concept')body+=`<p>${esc(p.active_experiment?`${p.active_experiment.replaceAll('_',' ')} · ${p.experiment_days_left} workdays remaining`:p.gdd.uncertainty)}</p><div class="actions">${p.active_experiment?'':open('[Enter] Experiments','experiments',true)}${btn('[E] Design','design')}${open('Findings','findings')}</div>`;
 else if(p.stage==='design')body+=`<p>Production awaits your commitment. The studio and market keep running when this review is closed.</p><div class="actions">${open('[Enter] Review plan','plan',true)}${open('[T] Presentation','presentation')}</div>`;
 else{const testing=p.stage==='testing',total=testing?p.bug_work:p.total_work,done=testing?p.bug_work_done:p.work_done;body+=`<progress aria-label="Project completion" value="${done}" max="${Math.max(total,1)}"></progress><p>${Math.round(done/Math.max(total,1)*100)}% · ${p.weeks} weeks on project</p><div class="actions">${p.ready_for_release?btn('[R] Release','release',0,true):open('Project details','findings')}${state.decision?open('Decision required','decision',true):''}</div>`;}return body;
}
function availability(e){
 if(e.burnout_weeks_left)return `Burnout (${e.burnout_weeks_left}w)`;
 if(e.vacation_weeks_left)return `Vacation (${e.vacation_weeks_left}w)`;
 if(e.training_weeks_left)return `Training (${e.training_weeks_left}w)`;
 if(e.onboarding_weeks_left)return 'Onboarding';
 return 'Available';
}
function metric(label,value,tone=''){return `<div class="metric ${tone}"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`;}
function overview(){
 const s=state.studio;
 const cashTone=s.cash<0?'cash-danger':'cash-good';
 const runwayTone=state.runway<4?'runway-danger':state.runway<8?'runway-caution':'runway-good';
 return `<div class="studio-summary" aria-label="Studio health">
  ${metric('Cash',money(s.cash),cashTone)}
  ${metric('Monthly burn',money(state.monthly_cost),'burn-expense')}
  ${metric('Runway',(state.runway>=10?Math.round(state.runway):state.runway.toFixed(1))+' mo',runwayTone)}
  ${metric('Audience',`${s.followers.toLocaleString()} fans`,'audience')}
 </div>
 <div class="studio-dashboard">
  ${studioCommand()}
  ${studioReleaseTable()}
  <aside class="studio-intelligence">
   <div class="studio-glance">${studioTeam()}${studioPulse()}</div>
   <div class="activity-panel"><div class="section-line"><h2>Recent activity</h2>${open('Full log →','activity')}</div><div class="activity-list">${Array.from({length:3},(_,i)=>`<div class="event">${esc(state.logs[i]||' ')}</div>`).join('')}</div></div>
  </aside>
 </div>`;
}

function render(force=false){
 if(!state.started){app.innerHTML=`<div class="welcome"><span class="eyebrow">A bootstrapped studio simulation</span><h1>INDIE GAME<br>DEV SIM</h1><p>Build a team. Make games. Keep the lights on.</p><div class="actions">${btn('[Enter] New studio','new',0,true)}${state.can_load?btn('Load studio','load'):''}</div><p class="small">Local game · no account · version 11 saves supported</p></div>`;return;}
 const signature=JSON.stringify([page,state.date,state.studio.current_project,state.studio.cash,state.studio.team,state.studio.idea_shelf.length,state.logs[0]]);
 if(force||signature!==lastRender){
  const focus=document.activeElement;const action=focus?.dataset?.action,opened=focus?.dataset?.open;
  app.innerHTML=`<header><nav aria-label="Main navigation">${[['Studio','H'],['Projects','G'],['People','T'],['Business','B'],['Market','S']].map(([p,k])=>`<button data-page="${p}" class="${p===page?'active':''}" ${p===page?'aria-current="page"':''}>[${k}]${p}</button>`).join('')}</nav><button data-open="settings">[Esc] Settings</button></header><main>${({Studio:overview,Projects:projectsView,People:peopleView,Business:businessView,Market:marketView}[page])()}</main><footer><div class="time-strip"><progress id="week-progress" max="1" aria-label="Week progress"></progress><span id="date"></span><span class="financial">${money(state.studio.cash)} | ${state.runway.toFixed(1)} mo</span><span class="trust">PTrust ${state.studio.reputation.toFixed(1)} | CTrust ${state.studio.contractor_reputation.toFixed(1)}</span></div><div class="footer-controls"><button data-action="slower" aria-label="Slower">[&lt;]</button><button id="pause" data-action="pause">[Space]</button><button data-action="faster" aria-label="Faster">[&gt;]</button><span id="clock-status"></span></div></footer>`;
  if(!dialog.open&&(action||opened)){const target=[...app.querySelectorAll('button')].find(b=>action?b.dataset.action===action:b.dataset.open===opened);target?.focus({preventScroll:true});}
  lastRender=signature;
 }
 updateClock();
}
let meterMotion=null, paintedWeek=null;
function updateClock(){
 if(!state.started)return;
 const absolute=state.clock.week-1+state.clock.progress;
 const running=connected&&!state.clock.held&&state.clock.speed&&!document.hidden;
 const now=performance.now();
 meterMotion={from:running?(paintedWeek??absolute):absolute,to:absolute+(running?state.clock.weeks_per_second*.25:0),start:now};
 document.querySelector('#date').textContent=`${state.date} · W${state.clock.week}`;
 document.querySelector('#pause').textContent=`[Space] ${state.clock.speed?'▶'.repeat(state.clock.speed):'Ⅱ'}`;
 document.querySelector('#clock-status').textContent=!connected?'Disconnected':state.clock.held||(state.clock.speed?'Running':'Paused');
 if(!running){paintedWeek=absolute;document.querySelector('#week-progress').value=state.clock.progress;}
}
function animateClock(now){
 if(meterMotion&&state?.started){
  const fraction=Math.min(1,Math.max(0,(now-meterMotion.start)/250));
  paintedWeek=meterMotion.from+(meterMotion.to-meterMotion.from)*fraction;
  const meter=document.querySelector('#week-progress');
  if(meter)meter.value=paintedWeek-Math.floor(paintedWeek);
 }
 requestAnimationFrame(animateClock);
}
requestAnimationFrame(animateClock);

const titles={ideas:'Idea shelf',experiments:'Choose an experiment',plan:'Design & production plan',presentation:'Presentation direction',findings:'Findings & project history',team:'Team detail',applicants:'Applicants',contracts:'Contract board',research:'Research capabilities',loans:'Financing',catalogue:'Released games',competitors:'Competition',activity:'Activity log',settings:'Settings & controls',decision:'Production decision',confirm:'Confirm commitment'};
function paginated(items,draw){return items.map(draw).join('')||'<p>Nothing here yet.</p>';}
function applicantComparison(applicants){
 if(!applicants.length)return '<p>No applicants right now. The pool refreshes monthly.</p>';
 const skills=['design','art','code','research'];
 const columnBest=Object.fromEntries(skills.map(skill=>[skill,Math.max(...applicants.map(person=>person[skill]))]));
 const rows=applicants.map((person,index)=>{
  const personalBest=Math.max(...skills.map(skill=>person[skill]));
  const cells=skills.map(skill=>{
   const classes=['candidate-stat'];
   if(person[skill]===personalBest)classes.push('candidate-strongest');
   if(person[skill]===columnBest[skill])classes.push('candidate-best');
   return `<span class="${classes.join(' ')}"><small>${skill==='research'?'Rsch':esc(skill)}</small><strong>${person[skill]}</strong></span>`;
  }).join('');
  return `<article class="candidate-row"><div class="candidate-name"><strong>${esc(person.name)}</strong><small>${esc(person.role)}</small></div><span class="candidate-salary">${money(person.salary/12)}<small>/ month</small></span><div class="candidate-stats">${cells}</div>${btn('Hire','hire',index,true)}</article>`;
 }).join('');
 return `<div class="candidate-key"><span><i class="candidate-key-best"></i>Best in applicant pool</span><span><strong>Bold</strong> = candidate's strongest skill</span></div><div class="candidate-table-header"><span>Candidate / role</span><span>Salary</span><div><span>Design</span><span>Art</span><span>Code</span><span>Research</span></div><span></span></div><div class="candidate-list">${rows}</div>`;
}
function contractComparison(contracts){
 if(!contracts.length)return '<p>No contract offers right now. The board refreshes over time.</p>';
 const rows=contracts.map((contract,index)=>`<tr><td data-label="Contract"><strong>${esc(contract.title)}</strong><small>${esc(contract.client)}</small></td><td data-label="Focus">${esc(contract.focus)}</td><td data-label="Difficulty"><strong>D${contract.difficulty}</strong><small>Quality ${contract.quality_target}</small></td><td data-label="Work"><strong>${number(contract.required_work)}</strong></td><td data-label="Deadline"><strong>${contract.weeks_left}w</strong><small>${contract.expires_week?`Expires W${contract.expires_week}`:'Open offer'}</small></td><td data-label="Trust">${contract.reputation_required}</td><td data-label="Payout"><strong class="green">${money(contract.pay)}</strong><small>${money(contract.pay/Math.max(1,contract.required_work))} / work</small></td><td>${btn('Accept','contract',index)}</td></tr>`).join('');
 return `<div class="contract-table-wrap"><table class="contract-table"><thead><tr><th>Contract / client</th><th>Focus</th><th>Difficulty</th><th>Work</th><th>Deadline</th><th>Trust</th><th>Payout</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
function modalBody(){const s=state.studio,p=s.current_project;
 switch(modal){
 case 'management':return managementBody();
 case 'charts':case 'ledger':return analysisBody(modal);
 case 'ideas':return paginated(s.idea_shelf,(x,i)=>record(x.title,`<p>${esc(x.fantasy)}</p><p>${esc(x.uncertainty)}</p>${!p?btn('Explore idea','idea',i,true):'<p>Finish or shelve the current project first.</p>'}`));
 case 'experiments':return !p||p.stage!=='concept'?'<p>No concept is open.</p>':p.active_experiment?`<p>${esc(p.active_experiment)} · ${p.experiment_days_left} workdays left. Close this popup to let time run.</p>`:paginated(state.experiments,(e,i)=>record(e.name,`<p>${esc(e.blurb)}</p><p class="green">${e.weeks} weeks</p>${btn('Run experiment','experiment',i,true)}`));
 case 'presentation':return paginated(p?.gdd.presentation_options||[],(x,i)=>record(x.name,`<p>${esc(x.note)}</p><p>${x.work.toFixed(2)}× work</p>${btn(i===state.presentation?'Selected':'Choose direction','presentation',i,i===state.presentation)}`));
 case 'plan':{if(p?.stage!=='design')return '<p>No design review is open.</p>';const fields=Object.keys(state.options).slice(modalPage*4,modalPage*4+4);return `<p>Setup costs are charged when you commit. Locked capabilities are checked before production starts.</p><div class="form-grid">${fields.map(k=>`<label>${esc(k.replace('selected_','').replaceAll('_',' '))}<select data-field="${k}">${state.plan[k]===-1?'<option selected disabled>Automatic price</option>':''}${state.options[k].map(o=>`<option value="${o.index}" ${o.index===state.plan[k]?'selected':''}>${esc(o.name)}</option>`).join('')}</select></label>`).join('')}</div><p class="warning">${state.requirements.length?'Requires: '+esc(state.requirements.join(', ')):'Capability checks passed.'}</p><div class="actions">${open('[T] Presentation','presentation')}${btn('Commit to production','commit',0,true)}</div>`;}
 case 'findings':return paginated([...(p?.gdd.findings||[]).map(f=>f.text),...(p?.gdd.history||[]).map(h=>h.entry)],x=>record('Project record',`<p>${esc(x)}</p>`));
 case 'activity':return paginated(state.logs,x=>`<article class="dialog-card"><p>${esc(x)}</p></article>`);
 case 'team':return paginated(s.team,(e,i)=>record(e.name,`<p>${esc(e.role)} · ${money(e.salary/12)} / month</p><p>Design ${e.design} · Art ${e.art} · Code ${e.code} · Research ${e.research}</p><p>Fatigue ${Math.round(e.fatigue)} · Morale ${Math.round(e.morale)}</p>${btn('Schedule vacation','vacation',i)}`));
 case 'applicants':return applicantComparison(s.applicants);
  case 'contracts':return contractComparison(s.contract_offers);
 case 'research':return paginated(state.research,(r,i)=>record(r.name,`<p>${esc(r.effect)} · ${money(r.cost)}</p><p>Prerequisites: ${esc(r.prereq.join(', ')||'none')}</p>${s.completed_research.includes(r.key)?'<span class="green">Completed</span>':btn('Queue research','research',i)}`));
 case 'loans':return paginated(state.loans,(l,i)=>record(l.name,`<p>${money(l.amount)} · ${esc(l.description)}</p>${btn('Take loan','loan',i)}`));
 case 'catalogue':return releaseRows(s.catalog);
 case 'competitors':return paginated(s.competitors,c=>record(c.name,`<p>${c.in_development.length} projects in development · ${esc(c.tier)} · ${number(c.fanbase)} fans</p>${bars(c.recent_releases.map(g=>({label:g.title,value:g.units_sold,detail:`${number(g.weekly_units)} units this week · ${g.quality}/100` })))}`));
 case 'decision':return state.decision?`<p>Time is held until this decision is resolved.</p><h3>${esc(state.decision.title)}</h3>${state.decision.options.map((o,i)=>record(o.name,`<p>${esc(o.effect)}</p>${btn('Choose','decision',i,true)}`)).join('')}`:'<p>No outstanding decision.</p>';
 case 'settings':return `<p>Keyboard and mouse are both supported. Time pauses while a popup is open and resumes at the previous speed when it closes.</p><div class="row"><span>Pages</span><span>H / G / T / B / S</span></div><div class="row"><span>Pause / speed</span><span>Space / ← → / &lt; &gt;</span></div><div class="row"><span>Ideas / jobs / research</span><span>N / J / U</span></div><div class="row"><span>Move / activate</span><span>↑ ↓ / Enter</span></div><div class="row"><span>Close popup / back</span><span>Esc / Backspace</span></div><div class="row"><span>Save</span><span>Ctrl+S</span></div><p>Inside forms, arrows change the focused option. Tab moves between controls. Q opens this menu; close the browser after saving.</p><div class="actions">${btn('Save studio','save',0,true)}</div>`;
 case 'confirm':return `<p>${esc(pending?.description)}</p><p>This changes studio finances. Continue?</p>${btn('Confirm','confirm',0,true)}`;
 default:return '';
 }
}
function modalCount(){const s=state.studio,p=s.current_project;return ({ideas:s.idea_shelf,experiments:state.experiments,presentation:p?.gdd.presentation_options||[],plan:Object.keys(state.options),findings:[...(p?.gdd.findings||[]),...(p?.gdd.history||[])],activity:state.logs,team:s.team,applicants:s.applicants,contracts:s.contract_offers,research:state.research,loans:state.loans,catalogue:s.catalog,competitors:s.competitors}[modal]||[]).length;}
function drawModal(){const total=modal==='plan'?Math.max(1,Math.ceil(modalCount()/4)):1;modalPage=Math.min(modalPage,total-1);const scroll=dialog.querySelector('.dialog-body')?.scrollTop||0;dialog.dataset.modal=modal;dialog.innerHTML=`<div class="dialog-header"><h2 id="dialog-title">${esc(titles[modal]||({charts:'Weekly sales chart',ledger:'Financial ledger'}[modal]))}</h2><button data-close aria-label="Close popup">[Esc] Close</button></div><div class="dialog-body" tabindex="0" aria-label="${esc(titles[modal]||modal)} content">${modalBody()}${total>1?`<div class="pager"><button data-turn="-1" ${modalPage===0?'disabled':''}>Previous</button><span>${modalPage+1} / ${total}</span><button data-turn="1" ${modalPage===total-1?'disabled':''}>Next</button></div>`:''}</div>`;dialog.querySelector('.dialog-body').scrollTop=scroll;}
async function showModal(name){if(busy)return;const wasOpen=dialog.open;if(!wasOpen)returnFocus=document.activeElement;modal=name;modalPage=0;if(!wasOpen){if(!await act('overlay',0,{open:true})){modal=null;return;}}drawModal();if(!dialog.open)dialog.showModal();dialog.querySelector('.dialog-body button, select')?.focus();}
async function closeModal(){if(busy)return;dialog.close();modal=null;pending=null;await act('overlay',0,{open:false});if(returnFocus?.isConnected)returnFocus.focus();else app.querySelector('nav button.active')?.focus();}
let pending=null;
async function actionClick(action,index){
 if(action==='confirm'){const task=pending;if(!task)return;pending=null;if(await act(task.action,task.index)){await closeModal();}return;}
 if(['hire','loan','commit'].includes(action)){pending={action,index,description:action==='hire'?`Hire ${state.studio.applicants[index].name} for ${money(state.studio.applicants[index].salary/12)} per month, plus hiring costs.`:action==='loan'?`Borrow ${money(state.loans[index].amount)}. ${state.loans[index].description}.`:'Commit this design and pay production setup costs.'};await showModal('confirm');return;}
 if(action==='slower'||action==='faster'){await act('speed',Math.max(0,Math.min(3,state.clock.speed+(action==='faster'?1:-1))));return;}
 if(await act(action,index)){if(['idea','experiment','shelve','decision','release'].includes(action)){page='Projects';if(dialog.open)await closeModal();render(true);}else if(action==='design'){page='Projects';render(true);if(state.studio.current_project?.stage==='design')await showModal('plan');}else if(dialog.open)drawModal();}
}
document.addEventListener('click',e=>{const b=e.target.closest('button');if(!b||busy)return;if(b.hasAttribute('data-close'))closeModal();else if(b.dataset.turn){modalPage+=Number(b.dataset.turn);drawModal();dialog.querySelector('.dialog-body button,select')?.focus();}else if(b.dataset.page){page=b.dataset.page;render(true);}else if(b.dataset.open)showModal(b.dataset.open);else if(b.dataset.action)actionClick(b.dataset.action,Number(b.dataset.index||0));});
dialog.addEventListener('cancel',e=>{e.preventDefault();closeModal();});
dialog.addEventListener('change',async e=>{if(e.target.dataset.field){const field=e.target.dataset.field;await act('plan',Number(e.target.value),{field});drawModal();dialog.querySelector(`[data-field="${field}"]`)?.focus();}});
document.addEventListener('keydown',e=>{
 const editing=e.target.matches('input,select,textarea,option')||!!e.target.closest('select');
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();if(state?.started)act('save');return;}
 if(editing)return;
 if(e.ctrlKey||e.metaKey||e.altKey)return;
 if(e.key==='Escape'||e.key==='Backspace'){e.preventDefault();if(dialog.open)closeModal();else if(e.key==='Escape')showModal('settings');else{page='Studio';render(true);}return;}
 if(busy)return;
 if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const root=dialog.open?dialog:app;const buttons=[...root.querySelectorAll('button:not(:disabled),select')];const index=buttons.indexOf(document.activeElement);buttons[(index+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();return;}
 if(dialog.open){if(e.key.toLowerCase()==='t'&&modal==='plan')showModal('presentation');return;}
 if(!state?.started){if(e.key==='Enter'&&!e.target.matches('button')&&state){e.preventDefault();act('new');}return;}
 if(e.key===' '){e.preventDefault();act('pause');return;}
 if(['ArrowLeft','ArrowRight','<','>'].includes(e.key)){e.preventDefault();actionClick(['ArrowLeft','<'].includes(e.key)?'slower':'faster',0);return;}
 const key=e.key.toLowerCase();
 if(key==='t'&&page==='Projects'&&state.studio.current_project?.stage==='design'){showModal('presentation');return;}
 const pages={h:'Studio',g:'Projects',t:'People',b:'Business',s:'Market'};
 if(pages[key]){page=pages[key];render(true);return;}
 const popups={n:'ideas',j:'contracts',u:'research',p:'catalogue',f:'loans',q:'settings'};
 if(popups[key]){showModal(popups[key]);return;}
 if(key==='e'&&(page==='People'||page==='Studio'))showModal('applicants');
 if(key==='e'&&page==='Projects'&&state.studio.current_project?.stage==='concept')actionClick('design',0);
 if(key==='r'&&page==='Projects'&&state.studio.current_project?.ready_for_release)actionClick('release',0);
 if(e.key==='Enter'&&!e.target.matches('button')){e.preventDefault();if(page==='Projects')showModal(state.studio.current_project?.stage==='concept'?'experiments':'plan');else if(page==='People')showModal('team');else if(page==='Market')showModal('catalogue');}
});
async function poll(){if(busy||document.hidden)return;try{const response=await fetch('/api/state');if(!response.ok)throw Error('Disconnected');const next=await response.json();if(busy)return;state=next;connected=true;render();if(state.decision&&!dialog.open){const p=state.studio.current_project;const key=p.title+':'+p.pending_decision;if(key!==shownDecision){shownDecision=key;await showModal('decision');}}else if(!state.decision){shownDecision='';}}catch{connected=false;if(state?.started)updateClock();}}
poll();setInterval(poll,250);
