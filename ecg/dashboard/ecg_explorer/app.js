const $ = id => document.getElementById(id);
const state = {recording:null, selected:null, start:0, span:5, flags:new Map(), importSeq:0};
const COLORS = {signal:'#243B53', raw:'#526478', grid:'#D6DFE9', text:'#536477'};
const WAVES = {P:'#7C3AED', Q:'#A65A00', R:'#1D4ED8', S:'#007F70', T:'#B42363'};
const finite = x => Number.isFinite(Number(x)) ? Number(x) : null;
const fmt = (x,d=2) => Number.isFinite(x) ? x.toFixed(d) : '—';
const esc = s => String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label = run => run.analysis?.script_version || run.metadata?.script_version || run.label || 'unknown version';
const runId = run => run.metadata?.created_utc || run.importName || 'unspecified recording';
const simulated = run => run.sample || run.metadata?.source==='demo' || run.metadata?.original_source==='demo';
function sample(){
 const fs=250, duration=12, r=[.72,1.55,2.39,3.21,4.04,4.87,5.71,6.54,7.37,8.20,9.03,9.87,10.7];
 const raw={t:[],y:[]},filtered={t:[],y:[]};
 for(let n=0;n<fs*duration;n++){
  const t=n/fs;let wave=0;
  for(const beat of r)for(const [offset,amp,width] of [[-.17,.18,.032],[-.032,-.18,.011],[0,1,.013],[.038,-.27,.012],[.25,.27,.055]])wave+=amp*Math.exp(-.5*((t-beat-offset)/width)**2);
  const noise=.012*Math.sin(n*1.73)+.008*Math.sin(n*2.71);
  raw.t.push(t);raw.y.push(wave+noise+.15*Math.sin(2*Math.PI*.28*t)+.09*Math.sin(2*Math.PI*50*t));filtered.t.push(t);filtered.y.push(wave+noise*.35);
 }
 const beats=r.map((t,i)=>({beat:i+1,p:t-.17,q:t-.032,r:t,s:t+.038,t:t+.25}));
 const rr=beats.slice(1).map((b,i)=>({end:b.r,rr:b.r-beats[i].r,bpm:60/(b.r-beats[i].r),accepted:true}));
 const sorted=rr.map(x=>x.bpm).sort((a,b)=>a-b);
 return {label:'Illustrative example',importName:'Synthetic example',source:'Synthetic example',raw,filtered,beats,rr,sample:true,files:['synthetic'],
 metadata:{source:'demo',units:'arbitrary units',target_fs_hz:fs,timestamp_kind:'synthetic uniform grid'},
 analysis:{median_hr_bpm:(sorted[5]+sorted[6])/2,r_candidates:beats.length,accepted_rr_intervals:rr.length,excluded_rr_intervals:0,polarity_multiplier:1,
 timing:{samples:raw.t.length,measured_average_fs_hz:fs,recorded_span_s:raw.t.at(-1)},warnings:['Synthetic illustration; these markers are constructed, not validated detections.']}};
}
function parseCSV(text, required) {
  const lines=text.replace(/^\uFEFF/,"").trim().split(/\r?\n/).filter(x=>x.trim());
  if(!lines.length) throw new Error("CSV is empty.");
  const header=lines.shift().split(",").map(s=>s.trim().replace(/^#\s*/,""));
  for(const column of required) if(!header.includes(column)) throw new Error("CSV needs " + required.join(", ") + " columns.");
  return lines.map((line,n)=>{
    const cells=line.split(","); if(cells.length<header.length) throw new Error("Incomplete CSV row " + (n+2) + ".");
    return Object.fromEntries(header.map((h,i)=>[h, cells[i].trim()]));
  });
}
function numeric(x) {
  const v=String(x ?? "").trim().toLowerCase();
  return v==="" || v==="nan" ? null : finite(v);
}
function signalRows(rows,timeCol,valueCol) {
  const t=[],y=[],adc=[];
  for(const row of rows) { const a=numeric(row[timeCol]),b=numeric(row[valueCol]); if(a===null||b===null) continue; t.push(a); y.push(b); if("raw_adc" in row) adc.push(numeric(row.raw_adc)); }
  if(t.length<2 || t.some((v,i)=>i>0&&v<=t[i-1])) throw new Error("Signal timestamps must increase and contain at least two valid samples.");
  return {t,y,...(adc.length?{adc}:{})};
}
function beatRows(rows) {
  return rows.map((row,i)=>({beat:numeric(row.beat)??i+1,p:numeric(row.P_time_s),q:numeric(row.Q_time_s),
    r:numeric(row.R_time_s),s:numeric(row.S_time_s),t:numeric(row.T_time_s)}))
    .filter(b=>b.r!==null).sort((a,b)=>a.r-b.r);
}
function rrRows(rows) {
  return rows.map(row=>({end:numeric(row.R_time_s),rr:numeric(row.RR_s),bpm:numeric(row.instantaneous_bpm),
    accepted:numeric(row.in_configured_range)===1})).filter(x=>x.end!==null && x.rr!==null).sort((a,b)=>a.end-b.end);
}
function readNpy(bytes) {
  const dv=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
  if(bytes.length<16 || String.fromCharCode(...bytes.slice(0,6))!=="\x93NUMPY") throw new Error("NPZ contains an invalid NPY array.");
  const major=bytes[6], len=major>=2?dv.getUint32(8,true):dv.getUint16(8,true), at=major>=2?12:10;
  const header=new TextDecoder().decode(bytes.slice(at,at+len));
  const dtype=header.match(/'descr':\s*'([^']+)'/)?.[1], shape=header.match(/'shape':\s*\(([^)]*)\)/)?.[1];
  if(!dtype||!shape||/fortran_order':\s*True/.test(header)) throw new Error("Unsupported NPY array layout.");
  const dims=shape.split(",").map(x=>x.trim()).filter(Boolean).map(Number);
  if(dims.length!==1) throw new Error("Only one-dimensional NPZ arrays are supported.");
  const m=dtype.match(/^([<>=|])([fiu])([1248])$/), n=dims[0];
  if(!m||m[1]===">"||!Number.isInteger(n)||n<0) throw new Error("Unsupported NPY dtype: " + dtype);
  const size=Number(m[3]), offset=at+len;
  if(offset+n*size>bytes.length) throw new Error("Truncated NPY array.");
  const out=new Array(n);
  for(let i=0;i<n;i++){
    const p=offset+i*size;
    let v;
    if(m[2]==="f"&&size===8) v=dv.getFloat64(p,true);
    else if(m[2]==="f"&&size===4) v=dv.getFloat32(p,true);
    else if(m[2]==="i"&&size===4) v=dv.getInt32(p,true);
    else if(m[2]==="u"&&size===4) v=dv.getUint32(p,true);
    else if(m[2]==="i"&&size===8) v=Number(dv.getBigInt64(p,true));
    else if(m[2]==="u"&&size===8) v=Number(dv.getBigUint64(p,true));
    else if(m[2]==="i"&&size===2) v=dv.getInt16(p,true);
    else if(m[2]==="u"&&size===2) v=dv.getUint16(p,true);
    else if(m[2]==="i"&&size===1) v=dv.getInt8(p);
    else if(m[2]==="u"&&size===1) v=dv.getUint8(p);
    else throw new Error("Unsupported NPY dtype: " + dtype);
    out[i]=v;
  }
  return out;
}
async function readNPZ(file) {
  if(!globalThis.JSZip) throw new Error("NPZ reader unavailable. Choose raw.csv instead.");
  const zip=await JSZip.loadAsync(file), names=["time_s","raw_signal"], arrays={};
  for(const name of names){
    const entry=zip.file(name+".npy"); if(!entry) throw new Error("raw.npz needs " + name + ".npy.");
    arrays[name]=readNpy(await entry.async("uint8array"));
  }
  if(arrays.time_s.length!==arrays.raw_signal.length) throw new Error("NPZ signal arrays have different lengths.");
  const adc=zip.file("raw_adc.npy");
  if(adc) arrays.raw_adc=readNpy(await adc.async("uint8array"));
  if(arrays.raw_adc && arrays.raw_adc.length!==arrays.time_s.length) throw new Error("NPZ ADC array has a different length.");
  return signalRows(arrays.time_s.map((t,i)=>({time_s:t,raw_signal:arrays.raw_signal[i],...(arrays.raw_adc?{raw_adc:arrays.raw_adc[i]}:{})})),"time_s","raw_signal");
}
async function expandInput(input) {
  const files=Array.from(input), archives=files.filter(f=>f.name.toLowerCase().endsWith(".zip"));
  if(!archives.length) return {files,importName:files[0]?.webkitRelativePath?.split("/")[0]||"selected files"};
  if(files.length!==1) throw new Error("Choose one ZIP by itself, or select extracted files.");
  if(!globalThis.JSZip) throw new Error("ZIP reader unavailable. Choose the extracted folder instead.");
  const zip=await JSZip.loadAsync(archives[0]), filesInZip=[];
  for(const entry of Object.values(zip.files)) {
    if(entry.dir) continue;
    const name=entry.name.split("/").at(-1);
    if(!name) continue;
    if(name.toLowerCase()==="ecg_analysis.png") continue;
    if(!["raw.csv","raw.npz","filtered.csv","pqrst_candidates.csv","rr_intervals.csv","metadata.json","analysis.json"].includes(name.toLowerCase())) continue;
    filesInZip.push(new File([await entry.async("uint8array")],name));
  }
  return {files:filesInZip,importName:archives[0].name};
}
function validateRun(run) {
  const signal=run.raw||run.filtered;
  if(!signal) throw new Error("Include raw.csv, raw.npz, or filtered.csv to display this run.");
  const tolerance=(signal.t.at(-1)-signal.t[0])/(signal.t.length-1)*2;
  if(run.raw&&run.filtered&&
    (Math.abs(run.raw.t[0]-run.filtered.t[0])>tolerance || Math.abs(run.raw.t.at(-1)-run.filtered.t.at(-1))>tolerance))
    throw new Error("Raw and filtered time ranges differ; choose files from one output run.");
  if(run.beats.some(b=>b.r<signal.t[0]-tolerance||b.r>signal.t.at(-1)+tolerance))
    throw new Error("R candidate times lie outside the signal range.");
  if(run.rr.length&&run.beats.length) {
    if(run.rr.length!==Math.max(0,run.beats.length-1)||run.rr.some((x,i)=>
      Math.abs(x.end-run.beats[i+1].r)>tolerance || Math.abs(x.rr-(run.beats[i+1].r-run.beats[i].r))>tolerance))
      throw new Error("RR intervals do not align with the R candidates.");
  }
  if(run.analysis?.r_candidates!==undefined && run.files.includes("pqrst_candidates.csv") && run.analysis.r_candidates!==run.beats.length)
    throw new Error("Analysis R count does not match the candidate file.");
}
async function loadRun(input) {
  const recognized=["raw.csv","raw.npz","filtered.csv","pqrst_candidates.csv","rr_intervals.csv","metadata.json","analysis.json"];
  const picked=new Map(), ignored=[];
  const expanded=await expandInput(input);
  for(const file of expanded.files){
    const base=file.name.toLowerCase();
    if(!recognized.includes(base)){ignored.push(file.name);continue;}
    if(picked.has(base)) throw new Error("Multiple " + file.name + " files selected. Choose one output folder.");
    picked.set(base,file);
  }
  if(!picked.size) throw new Error("No recognized ECG output files selected.");
  const run={label:"Imported run",source:"Local files",importName:expanded.importName,raw:null,filtered:null,beats:[],rr:[],metadata:{},analysis:{},files:[...picked.keys()],sample:false};
  const read=async name=>picked.has(name)?await picked.get(name).text():null;
  for(const name of ["metadata.json","analysis.json"]){
    const content=await read(name); if(content) run[name.split(".")[0]]=JSON.parse(content);
  }
  if(picked.has("raw.csv")) run.raw=signalRows(parseCSV(await read("raw.csv"),["time_s","raw_signal"]),"time_s","raw_signal");
  else if(picked.has("raw.npz")) run.raw=await readNPZ(picked.get("raw.npz"));
  if(picked.has("filtered.csv")) run.filtered=signalRows(parseCSV(await read("filtered.csv"),["time_s","filtered_oriented_signal"]),"time_s","filtered_oriented_signal");
  if(picked.has("pqrst_candidates.csv")) run.beats=beatRows(parseCSV(await read("pqrst_candidates.csv"),["R_time_s"]));
  if(picked.has("rr_intervals.csv")) run.rr=rrRows(parseCSV(await read("rr_intervals.csv"),["R_time_s","RR_s"]));
  validateRun(run);
  run.label=label(run);
  return {run,ignored};
}

function extent(){const r=state.recording,s=r?.raw||r?.filtered;return s?{min:s.t[0],max:s.t.at(-1)}:{min:0,max:10};}
function rrBefore(i){const r=state.recording,b=r.beats[i];return r.rr.find(x=>Math.abs(x.end-b.r)<1e-5);}
function beatStatus(i){if(state.flags.get(i)?.flagged)return {text:'Flagged',className:'flagged'};if(rrBefore(i)?.accepted===false)return {text:'RR out of range',className:'suspicious'};return {text:'Inspect',className:''};}
function selectBeat(i,center=true){if(!state.recording?.beats[i])return;state.selected=i;if(center){const e=extent();state.start=Math.max(e.min,Math.min(e.max-state.span,state.recording.beats[i].r-state.span/2));}render();}
function renderSummary(){
 const r=state.recording,a=r.analysis||{},t=a.timing||{};
 const cards=[['Duration',Number.isFinite(t.recorded_span_s)?fmt(t.recorded_span_s,3)+' s':'—',t.samples!==undefined?t.samples.toLocaleString()+' samples':'not supplied'],
 ['Measured sampling',Number.isFinite(t.measured_average_fs_hz)?fmt(t.measured_average_fs_hz,2)+' Hz':'—',r.metadata.target_fs_hz?'Target '+r.metadata.target_fs_hz+' Hz':'not supplied'],
 ['Median estimated HR',Number.isFinite(a.median_hr_bpm)?fmt(a.median_hr_bpm,1)+' bpm':'—',a.accepted_rr_intervals!==undefined?a.accepted_rr_intervals+' accepted RR intervals':'analysis summary not supplied'],
 ['Detected R candidates',String(r.beats.length),['P','Q','S','T'].map(k=>k+' '+r.beats.filter(b=>b[k.toLowerCase()]!==null).length).join(' · ')]];
 $('summary').innerHTML=cards.map(([title,value,sub])=>'<div class="summary-card"><span class="label">'+esc(title)+'</span><strong>'+esc(value)+'</strong><small>'+esc(sub)+'</small></div>').join('');
 $('data-kind').textContent=r.sample?'SYNTHETIC EXAMPLE':simulated(r)?'IMPORTED SIMULATION':'IMPORTED RECORDING';
 $('recording-name').textContent=r.importName||runId(r);
 $('recording-source').textContent=label(r)+' · '+(r.metadata.source||r.source)+' · '+runId(r);
 $('import-summary').textContent=r.sample?'Example data only. Upload your recording to replace it.':r.files.length+' data files loaded. Review stays in this tab until exported.';
 const warnings=Array.isArray(a.warnings)?a.warnings:[];
 $('warnings').hidden=!warnings.length;
 $('warnings').innerHTML='<strong>Analysis warnings</strong><ul>'+warnings.map(w=>'<li>'+esc(w)+'</li>').join('')+'</ul>';
}
function renderBeats(){
 const r=state.recording,only=$('suspicious-only').checked;
 const rows=r.beats.map((b,i)=>({b,i})).filter(({i})=>!only||['flagged','suspicious'].includes(beatStatus(i).className));
 $('beat-list').innerHTML=rows.length?rows.map(({b,i})=>{const rr=rrBefore(i),s=beatStatus(i);return '<button type="button" role="option" aria-selected="'+(state.selected===i)+'" class="beat-row '+(state.selected===i?'selected':'')+'" data-beat="'+i+'"><span class="who">Beat '+esc(b.beat)+'</span><span>'+fmt(b.r,3)+' s</span><span>'+fmt(rr?.rr,3)+' s</span><span class="status '+s.className+'">'+s.text+'</span></button>';}).join(''):'<p class="empty">No candidates in this view. Turn off “Review only” or include pqrst_candidates.csv.</p>';
}
function renderDetail(){
 const r=state.recording,i=state.selected,b=r.beats[i],area=$('beat-detail');
 if(!b){$('detail-title').textContent='Beat detail';area.innerHTML='<p class="empty">No candidate selected.</p>';return;}
 const rr=rrBefore(i),next=r.beats[i+1]?r.beats[i+1].r-b.r:null,review=state.flags.get(i)||{flagged:false,note:''};
 $('detail-title').textContent='Beat '+b.beat;
 area.innerHTML='<p class="detail-lede">R at '+fmt(b.r,3)+' s · '+esc(label(r))+' · '+beatStatus(i).text+'</p>'+
 '<canvas id="detail-chart" class="detail-plot" aria-label="Selected beat close-up with labelled candidate markers"></canvas>'+
 '<div class="wave-labels">'+Object.keys(WAVES).map(k=>{const t=b[k.toLowerCase()];return '<span class="'+(t===null?'missing':'')+'"><b style="color:'+WAVES[k]+'">'+k+'</b> '+(t===null?'not labelled':fmt(t,3)+' s')+'</span>';}).join('')+'</div>'+
 '<div class="detail-metrics"><div><small>RR before</small><strong>'+fmt(rr?.rr,3)+' s</strong></div><div><small>RR after</small><strong>'+fmt(next,3)+' s</strong></div><div><small>Script range</small><strong>'+(!rr||rr.accepted===null?'—':rr.accepted?'In range':'Outside')+'</strong></div></div>'+
 '<label class="flag-row"><input id="flag-check" type="checkbox" '+(review.flagged?'checked':'')+'> Flag this detection for review</label><label class="note-label" for="review-note">Review note (session only)</label><textarea id="review-note" class="review-note" placeholder="Describe what needs inspection">'+esc(review.note)+'</textarea>';
 $('flag-check').addEventListener('change',e=>{state.flags.set(i,{flagged:e.target.checked,note:$('review-note').value});renderBeats();renderDetail();drawSafely();});
 $('review-note').addEventListener('input',e=>state.flags.set(i,{flagged:$('flag-check').checked,note:e.target.value}));
}
function renderContext(){
 const r=state.recording,m=r.metadata||{},a=r.analysis||{};
 $('raw-units').textContent=m.units||'units not supplied';$('filtered-units').textContent=m.units||'units not supplied';
 $('alignment-note').textContent='Shared time window. Select a beat or click near an R marker. Missing labels mean no candidate was supplied.';
 $('run-context').innerHTML='<div class="context-run"><dl>'+[
 ['Recording ID',runId(r)],['Source',m.source||r.source],['Script version',label(r)],['Units',m.units||'not supplied'],['ADC channel',m.channel??'—'],['Polarity',a.polarity_multiplier??'not supplied'],['Filter',a.filter_hz?a.filter_hz.join('–')+' Hz':'not supplied'],['R threshold',a.r_threshold_mode||'not supplied'],['Prominence',fmt(a.r_prominence_threshold,5)],['RR accepted',a.accepted_rr_intervals??'—'],['RR excluded',a.excluded_rr_intervals??'—'],['Files',r.files.join(', ')]
 ].map(([k,v])=>'<dt>'+esc(k)+'</dt><dd>'+esc(v)+'</dd>').join('')+'</dl><details class="json-details"><summary>Full metadata &amp; analysis</summary><pre>'+esc(JSON.stringify({metadata:m,analysis:a},null,2))+'</pre></details></div>';
}
function render(){
 const r=state.recording;if(!r)return;
 if(!r.beats[state.selected])state.selected=r.beats.length?0:null;
 const e=extent();state.span=Math.min(Number($('span-select').value),Math.max(.1,e.max-e.min));state.start=Math.max(e.min,Math.min(state.start,e.max-state.span));
 $('window-label').textContent=fmt(state.start,2)+'–'+fmt(state.start+state.span,2)+' s';
 $('time-slider').disabled=e.max-e.min<=state.span+.001;$('time-slider').value=Math.round(1000*(state.start-e.min)/Math.max(.001,e.max-e.min-state.span));
 renderSummary();renderBeats();renderDetail();renderContext();drawSafely();
}
function canvasSetup(canvas){
 // CSS owns layout. Never use the mutable canvas width/height attributes as CSS sizes.
 const rect=canvas.getBoundingClientRect(),w=rect.width,h=rect.height;
 if(!Number.isFinite(w)||!Number.isFinite(h)||w<1||h<1)throw new Error('Chart has no visible drawing area');
 const ratio=Math.min(Math.max(1,window.devicePixelRatio||1),3,4096/w,2048/h,Math.sqrt(8000000/(w*h)));
 const bw=Math.max(1,Math.round(w*ratio)),bh=Math.max(1,Math.round(h*ratio));
 if(canvas.width!==bw)canvas.width=bw;if(canvas.height!==bh)canvas.height=bh;
 const ctx=canvas.getContext('2d');if(!ctx)throw new Error('Canvas drawing is unavailable');
 ctx.setTransform(bw/w,0,0,bh/h,0,0);ctx.clearRect(0,0,w,h);
 return {ctx,w,h,left:55,right:w-18,top:22,bottom:h-31};
}
function lowerBound(xs,v){let lo=0,hi=xs.length;while(lo<hi){const m=(lo+hi)>>1;if(xs[m]<v)lo=m+1;else hi=m;}return lo;}
function pointsIn(s,lo,hi){if(!s)return [];const first=lowerBound(s.t,lo),last=Math.min(s.t.length,lowerBound(s.t,hi)+1),out=[];for(let i=first;i<last;i++)if(Number.isFinite(s.y[i]))out.push(i);return out;}
function axis(g,min,max,ymin,ymax){
 const {ctx,left,right,top,bottom}=g;ctx.font='12px system-ui';ctx.lineWidth=1;ctx.strokeStyle=COLORS.grid;ctx.fillStyle=COLORS.text;
 for(let j=0;j<=3;j++){const y=top+(bottom-top)*j/3;ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();ctx.textAlign='right';ctx.fillText(fmt(ymax-(ymax-ymin)*j/3,ymax-ymin<.1?3:2),left-7,y+4);}
 const target=Math.max(2,Math.floor((right-left)/90)),base=10**Math.floor(Math.log10((max-min)/target||1));
 const step=[1,2,5,10].map(x=>x*base).find(x=>(max-min)/x<=target)||base*10;
 for(let t=Math.ceil(min/step)*step;t<max-1e-7;t+=step){const x=left+(t-min)/(max-min)*(right-left);ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);ctx.stroke();ctx.textAlign='center';ctx.fillText(fmt(t,step<1?1:0),x,bottom+18);}
 ctx.textAlign='right';ctx.fillText('Time (s)',right,g.h-3);
}
function path(g,s,color,lo,hi,ymin,ymax,width=1.2){
 if(!s)return;const {ctx,left,right,top,bottom}=g,indices=pointsIn(s,lo,hi);if(!indices.length)return;
 ctx.save();ctx.beginPath();ctx.rect(left,top,right-left,bottom-top);ctx.clip();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();
 const bucket=Math.max(1,Math.floor(indices.length/(right-left)*1.3));let moved=false;
 for(let j=0;j<indices.length;j+=bucket){const group=indices.slice(j,j+bucket),low=group.reduce((a,b)=>s.y[a]<s.y[b]?a:b),high=group.reduce((a,b)=>s.y[a]>s.y[b]?a:b);for(const i of [Math.min(low,high),Math.max(low,high)]){const x=left+(s.t[i]-lo)/(hi-lo)*(right-left),y=bottom-(s.y[i]-ymin)/(ymax-ymin)*(bottom-top);if(!moved){ctx.moveTo(x,y);moved=true;}else ctx.lineTo(x,y);}}
 ctx.stroke();ctx.restore();
}
function valueAt(s,t){if(!s)return 0;return s.y[Math.min(s.t.length-1,lowerBound(s.t,t))];}
function domain(s,lo,hi){const vals=pointsIn(s,lo,hi).map(i=>s.y[i]);let min=vals.length?Math.min(...vals):-.5,max=vals.length?Math.max(...vals):.5;const pad=Math.max(.02,(max-min)*.18);return [min-pad,max+pad];}
function markers(g,s,beats,lo,hi,min,max,detail=false){
 const ctx=g.ctx;ctx.font='bold 12px system-ui';ctx.textAlign='center';
 for(const {b,i} of beats)for(const k of Object.keys(WAVES)){
  const t=b[k.toLowerCase()];if(t===null||t<lo||t>hi)continue;
  const x=g.left+(t-lo)/(hi-lo)*(g.right-g.left),y=g.bottom-(valueAt(s,t)-min)/(max-min)*(g.bottom-g.top);
  ctx.fillStyle=WAVES[k];ctx.beginPath();ctx.arc(x,y,k==='R'?4:3,0,Math.PI*2);ctx.fill();
  // Q/S labels go below the point; P/R/T go above. Labels remain visible at narrow widths.
  const ly=k==='Q'||k==='S'?Math.min(g.bottom-1,y+16):Math.max(14,y-10);
  ctx.fillText(k,x,ly);
  if(k==='R'&&(state.selected===i||state.flags.get(i)?.flagged)){ctx.beginPath();ctx.arc(x,y,7,0,Math.PI*2);ctx.strokeStyle=state.flags.get(i)?.flagged?'#A65A00':'#14263D';ctx.lineWidth=1.2;ctx.stroke();}
 }
}
function plotSignal(id,type){
 const r=state.recording,s=r[type],g=canvasSetup($(id)),lo=state.start,hi=lo+state.span,[min,max]=domain(s,lo,hi);axis(g,lo,hi,min,max);
 if(!s){g.ctx.fillStyle=COLORS.text;g.ctx.fillText('No '+type+' file supplied',g.right-10,g.top+30);return;}
 path(g,s,type==='raw'?COLORS.raw:COLORS.signal,lo,hi,min,max);
 if(type==='filtered')markers(g,s,r.beats.map((b,i)=>({b,i})),lo,hi,min,max);
}
function plotRR(){
 const g=canvasSetup($('rr-chart')),lo=state.start,hi=lo+state.span,p=state.recording.rr.filter(x=>x.end>=lo&&x.end<=hi),values=p.map(x=>x.rr);
 let min=values.length?Math.min(...values):.6,max=values.length?Math.max(...values):1;const pad=Math.max(.03,(max-min)*.3);min=Math.max(0,min-pad);max+=pad;axis(g,lo,hi,min,max);
 const ctx=g.ctx;ctx.strokeStyle=COLORS.signal;ctx.lineWidth=1.4;ctx.beginPath();
 p.forEach((v,i)=>{const x=g.left+(v.end-lo)/(hi-lo)*(g.right-g.left),y=g.bottom-(v.rr-min)/(max-min)*(g.bottom-g.top);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();
 for(const v of p){const x=g.left+(v.end-lo)/(hi-lo)*(g.right-g.left),y=g.bottom-(v.rr-min)/(max-min)*(g.bottom-g.top);ctx.fillStyle=v.accepted===false?'#A65A00':COLORS.signal;ctx.beginPath();ctx.arc(x,y,3.5,0,Math.PI*2);ctx.fill();}
}
function drawDetail(){const r=state.recording,i=state.selected,b=r.beats[i];if(!b||!$('detail-chart'))return;const s=r.filtered||r.raw,g=canvasSetup($('detail-chart')),lo=b.r-.32,hi=b.r+.42,[min,max]=domain(s,lo,hi);axis(g,lo,hi,min,max);path(g,s,COLORS.signal,lo,hi,min,max,1.5);markers(g,s,[{b,i}],lo,hi,min,max,true);}
function drawSafely(){
 const errors=[];for(const [name,draw] of [['raw',()=>plotSignal('raw-chart','raw')],['filtered',()=>plotSignal('filtered-chart','filtered')],['RR',plotRR],['beat close-up',drawDetail]])try{draw()}catch(e){errors.push(name+': '+e.message);}
 $('render-status').hidden=!errors.length;$('render-status').textContent=errors.length?'Recording loaded; chart rendering failed ('+errors.join('; ')+'). The signal, analysis and review data are retained.':'';
 return errors;
}
function notice(message,success=false){$('notice').hidden=false;$('notice').className='notice'+(success?' success':'');$('notice').textContent=message;}
async function handleFiles(files){
 const seq=++state.importSeq;let parsed;
 try{parsed=await loadRun(files)}catch(error){if(seq===state.importSeq)notice('Import failed; the previous recording is still displayed. '+error.message);return;}
 if(seq!==state.importSeq)return;
 state.recording=parsed.run;state.flags.clear();state.selected=parsed.run.beats.length?0:null;state.start=extent().min;$('suspicious-only').checked=false;
 notice('Recording loaded: '+parsed.run.files.length+' data files.'+(parsed.ignored.length?' Other files were ignored.':''),true);
 try{render()}catch(error){$('render-status').hidden=false;$('render-status').textContent='Recording loaded; display update failed: '+error.message+'. Data are retained.';}
}
function reviewCSV(){
 const r=state.recording,rows=[['recording_id','input_name','script_version','beat','R_time_s','RR_before_s','review_status','selected','flagged','note']];
 r.beats.forEach((b,i)=>{const review=state.flags.get(i)||{};rows.push([runId(r),r.importName||r.source,label(r),b.beat,b.r,rrBefore(i)?.rr??'',beatStatus(i).text,state.selected===i?'1':'0',review.flagged?'1':'0',review.note||'']);});
 return rows.map(row=>row.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')).join('\r\n')+'\r\n';
}
function exportReview(){const url=URL.createObjectURL(new Blob([reviewCSV()],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='ecg_detection_review.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function registerWebMCP(){const mc=document.modelContext;if(!mc?.registerTool)return;for(const tool of [
 {name:'get_ecg_review_summary',title:'Get ECG review summary',description:'Read the loaded recording summary.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true},execute(){const r=state.recording;return {recording_id:runId(r),script_version:label(r),simulated:simulated(r),r_candidates:r.beats.length,accepted_rr:r.analysis.accepted_rr_intervals,median_hr_bpm:r.analysis.median_hr_bpm,flagged:[...state.flags.values()].filter(x=>x.flagged).length}}},
 {name:'set_ecg_review_flag',title:'Flag ECG candidate',description:'Set a flag and optional note for a beat in the loaded recording.',inputSchema:{type:'object',properties:{beat:{type:'integer',minimum:1},flagged:{type:'boolean'},note:{type:'string',maxLength:500}},required:['beat','flagged'],additionalProperties:false},annotations:{readOnlyHint:false},execute(input){if(!input||!Number.isInteger(input.beat)||typeof input.flagged!=='boolean'||(input.note!==undefined&&(typeof input.note!=='string'||input.note.length>500)))throw new Error('Invalid review input');const i=state.recording.beats.findIndex(b=>b.beat===input.beat);if(i<0)throw new Error('Beat not found');state.flags.set(i,{flagged:input.flagged,note:input.note??state.flags.get(i)?.note??''});state.selected=i;render();return {beat:input.beat,flagged:input.flagged}}}
 ])try{Promise.resolve(mc.registerTool(tool)).catch(()=>{})}catch{}}
// UI wiring is kept separate so the importer and sizing contract can be exercised independently.
for(const id of ['recording-files','recording-folder'])$(id).addEventListener('change',e=>{const f=e.target.files;if(f?.length)handleFiles(f);e.target.value='';});
$('reset-demo').addEventListener('click',()=>{++state.importSeq;state.recording=sample();state.flags.clear();state.selected=0;state.start=0;$('span-select').value='5';$('suspicious-only').checked=false;$('notice').hidden=true;render();});
$('span-select').addEventListener('change',render);
$('time-slider').addEventListener('input',e=>{const ext=extent();state.start=ext.min+Number(e.target.value)/1000*Math.max(0,ext.max-ext.min-state.span);render();});
$('suspicious-only').addEventListener('change',renderBeats);
$('beat-list').addEventListener('click',e=>{const row=e.target.closest('[data-beat]');if(row)selectBeat(Number(row.dataset.beat));});
$('export-flags').addEventListener('click',exportReview);
for(const id of ['raw-chart','filtered-chart'])$(id).addEventListener('click',e=>{const rect=e.target.getBoundingClientRect(),t=state.start+Math.max(0,Math.min(1,(e.clientX-rect.left-55)/(rect.width-73)))*state.span;const found=state.recording.beats.map((b,i)=>({b,i})).filter(x=>x.b.r>=state.start&&x.b.r<=state.start+state.span).sort((a,b)=>Math.abs(a.b.r-t)-Math.abs(b.b.r-t))[0];if(found&&Math.abs(found.b.r-t)<Math.max(.15,state.span*.035))selectBeat(found.i,false);});
let pendingDraw=false,lastObservedWidth=-1;
function scheduleDraw(){if(pendingDraw)return;pendingDraw=true;requestAnimationFrame(()=>{pendingDraw=false;if(state.recording)drawSafely();});}
const observer=new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(Math.abs(width-lastObservedWidth)<.5)return;lastObservedWidth=width;scheduleDraw();});
observer.observe($('chart-stack'));window.addEventListener('resize',scheduleDraw);
state.recording=sample();state.selected=0;render();registerWebMCP();
