'use strict';
// Browser-only views. Charts use the same saved simulation data as the TUI.
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
function projectsView(){
 const s=state.studio,p=s.current_project;
 const findings=p?.gdd.findings||[];
 return heading('Projects','The creative brief → evidence → production')+`<div class="project-board">
 ${section('Production workspace',`<div class="project-hero">${projectSummary()}</div><div class="project-facts">${metric('Stage',p?.stage||'No project')}${metric('Findings',findings.length)}${metric('Catalogue',s.catalog.length)}</div>`)}
 ${section('Idea shelf',`<div class="idea-preview">${s.idea_shelf.slice(0,3).map(x=>`<article><h3>${esc(x.title)}</h3><p>${esc(x.fantasy)}</p></article>`).join('')||empty('New pitches arrive as time passes.')}</div>`,open('[N] Browse ideas','ideas'))}
 ${section('Design evidence',`<div class="evidence">${findings.slice(-3).reverse().map(f=>`<blockquote>${esc(f.text)}</blockquote>`).join('')||empty('Run a concept experiment to test the central idea before investing in production.')}</div><div class="actions">${open('All findings','findings')}${p?.stage==='concept'?btn('Shelve concept','shelve'):''}${state.decision?open('Decision required','decision',true):''}</div>`)}
 </div>`;
}
let rosterPage=0;
function peopleView(){
 const s=state.studio,size=innerWidth<701?1:innerHeight<701?2:4,total=Math.max(1,Math.ceil(s.team.length/size));
 rosterPage=Math.min(rosterPage,total-1);
 const employees=s.team.slice(rosterPage*size,(rosterPage+1)*size);
 return heading('People','Individual strengths, availability and wellbeing')+`<div class="people-summary">${metric('People',s.team.length)}${metric('Available',s.team.filter(e=>availability(e)==='Available').length,'team-avail')}${metric('Monthly payroll',money(sum(s.team,'salary')/12),'burn-expense')}<div class="actions">${open('[E] Hire','applicants',true)}</div></div><div class="people-board">
 <section class="roster"><div class="section-line"><h2>Team roster</h2><div class="roster-controls"><button data-roster="-1" ${rosterPage===0?'disabled':''} aria-label="Previous people">←</button><span>${rosterPage+1} / ${total}</span><button data-roster="1" ${rosterPage===total-1?'disabled':''} aria-label="Next people">→</button></div></div><div class="employee-grid">${employees.map((e,i)=>`<article class="employee-card"><div class="employee-heading"><h3>${esc(e.name)}</h3><span class="${e.burnout_weeks_left?'danger':'green'}">${esc(availability(e))}</span></div><div class="employee-role">${esc(e.role)} · ${money(e.salary/12)}/mo</div>${bars(['design','art','code','research'].map(key=>({label:key,value:e[key]})),{max:100})}<div class="condition-line"><span class="${e.fatigue>=70?'danger':e.fatigue>=35?'warning':'green'}">Fatigue ${Math.round(e.fatigue)}</span><span class="${e.morale<40?'danger':e.morale<70?'warning':'green'}">Morale ${Math.round(e.morale)}</span></div>${btn('Vacation','vacation',rosterPage*size+i)}</article>`).join('')}</div></section>
 ${section('Team skill coverage',bars(['design','art','code','research'].map(key=>({label:key,value:sum(s.team,key)})))+`<p class="view-note">Combined skill points, not available output. Fatigue, leave and shared commitments affect delivery.</p>`,open('All people','team'))}
 </div>`;
}
function businessView(){
 const s=state.studio;
 return heading('Business','Cash flow, cost structure and commitments')+`<div class="business-summary">${metric('Cash',money(s.cash),s.cash<0?'cash-danger':'cash-good')}${metric('Monthly burn',money(state.monthly_cost),'burn-expense')}${metric('Runway',state.runway.toFixed(1)+' mo','runway-good')}${metric('Debt balance',money(sum(s.loans,'balance')),'burn-expense')}</div><div class="business-board">
 ${section('Cash flow history',financeTrend(s.ledger),open('Ledger','ledger'))}
 ${section('Fixed monthly costs',donut(Object.entries(state.cost_breakdown).map(([label,value])=>({label,value})),'Fixed monthly costs'),open('[F] Financing','loans'))}
 ${section('Client commitments',`<h3>${esc(s.contract?.title||'No active contract')}</h3>${s.contract?bars([{label:'Work completed',value:s.contract.work_done}],{max:s.contract.required_work}):`<p class="view-note">${s.contract_offers.length} offers available to fund your next game.</p>`}<div class="actions">${open('[J] Contract board','contracts',true)}</div>`)}
 ${section('Capacity allocation',donut(Object.entries(state.allocations).filter(([,v])=>v>0).map(([label,value])=>({label,value})),'Allocated capacity'),open('[U] Research','research'))}
 </div>`;
}
function marketView(){
 const s=state.studio,chart=state.market_chart;
 const byStudio={};for(const entry of chart)byStudio[entry.studio_name]=(byStudio[entry.studio_name]||0)+entry.weekly_units;
 const studios=Object.entries(byStudio).sort((a,b)=>b[1]-a[1]);
 const share=studios.slice(0,4).map(([label,value])=>({label,value}));
 if(studios.length>4)share.push({label:'Other chart studios',value:studios.slice(4).reduce((n,x)=>n+x[1],0)});
 const limit=innerHeight<701?3:5;
 return heading('Market','Weekly sales, competing studios and your audience')+`<div class="market-summary">${metric('Followers',number(s.followers),'audience')}${metric('Your units sold',number(sum(s.catalog,'units_sold')))}${metric('Monthly players',number(sum(s.catalog,'monthly_players')))}${metric('Released games',s.catalog.length)}</div><div class="market-board">
 ${section('Weekly sales chart',bars(chart.slice(0,limit).map((g,i)=>({label:`${i+1}. ${g.title}`,value:g.weekly_units,detail:`${g.studio_name} · ${g.genre} · ${g.score}/100` })))+`<p class="view-note">Units this week · same chart as the terminal edition</p>`,open('Full chart','charts'))}
 ${section('Chart sales share',donut(share,'Weekly chart sales share')+`<p class="view-note">Share of the top ${chart.length} chart entries, not the entire market.</p>`,open('Studios','competitors'))}
 ${section('Your catalogue',s.catalog.length?bars([...s.catalog].sort((a,b)=>b.units_sold-a.units_sold).slice(0,3).map(g=>({label:g.title,value:g.units_sold}))):empty('Your first release will appear here. Build an audience while you develop.'),open('[P] Manage releases','catalogue'))}
 </div>`;
}
function analysisBody(name){
 const s=state.studio;
 if(name==='charts')return bars(state.market_chart.map(g=>({label:g.title,value:g.weekly_units,detail:`${g.studio_name} · ${g.genre} · ${g.score}/100`})));
 if(name==='ledger')return financeTrend(s.ledger)+[...s.ledger].sort((a,b)=>b.month.localeCompare(a.month)).map(r=>record(r.month,`<div class="ledger-row"><span class="green">In ${money(r.revenue)}</span><span class="danger">Out ${money(r.expenses)}</span><strong>Net ${money(r.net)}</strong></div>`)).join('');
 return '';
}
document.addEventListener('click',event=>{
 const control=event.target.closest('[data-roster]');
 if(control&&!busy){rosterPage=Math.max(0,rosterPage+Number(control.dataset.roster));render(true);}
});
window.addEventListener('resize',()=>{if(state?.started)render(true);});
