function initReportsPage(){
    loadSummary();
    loadCharts();
}

function loadSummary(){
    fetch("/api/reports/summary")
    .then(r=>r.json())
    .then(data=>{
        setText("sum-total", data.total_locations);
        setText("sum-filled", data.filled_trays);
        setText("sum-empty", data.empty_trays);
        setText("sum-users", data.total_users);
        setText("sum-stored", data.stored_count);
        setText("sum-issued", data.issued_count);
    })
    .catch(()=>setMsg("Unable to load analytics summary", true));
}

function loadCharts(){
    fetch("/api/reports/charts")
    .then(r=>r.json())
    .then(data=>{
        renderTrayRatio(data.tray_ratio || {});
        renderSideUtilization(data.side_utilization || []);
        renderMaterialDistribution(data.material_distribution || []);
        renderTrend(data.movement_trend || []);
    })
    .catch(()=>setMsg("Unable to load chart analytics", true));
}

function setText(id, value){
    const el = document.getElementById(id);
    if(el) el.innerText = value;
}

function setMsg(msg, isError){
    const el = document.getElementById("reports-msg");
    if(!el) return;
    el.innerText = msg;
    el.style.color = isError ? "#f87171" : "#4ade80";
}

function renderTrayRatio(ratio){
    const total = Number(ratio.total || 0);
    const filled = Number(ratio.filled || 0);
    const empty = Number(ratio.empty || 0);
    const filledPct = total ? (filled * 100 / total) : 0;
    const emptyPct = total ? (empty * 100 / total) : 0;

    const filledEl = document.getElementById("ratio-filled");
    const emptyEl = document.getElementById("ratio-empty");
    const legend = document.getElementById("ratio-legend");
    if(filledEl) filledEl.style.width = `${filledPct}%`;
    if(emptyEl) emptyEl.style.width = `${emptyPct}%`;
    if(legend) legend.innerText = `Filled: ${filled} (${filledPct.toFixed(1)}%) | Empty: ${empty} (${emptyPct.toFixed(1)}%)`;
}

function renderSideUtilization(rows){
    const box = document.getElementById("side-chart");
    if(!box) return;
    box.innerHTML = "";
    if(!rows.length){
        box.innerHTML = "<div class='chart-empty'>No side data</div>";
        return;
    }

    rows.forEach(r=>{
        const total = Number(r.filled || 0) + Number(r.empty || 0);
        const filledPct = total ? (Number(r.filled || 0) * 100 / total) : 0;
        const emptyPct = 100 - filledPct;
        const row = document.createElement("div");
        row.className = "stack-row";
        row.innerHTML = `
            <div class="stack-label">${r.side}</div>
            <div class="stack-bar">
                <div class="stack-fill" style="width:${filledPct}%"></div>
                <div class="stack-empty" style="width:${emptyPct}%"></div>
            </div>
            <div class="stack-value">${r.filled}/${total}</div>
        `;
        box.appendChild(row);
    });
}

function renderMaterialDistribution(rows){
    const box = document.getElementById("material-chart");
    if(!box) return;
    box.innerHTML = "";
    if(!rows.length){
        box.innerHTML = "<div class='chart-empty'>No material activity yet</div>";
        return;
    }
    const max = Math.max(...rows.map(r=>Number(r.count || 0)), 1);
    rows.forEach(r=>{
        const pct = (Number(r.count || 0) * 100 / max);
        const el = document.createElement("div");
        el.className = "bar-row";
        el.innerHTML = `
            <div class="bar-label">${(r.material_type || "UNKNOWN").replace("_"," ")}</div>
            <div class="bar-wrap"><div class="bar-fill" style="width:${pct}%"></div></div>
            <div class="bar-value">${r.count}</div>
        `;
        box.appendChild(el);
    });
}

function renderTrend(rows){
    const box = document.getElementById("trend-chart");
    if(!box) return;
    box.innerHTML = "";
    if(!rows.length){
        box.innerHTML = "<div class='chart-empty'>No movement trend data</div>";
        return;
    }
    const max = Math.max(
        ...rows.map(r=>Math.max(Number(r.inward || 0), Number(r.outward || 0))),
        1
    );
    rows.forEach(r=>{
        const inwardPct = (Number(r.inward || 0) * 100 / max);
        const outwardPct = (Number(r.outward || 0) * 100 / max);
        const el = document.createElement("div");
        el.className = "trend-row";
        el.innerHTML = `
            <div class="trend-date">${r.date}</div>
            <div class="trend-bars">
                <div class="trend-inward" style="width:${inwardPct}%"></div>
                <div class="trend-outward" style="width:${outwardPct}%"></div>
            </div>
            <div class="trend-value">IN ${r.inward} | OUT ${r.outward}</div>
        `;
        box.appendChild(el);
    });
}

function downloadReport(url){
    window.location.href = url;
}

function downloadItemWise(){
    const q = document.getElementById("item-query").value.trim();
    if(!q){
        setMsg("Enter item ID or description", true);
        return;
    }
    downloadReport(`/api/reports/item-wise.pdf?q=${encodeURIComponent(q)}`);
}

function downloadLocationWise(){
    const loc = document.getElementById("loc-query").value.trim();
    if(!loc){
        setMsg("Enter location ID", true);
        return;
    }
    downloadReport(`/api/reports/location-wise.pdf?loc=${encodeURIComponent(loc)}`);
}

function downloadUserWise(){
    const user = document.getElementById("user-query").value.trim();
    if(!user){
        setMsg("Enter username", true);
        return;
    }
    downloadReport(`/api/reports/user-wise.pdf?user=${encodeURIComponent(user)}`);
}

function goDashboard(){
    window.location.href = "/dashboard";
}

function logout(){
    fetch("/logout")
    .then(()=>window.location.href="/");
}
