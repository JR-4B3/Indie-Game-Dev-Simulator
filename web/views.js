'use strict';
// Browser-only workspaces. Charts use the same saved simulation data as the TUI.
const chartColors=['#89b4fa','#83f59d','#f9e86f','#cba6f7','#f38ba8','#94e2d5'];
const number=n=>Math.round(n||0).toLocaleString();
const sum=(items,key)=>items.reduce((total,item)=>total+(Number(item[key])||0),0);
const empty=text=>`<div class="empty-state">${esc(text)}</div>`;
const section=(title,body,control='')=>`<section class="view-section"><div class="section-line"><h2>${esc(title)}</h2>${control}</div>${body}</section>`;
function bars(items,{format=number,max=0}={}){
 if(!items.length)return empty('No data yet. Results will appear as the simulation runs.');
 const ceiling=Math.max(1,max,...items.map(x=>x.value));
 return `<div class="bar-chart">${items.map((x,i)=>`<div class="chart-row"><div class="chart-label"><span title="${esc(x.label)}">${esc(x.label)}</span><strong>${esc(format(x.value))}</strong></div><svg viewBox="0 0 500 10" preserveAspectRatio="none" role="img" aria-label="${esc(x.label)}: ${esc(format(x.value))}"><rect width="500" height="10" fill="#33364f"/><rect width="${Math.max(0,x.value)/ceiling*500}" height="10" fill="${chartColors[i%chartColors.length]}"/></svg>${x.detail?`<small>${esc(x.detail)}</small>`:''}</div>`).join('')}</div>`;
}
function donut(items,label){
 const positive=items.filter(x=>x.value>0),total=sum(positive,'value');
 if(!total)return empty(`No ${label.toLowerCase()} yet.`);
 let offset=0;
 const rings=positive.map((x,i)=>{const percent=x.value/total*100;const ring=`<circle cx="60" cy="60" r="44" fill="none" stroke="${chartColors[i%chartColors.length]}" stroke-width="16" pathLength="100" stroke-dasharray="${percent} ${100-percent}" stroke-dashoffset="${-offset}" transform="rotate(-90 60 60)"/>`;offset+=percent;return ring;}).join('');
 return `<div class="donut-chart"><svg viewBox="0 0 120 120" role="img" aria-label="${esc(label)}"><title>${esc(positive.map(x=>`${x.label}: ${Math.round(x.value/total*100)}%`).join(', '))}</title>${rings}<text x="60" y="64" text-anchor="middle" fill="#cdd6f4" font-size="14">100%</text></svg><div class="chart-legend">${positive.map((x,i)=>`<div><svg viewBox="0 0 10 10" aria-hidden="true"><rect width="10" height="10" fill="${chartColors[i%chartColors.length]}"/></svg><span>${esc(x.label)}</span><strong>${Math.round(x.value/total*100)}%</strong></div>`).join('')}</div></div>`;
}
function financeTrend(ledger){
 if(!ledger.length)return empty('Your first closed month will start the revenue and expense history.');
 const rows=[...ledger].sort((a,b)=>a.month.localeCompare(b.month)).slice(-12),maximum=Math.max(1,...rows.flatMap(x=>[x.revenue,x.expenses]));
 const path=key=>rows.map((r,i)=>`${i?'L':'M'} ${30+i*540/Math.max(1,rows.length-1)} ${160-r[key]/maximum*140}`).join(' ');
 return `<figure class="trend"><figcaption><span class="green">Revenue</span> / <span class="danger">Expenses</span> · monthly USD</figcaption><svg viewBox="0 0 600 190" role="img" aria-label="Monthly revenue and expenses"><title>${esc(rows.map(r=>`${r.month}: revenue ${money(r.revenue)}, expenses ${money(r.expenses)}`).join('; '))}</title><path d="M30 20V160H570" fill="none" stroke="#62658a"/><path d="${path('revenue')}" fill="none" stroke="#83f59d" stroke-width="3"/><path d="${path('expenses')}" fill="none" stroke="#f38ba8" stroke-width="3"/>${rows.map((r,i)=>`<circle cx="${30+i*540/Math.max(1,rows.length-1)}" cy="${160-r.revenue/maximum*140}" r="3" fill="#83f59d"/><circle cx="${30+i*540/Math.max(1,rows.length-1)}" cy="${160-r.expenses/maximum*140}" r="3" fill="#f38ba8"/>`).join('')}<text x="30" y="183" fill="#a6adc8" font-size="12">${esc(rows[0].month)}</text><text x="570" y="183" text-anchor="end" fill="#a6adc8" font-size="12">${esc(rows.at(-1).month)}</text><text x="35" y="18" fill="#a6adc8" font-size="12">${esc(money(maximum))}</text></svg></figure>`;
}
function skillBars(person){
 const skills=['design','art','code','research'];
 return `<div class="skill-bars">${skills.map((skill,index)=>`<div class="skill-row ${person[skill]===Math.max(...skills.map(k=>person[k]))?'strongest':''}"><span>${skill}</span><svg viewBox="0 0 100 7" preserveAspectRatio="none"><rect width="100" height="7" fill="#33364f"/><rect width="${person[skill]}" height="7" fill="${chartColors[index]}"/></svg><strong>${person[skill]}</strong></div>`).join('')}</div>`;
}
function projectBrief(p){
 if(!p)return `<div class="project-brief empty-project"><span class="brief-kicker">No original production</span><h3>Pick an idea worth testing</h3><p>Ideas become findings. Findings become a production plan.</p>${open('[N] Browse ideas','ideas',true)}</div>`;
 const progress=p.stage==='testing'?p.bug_progress:p.progress;
 const eta=Math.max(1,Math.round(p.remaining_work/Math.max(1,p.weekly_output)));
 const control=state.decision?open('Decision required','decision',true):p.stage==='concept'?open('[Enter] Experiment','experiments',true):p.stage==='design'?open('[Enter] Review plan','plan',true):p.ready_for_release?btn('[R] Release','release',0,true):open('History & findings','findings');
 const stages=['concept','design','development','testing','gold'];
 return `<div class="project-brief"><span class="brief-kicker">${esc(p.stage)} · ${esc(p.phase)}</span><h3>${esc(p.title)}</h3><p>${esc(p.active_experiment?`${p.active_experiment.replaceAll('_',' ')} · ${p.experiment_days_left} workdays left`:p.gdd.uncertainty||`${p.scope} / ${p.channel} / ${money(p.price)}`)}</p><div class="stage-rail">${stages.map((stage,index)=>`<span class="${index<stages.indexOf(p.stage)?'done':index===stages.indexOf(p.stage)?'current':''}">${stage==='gold'?'release':stage}</span>`).join('')}</div><div class="brief-progress"><div><span>${p.stage==='testing'?'Defect clearance':'Production'}</span><strong>${Math.round(progress*100)}%</strong></div><progress value="${progress}" max="1"></progress></div><div class="brief-grid"><span>Week <b>${p.weeks}</b>${p.planned_weeks?` / ${p.planned_weeks}`:''}</span><span>ETA <b>~${eta}w</b></span><span>Hype <b>${number(p.hype)}</b></span><span>Defects <b class="${p.known_defects?'danger':'green'}">${number(p.known_defects)}</b></span><span>Cost <b>${money((p.production_cost||0)+(p.labor_cost||0)+(p.marketing_cost||0))}</b></span><span>Output <b>${state.projected_output.toFixed(1)}/wk</b></span></div><div class="actions">${control}${p.stage==='concept'?btn('[E] Design','design'):''}${p.stage==='design'?open('[T] Presentation','presentation'):''}${p?open('Findings','findings'):''}${manageButton(-1,'Marketing')}</div></div>`;
}
function projectsView(){
 const s=state.studio,p=s.current_project,findings=p?.gdd.findings||[];
 const evidence=findings.slice(-4).reverse().map((finding,index)=>`<article class="evidence-item"><span>F${findings.length-index}</span><p>${esc(finding.text)}</p></article>`).join('')||empty('Experiments turn claims into evidence.');
 return heading('Projects','Production pipeline: pitch → proof → production')+`<div class="project-workspace">
  ${section('Current production',projectBrief(p))}
  ${section('Idea pipeline',`<div class="idea-strip"><span>Ready to explore</span><strong>${s.idea_shelf.length}</strong></div><div class="idea-list">${s.idea_shelf.slice(0,3).map(x=>`<article><h3>${esc(x.title)}</h3><p>${esc(x.fantasy)}</p></article>`).join('')||empty('The team will generate pitches as time runs.')}</div>`,open('[N] Idea shelf','ideas'))}
  ${section('Design evidence',`<div class="evidence-list">${evidence}</div><div class="evidence-footer"><span>${findings.length} finding${findings.length===1?'':'s'} recorded</span>${p?.stage==='concept'?btn('Shelve concept','shelve'):''}</div>`,open('All findings','findings'))}
 </div>`;
}
function employeeCard(e,index){
 const status=availability(e);
 return `<article class="person-card"><div class="person-top"><div><h3>${esc(e.name)}</h3><span>${esc(e.role)} · ${money(e.salary/12)}/mo</span></div><strong class="${status==='Available'?'green':e.burnout_weeks_left?'danger':'warning'}">${esc(status)}</strong></div>${skillBars(e)}<div class="person-condition"><span>Fatigue <b class="${e.fatigue>=70?'danger':e.fatigue>=35?'warning':'green'}">${Math.round(e.fatigue)}</b></span><span>Morale <b class="${e.morale<40?'danger':e.morale<70?'warning':'green'}">${Math.round(e.morale)}</b></span><span>Career <b>L${e.career_level}</b></span><span>Trait <b>${esc(e.trait)}</b></span></div><div class="person-actions">${btn('Vacation','vacation',index)}</div></article>`;
}
function peopleView(){
 const s=state.studio,available=s.team.filter(e=>availability(e)==='Available').length;
 const limit=innerWidth<701?1:innerHeight<701?(innerWidth<1101?2:4):innerWidth<1101?4:6;
 return heading('People','Roster, skills, condition and capacity')+`<div class="people-summary"><span>${s.team.length} people</span><span class="green">${available} available</span><span>${money(sum(s.team,'salary')/12)}/month payroll</span><span>${state.projected_output.toFixed(1)} project output/week</span>${open('[E] Hire applicants','applicants',true)}</div><div class="people-workspace"><div class="employee-grid">${s.team.slice(0,limit).map(employeeCard).join('')}</div><aside class="people-side">${section('Skill coverage',bars(['design','art','code','research'].map(key=>({label:key,value:sum(s.team,key)})))+`<p class="view-note">Combined points; fatigue and other work reduce output.</p>`,open(`All ${s.team.length} people`,'team'))}${section('Capacity commitments',donut(Object.entries(state.allocations).filter(([,value])=>value>0).map(([label,value])=>({label,value})),'Allocated capacity'))}</aside></div>`;
}
function businessView(){
 const s=state.studio;
 const activeLoan=s.loans.reduce((total,loan)=>total+loan.balance,0);
 return heading('Business','Cash flow, commitments and capability investment')+`<div class="business-command"><div class="business-financial"><div><span>Cash</span><strong class="${s.cash<0?'danger':'green'}">${money(s.cash)}</strong></div><div><span>Burn</span><strong class="danger">${money(state.monthly_cost)}</strong></div><div><span>Runway</span><strong class="${state.runway<4?'danger':state.runway<8?'warning':'green'}">${state.runway.toFixed(1)} mo</strong></div><div><span>Debt</span><strong class="${activeLoan?'danger':''}">${money(activeLoan)}</strong></div></div><div class="business-actions">${open('[F] Financing','loans')}${open('[J] Contract board','contracts',true)}${open('[U] Research & upgrades','research')}</div></div><div class="business-workspace">
  ${section('Cash flow',financeTrend(s.ledger),open('Ledger','ledger'))}
  ${section('Monthly cost mix',donut(Object.entries(state.cost_breakdown).map(([label,value])=>({label,value})),'Fixed monthly costs'))}
  ${section('Client delivery',`<div class="commitment-status"><span class="status-pill ${s.contract?'green':'muted'}">${s.contract?'ACTIVE':'IDLE'}</span><h3>${esc(s.contract?.title||'No active contract')}</h3></div>${s.contract?bars([{label:'Delivery progress',value:s.contract.work_done}],{max:s.contract.required_work})+`<div class="commitment-grid"><span>Due <b>${s.contract.weeks_left}w</b></span><span>Payout <b class="green">${money(s.contract.pay)}</b></span><span>CTrust <b>${s.contractor_reputation.toFixed(1)}</b></span></div>`:`<p class="view-note">${s.contract_offers.length} offers available. Contractor trust unlocks better-paying work.</p>`}`)}
  ${section('Research & upgrades',`<div class="commitment-status"><span class="status-pill ${s.active_research?'green':'muted'}">${s.active_research?'ACTIVE':'IDLE'}</span><h3>${esc(s.active_research?.name||'No active research')}</h3></div>${s.active_research?bars([{label:'Research progress',value:s.active_research.progress*100}],{max:100,format:x=>Math.round(x)+'%'})+`<p class="view-note">${esc(s.active_research.effect)}</p>`:`<p class="view-note">${s.completed_research.length} completed · ${s.research_queue.length} queued · ${Math.round((state.allocations.research||0)*100)}% capacity.</p>`}`)}
 </div>`;
}
function marketView(){
 const s=state.studio,chart=state.market_chart;
 const byStudio={};for(const entry of chart)byStudio[entry.studio_name]=(byStudio[entry.studio_name]||0)+entry.weekly_units;
 const studios=Object.entries(byStudio).sort((a,b)=>b[1]-a[1]);
 const share=studios.slice(0,4).map(([label,value])=>({label,value}));
 if(studios.length>4)share.push({label:'Other chart studios',value:studios.slice(4).reduce((n,x)=>n+x[1],0)});
 const best=[...s.catalog].sort((a,b)=>b.weekly_units-a.weekly_units)[0];
 return heading('Market','Chart position, audience and portfolio performance')+`<div class="market-command"><span><b>${number(s.followers)}</b> followers</span><span><b class="blue">${number(sum(s.catalog,'weekly_units'))}</b> units/week</span><span><b>${number(sum(s.catalog,'units_sold'))}</b> lifetime units</span><span><b>${number(sum(s.catalog,'monthly_players'))}</b> monthly players</span>${best?`<span class="best-seller">Top title: <b>${esc(best.title)}</b></span>`:''}</div><div class="market-workspace">
   ${section('Weekly sales chart',compactChart(chart))}
  <aside class="market-side">${innerWidth>700?section('Studio sales share',donut(share,'Weekly chart sales share'),open('Studios','competitors')):''}${section('Portfolio',s.catalog.length?releaseRows(s.catalog,innerHeight<701?1:2):empty('Release a game to build sales history and audience.'),open('[P] Releases','catalogue'))}</aside>
 </div>`;
}
function analysisBody(name){
 const s=state.studio;
 if(name==='charts')return compactChart(state.market_chart);
 if(name==='ledger')return financeTrend(s.ledger)+[...s.ledger].sort((a,b)=>b.month.localeCompare(a.month)).map(r=>record(r.month,`<div class="ledger-row"><span class="green">In ${money(r.revenue)}</span><span class="danger">Out ${money(r.expenses)}</span><strong>Net ${money(r.net)}</strong></div>`)).join('');
 return '';
}
window.addEventListener('resize',()=>{if(state?.started)render(true);});
