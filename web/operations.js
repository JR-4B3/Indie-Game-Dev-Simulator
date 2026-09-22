'use strict';
// Compact operational displays. Values are saved simulation results, not estimates.
let managedRelease=null;
let studioReleaseIndex=null;
// The title registry is initialized by app.js before any interaction.
const manageButton=(index,label='Operations')=>`<button data-release="${index}">${esc(label)}</button>`;
function compactChart(entries){
 if(!entries.length)return empty('No chart entries yet. Sales will appear after releases.');
 const peak=Math.max(1,...entries.map(g=>g.weekly_units));
 return `<div class="compact-chart"><div class="chart-columns"><span># / Game · Studio</span><span>Units / week</span></div>${entries.map((g,i)=>`<div class="rank-row"><span class="rank">${i+1}</span><div class="rank-game"><strong title="${esc(g.title)}">${esc(g.title)}</strong><small>${esc(g.studio_name)}</small></div><svg viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true"><rect width="100" height="6" fill="#33364f"/><rect width="${g.weekly_units/peak*100}" height="6" fill="${g.game_id?'#83f59d':'#89b4fa'}"/></svg><strong>${number(g.weekly_units)}</strong></div>`).join('')}</div>`;
}
function releaseRows(games,limit=games.length){
 if(!games.length)return empty('No releases yet. Sales and maintenance needs appear here after launch.');
 return `<div class="release-list">${games.slice(0,limit).map(g=>`<article class="release-row"><div><strong>${esc(g.title)}</strong><small>${number(g.weekly_units)} units/wk · ${number(g.units_sold)} lifetime · Hype ${number(g.hype)}</small><small>${money(g.net_revenue)} revenue · <span class="${g.profit<0?'danger':'green'}">${money(g.profit)} profit</span></small><small class="${g.known_bugs>0?'warning':'muted'}">${number(g.known_bugs)} known bugs · ${esc(g.support_level)} support · ${number(g.monthly_players)} players</small></div>${manageButton(state.studio.catalog.indexOf(g))}</article>`).join('')}</div>`;
}
function projectControl(p){
 return state.decision?open('Decision required','decision',true):p?.stage==='concept'?open('[Enter] Experiments','experiments'):p?.stage==='design'?open('[Enter] Review plan','plan'):p?.ready_for_release?btn('[R] Release','release',0,true):p?open('Details','findings'):open('[N] Explore ideas','ideas',true);
}
function releaseCommand(game,index){
 const updateForGame=state.studio.active_update?.game_id===game.game_id?state.studio.active_update:state.studio.update_queue.find(x=>x.game_id===game.game_id);
 const updateProgress=updateForGame?(updateForGame.work_done+updateForGame.bugs_fixed)/Math.max(1,updateForGame.required_work+updateForGame.bugs_found):0;
 const updateNote=updateForGame?`${updateForGame===state.studio.active_update?'Active':'Queued'} ${updateForGame.size} · ${Math.round(updateProgress*100)}%`:'No update committed';
 return `<div class="command-heading"><div><span class="command-kind">Live game · v${esc(game.version)}</span><h3>${esc(game.title)}</h3></div><button data-original-game>Original game</button></div><div class="live-command-metrics"><span>Sales/wk <b class="blue">${number(game.weekly_units)}</b></span><span>Hype <b>${number(game.hype)}</b></span><span>Bugs <b class="${game.known_bugs?'warning':'green'}">${number(game.known_bugs)}</b></span><span>Players <b>${number(game.monthly_players)}</b></span><span>Profit <b class="${game.profit<0?'danger':'green'}">${money(game.profit)}</b></span></div><div class="live-update-plan"><label>Update size${optionSelect('studio-update-size',state.update_sizes,game.update_size,x=>`${x.name} · ${money(x.cost)}`)}</label><label>Focus${optionSelect('studio-update-focus',state.update_focuses,game.update_focus,x=>x.name)}</label><button class="primary" data-studio-update="${index}">Queue update</button></div><div class="command-actions"><span class="update-note">${esc(updateNote)}</span>${btn('Support: '+game.support_level,'support',index)}${manageButton(index,'Marketing · community · details')}</div>`;
}
function studioCommand(){
 const s=state.studio,p=s.current_project,c=s.contract;
 let gameBody;
 if(studioReleaseIndex!==null&&s.catalog[studioReleaseIndex])gameBody=releaseCommand(s.catalog[studioReleaseIndex],studioReleaseIndex);
 else if(!p)gameBody=`<div class="command-heading"><div><span class="command-kind">Original game</span><h3>No game in progress</h3></div>${projectControl(p)}</div><p>${s.idea_shelf.length} ideas on the shelf. Explore a concept before committing production resources.</p><div class="command-facts"><span>Released <b>${s.catalog.length}</b></span><span>Audience <b>${number(s.followers)}</b></span></div>`;
 else{
  const progress=p.stage==='testing'?p.bug_progress:p.progress,eta=Math.max(1,Math.round(p.remaining_work/Math.max(1,p.weekly_output)));
  gameBody=`<div class="command-heading"><div><span class="command-kind">Original game · ${esc(p.stage)}</span><h3>${esc(p.title)}</h3></div>${projectControl(p)}</div><div class="command-progress"><div><span>${esc(p.phase)}</span><strong>${Math.round(progress*100)}%</strong></div><progress value="${progress}" max="1"></progress></div><div class="command-facts"><span>Week <b>${p.weeks}</b>${p.planned_weeks?` / ${p.planned_weeks} planned`:''}</span><span>ETA <b>~${eta}w</b></span><span>Scope <b>${esc(p.scope)}</b></span><span>Hype <b>${number(p.hype)}</b></span><span>Known defects <b class="${p.known_defects?'warning':''}">${number(p.known_defects)}</b></span><span>Cost <b>${money((p.production_cost||0)+(p.labor_cost||0)+(p.marketing_cost||0))}</b></span></div><div class="command-actions">${open('Findings','findings')}${manageButton(-1,'Marketing & community')}</div>`;
 }
 const contractProgress=c?c.work_done/Math.max(1,c.required_work):0;
 const contractBody=c?`<div class="command-heading"><div><span class="command-kind">Client contract</span><h3>${esc(c.title)}</h3></div>${open('[J] Board','contracts')}</div><p>${esc(c.client)} · ${esc(c.focus)} · ${c.weeks_left}w remaining</p><div class="command-progress"><div><span>Delivery</span><strong>${Math.round(contractProgress*100)}%</strong></div><progress value="${contractProgress}" max="1"></progress></div><div class="command-facts"><span>Payout <b class="green">${money(c.pay)}</b></span><span>Work <b>${number(c.work_done)} / ${number(c.required_work)}</b></span><span>Queue <b>${s.contract_queue.length}</b></span></div>`:`<div class="command-heading"><div><span class="command-kind">Client work</span><h3>No active contract</h3></div>${open('[J] Contracts','contracts')}</div><p>${s.contract_offers.length} offers available · ${s.contract_queue.length} queued · contractor trust ${s.contractor_reputation.toFixed(1)}</p>`;
 return `<section class="studio-command ${studioReleaseIndex!==null?'release-context':''}"><div class="section-line"><h2>Studio command</h2><span class="small muted">${Object.entries(state.allocations).filter(([,v])=>v>.001).map(([k,v])=>`${k} ${Math.round(v*100)}%`).join(' · ')||'No committed capacity'}</span></div><div class="command-grid"><article class="command-card game-command">${gameBody}</article><article class="command-card contract-command">${contractBody}</article></div></section>`;
}
function studioTeam(){
 const s=state.studio,available=s.team.filter(e=>availability(e)==='Available').length;
 return `<section class="team-panel"><div class="section-line"><h2>Team condition · ${s.team.length}</h2>${open('Details →','team')}</div><div class="team-quick"><span class="green">${available} available</span><span>${money(sum(s.team,'salary')/12)}/mo</span></div><table><thead><tr><th>Name</th><th>Fatigue</th><th>Morale</th></tr></thead><tbody>${s.team.slice(0,5).map(e=>{const fatigue=e.fatigue>=70?'danger':e.fatigue>=35?'caution':'good',morale=e.morale>=70?'team-status-good':e.morale>=40?'team-status-caution':'team-status-danger';return `<tr><td class="member-name">${esc(e.name)}</td><td><div class="fatigue-wrapper"><progress class="${fatigue}" value="${e.fatigue}" max="100"></progress><span class="fatigue-num fatigue-${fatigue}">${Math.round(e.fatigue)}</span></div></td><td class="${morale}">${Math.round(e.morale)}</td></tr>`;}).join('')}</tbody></table></section>`;
}
function studioReleaseTable(){
 const s=state.studio;
 if(!s.catalog.length)return `<section class="studio-release-table"><div class="section-line"><h2>Released games</h2></div>${empty('No releases yet. Post-launch sales, health and maintenance appear here.')}</section>`;
 return `<section class="studio-release-table"><div class="section-line"><h2>Released games · ${s.catalog.length}</h2><span class="release-totals">Month <b class="green">${money(s.period_revenue)}</b> in / <b class="danger">${money(s.period_expenses)}</b> out · WTD <b>${number(sum(s.catalog,'week_to_date'))}</b></span></div><div class="release-table-wrap"><table><thead><tr><th>Game</th><th>Sales/wk</th><th>Lifetime</th><th>Hype</th><th>Revenue</th><th>Profit</th><th>Bugs</th><th>Players</th><th>Support</th></tr></thead><tbody>${s.catalog.slice(0,6).map((g,i)=>`<tr class="release-select-row ${studioReleaseIndex===i?'selected':''}" data-select-release="${i}" tabindex="0" role="button" aria-label="Open ${esc(g.title)} operations"><td><strong>${esc(g.title)}</strong><small>${esc(g.version)} · ${g.score}/100</small></td><td class="blue">${number(g.weekly_units)}</td><td>${number(g.units_sold)}</td><td class="${g.hype<10?'warning':''}">${number(g.hype)}</td><td class="green">${money(g.net_revenue)}</td><td class="${g.profit<0?'danger':'green'}">${money(g.profit)}</td><td class="${g.known_bugs?'warning':'green'}">${number(g.known_bugs)}</td><td>${number(g.monthly_players)}</td><td>${esc(g.support_level)}</td></tr>`).join('')}</tbody></table></div><p class="release-hint">Select a game to replace Original Game with its live-operations controls.</p></section>`;
}
function studioPulse(){
 const s=state.studio;
 return `<section class="studio-pulse"><div class="section-line"><h2>Market pulse</h2>${open('Full chart','charts')}</div>${compactChart(state.market_chart.slice(0,10))}</section>`;
}
function studioReleases(){
 const s=state.studio;
 return `<section class="studio-releases"><div class="section-line"><h2>Released games</h2>${open('[P] All releases','catalogue')}</div><div class="operating-totals"><span>Month in <b class="green">${money(s.period_revenue)}</b></span><span>Out <b class="danger">${money(s.period_expenses)}</b></span><span>Sales WTD <b>${number(sum(s.catalog,'week_to_date'))}</b></span></div>${releaseRows(s.catalog,innerHeight<701?1:2)}</section>`;
}
function projectTelemetry(){
 const p=state.studio.current_project;
 if(!p)return '';
 return `<div class="project-telemetry"><span>Hype <b>${number(p.hype)}</b></span><span>Known defects <b>${number(p.known_defects)}</b></span><span>Tracked cost <b>${money((p.production_cost||0)+(p.labor_cost||0)+(p.marketing_cost||0))}</b></span><span>Marketing <b>${money(p.marketing_cost)}</b></span>${manageButton(-1,'Marketing & community')}</div>`;
}
function historyChart(values){
 if(!values?.length)return empty('Weekly sales history will build as time passes.');
 const shown=values.slice(-20),peak=Math.max(1,...shown);
 return `<figure class="sales-history"><figcaption>Weekly sales · last ${shown.length} recorded weeks</figcaption><svg viewBox="0 0 600 100" role="img" aria-label="Weekly sales history"><title>${shown.map(number).join(', ')} units</title>${shown.map((v,i)=>`<rect x="${i*600/shown.length}" y="${90-v/peak*80}" width="${Math.max(1,600/shown.length-3)}" height="${v/peak*80}" fill="#89b4fa"/>`).join('')}<path d="M0 90H600" stroke="#62658a"/></svg></figure>`;
}
function optionSelect(name,choices,selected,format){
 return `<select name="${name}">${choices.map((x,i)=>`<option value="${i}" ${x.name===selected?'selected':''}>${esc(format(x))}${x.lock?' — '+esc(x.lock):''}</option>`).join('')}</select>`;
}
function campaignPreview(index){
 const x=state.promotions[index];
 return `${x.effect} · up to +${x.hype} hype · ceiling ${x.ceiling} · ${Math.round(x.team*100)}% team${x.lock?' · '+x.lock:''}`;
}
function operationQueues(gameId){
 const s=state.studio,updates=[...(s.active_update?[s.active_update]:[]),...s.update_queue].filter(x=>x.game_id===gameId);
 const promotions=s.active_promotions.filter(x=>x.game_id===gameId),community=s.active_community_actions.filter(x=>x.game_id===gameId);
 return `<div class="operation-queues"><h3>Commitments</h3>${updates.map(x=>`<p>${x===s.active_update?'Active':'Queued'}: ${esc(x.size)} / ${esc(x.focus)} · v${esc(x.target_version)} · ${Math.round((x.work_done+x.bugs_fixed)/Math.max(1,x.required_work+x.bugs_found)*100)}%</p>`).join('')}${promotions.map(x=>`<p>${x===s.active_promotions[0]?'Active':'Queued'}: ${esc(x.name)} · ${x.weeks_left}w · ${Math.round(x.team_share*100)}% team</p>`).join('')}${community.map(x=>`<p>${esc(x.name)} · ${x.weeks_left}w · ${Math.round(x.team_load*100)}% team</p>`).join('')}${!updates.length&&!promotions.length&&!community.length?'<p>No updates or campaigns committed.</p>':''}</div>`;
}
function managementBody(){
 const s=state.studio,g=managedRelease===-1?s.current_project:s.catalog[managedRelease];
 if(!g)return empty('This project or release is no longer available.');
 const released=managedRelease!==-1,id=released?g.game_id:0;
 return `<div class="management-title"><h3>${esc(g.title)}</h3><span>${released?'v'+esc(g.version)+' · '+esc(g.channel):esc(g.stage)}</span></div>
 <div class="release-metrics">${metric('Hype',number(g.hype))}${metric('Marketing spent',money(g.marketing_cost))}${released?`${metric('Units / week',number(g.weekly_units))}${metric('Sales WTD',number(g.week_to_date))}${metric('Lifetime units',number(g.units_sold))}${metric('Net revenue',money(g.net_revenue))}${metric('Tracked profit',money(g.profit),g.profit<0?'cash-danger':'cash-good')}${metric('Monthly players',number(g.monthly_players))}${metric('User / press',`${number(g.user_rating)} / ${number(g.press_rating)}`)}${metric('Known bugs',number(g.known_bugs),'burn-expense')}${metric('Trust / sentiment',`${number(g.trust)} / ${number(g.sentiment)}`)}${metric('Refunds',number(g.refunded_units))}`:''}</div>
 ${released?historyChart(g.sales_history):''}
 ${released?`<section class="management-section"><h3>Support & pricing</h3><div class="actions">${btn('Support: '+g.support_level,'support',managedRelease)}<button data-operation="price" data-delta="-1">− Price</button><strong>${new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(g.price)}</strong><button data-operation="price" data-delta="1">+ Price</button></div><p>Support consumes shared capacity. Raising prices can cost player trust; frequent patches can cause fatigue.</p><h3>Plan an update</h3><div class="form-grid"><label>Size & upfront cost${optionSelect('update-size',state.update_sizes,g.update_size,x=>`${x.name} · ${money(x.cost)} · ${Math.round(x.team*100)}% team`)}</label><label>Focus${optionSelect('update-focus',state.update_focuses,g.update_focus,x=>x.name)}</label></div><button data-operation="release_update" class="primary">Queue selected update</button></section>`:''}
 <section class="management-section"><h3>Marketing</h3><label>Campaign · cost · duration · reputation required${optionSelect('promotion',state.promotions,null,x=>`${x.name} · ${money(x.cost)} · ${x.weeks}w · rep ${x.rep}`)}</label><p id="promotion-preview">${esc(campaignPreview(0))}</p><p>Hype is not sales. Campaigns share one queue and team capacity; research, funds and reputation gates still apply.</p><button data-operation="marketing" class="primary">Fund campaign</button></section>
 <section class="management-section"><h3>Community</h3><label>Action · cost · duration${optionSelect('community',state.community_actions,null,x=>`${x.name} · ${money(x.cash_cost)} · ${x.duration_weeks}w`)}</label><p>Repeated messaging has diminishing returns. Community work also uses the team's time.</p><button data-operation="community">Start community action</button></section>
 ${operationQueues(id)}`;
}
document.addEventListener('click',async event=>{
 const control=event.target.closest('button');if(!control||busy)return;
 if(control.hasAttribute('data-original-game')){studioReleaseIndex=null;render(true);return;}
 if(control.hasAttribute('data-studio-update')){
  const index=Number(control.dataset.studioUpdate);
  await act('release_update',index,{size:state.update_sizes[Number(document.querySelector('[name="studio-update-size"]').value)].name,focus:state.update_focuses[Number(document.querySelector('[name="studio-update-focus"]').value)].name});
  return;
 }
 if(control.hasAttribute('data-release')){managedRelease=Number(control.dataset.release);titles.management='Game operations';await showModal('management');return;}
 const action=control.dataset.operation;if(!action)return;
 const g=managedRelease===-1?state.studio.current_project:state.studio.catalog[managedRelease];if(!g)return;
 let index=managedRelease,extra={};
 if(action==='release_update'){
  extra={size:state.update_sizes[Number(dialog.querySelector('[name="update-size"]').value)].name,focus:state.update_focuses[Number(dialog.querySelector('[name="update-focus"]').value)].name};
 }else if(action==='price'){extra={delta:Number(control.dataset.delta)};}
 else{index=Number(dialog.querySelector(`[name="${action==='marketing'?'promotion':'community'}"]`).value);extra={game_id:managedRelease===-1?0:g.game_id};}
 if(await act(action,index,extra))drawModal();
});
document.addEventListener('click',event=>{
 const row=event.target.closest('[data-select-release]');
 if(row&&!busy){studioReleaseIndex=Number(row.dataset.selectRelease);render(true);document.querySelector('.game-command')?.focus?.();}
});
document.addEventListener('keydown',event=>{
 const row=event.target.closest('[data-select-release]');
 if(row&&(event.key==='Enter'||event.key===' ')){event.preventDefault();studioReleaseIndex=Number(row.dataset.selectRelease);render(true);}
});
document.addEventListener('change',event=>{
 if(event.target.name==='promotion')document.querySelector('#promotion-preview').textContent=campaignPreview(Number(event.target.value));
});
