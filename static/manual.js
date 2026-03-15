let manualRow = 1;
let manualSelected = null;
const MANUAL_CELLS_PER_PAGE = 16;
const MANUAL_RIGHT_MAX = 149;
const MANUAL_AUTO_REFRESH_MS = 5000;
const MANUAL_OP_REFRESH_MS = 1000;
let manualLoading = false;
let manualRefreshTimer = null;
let manualOpTimer = null;
let manualCycleRunning = false;
let manualCycleLoc = null;
let manualLocationsCache = new Map();
let manualInitialized = false;
let manualDraftDirty = false;
let manualEditingLoc = null;

seedManualLocations();
bindManualInit();

function initManualPage(){
    if(manualInitialized) return;
    manualInitialized = true;

    bindManualDraftTracking();
    renderManualFromMap(manualLocationsCache);
    loadManualGrid();
    pollCycleStatus();

    if(!manualRefreshTimer){
        manualRefreshTimer = setInterval(loadManualGrid, MANUAL_AUTO_REFRESH_MS);
    }
    if(!manualOpTimer){
        manualOpTimer = setInterval(pollCycleStatus, MANUAL_OP_REFRESH_MS);
    }
}

function bindManualInit(){
    if(document.readyState === "loading"){
        document.addEventListener("DOMContentLoaded", initManualPage, { once: true });
        return;
    }
    initManualPage();
}

function seedManualLocations(){
    for(let i=1; i<=297; i++){
        const side = i <= MANUAL_RIGHT_MAX ? "RIGHT" : "LEFT";
        manualLocationsCache.set(i, [i, side, null, null]);
    }
}

function bindManualDraftTracking(){
    const itemInput = document.getElementById("manual-item");
    const descInput = document.getElementById("manual-desc");
    if(itemInput){
        itemInput.addEventListener("input", markManualDraftDirty);
    }
    if(descInput){
        descInput.addEventListener("input", markManualDraftDirty);
    }
}

function markManualDraftDirty(){
    if(!manualSelected) return;
    manualDraftDirty = true;
    manualEditingLoc = Number(manualSelected[0]);
}

function hasUnsavedDraftForSelected(){
    if(!manualSelected) return false;
    return manualDraftDirty && Number(manualEditingLoc) === Number(manualSelected[0]);
}

function normalizeManualLocations(data){
    const map = new Map(manualLocationsCache);
    if(!Array.isArray(data)) return map;

    data.forEach(row=>{
        if(Array.isArray(row)){
            const loc = Number(row[0]);
            if(Number.isNaN(loc)) return;
            map.set(loc, [loc, row[1], row[2], row[3]]);
            return;
        }
        if(row && typeof row === "object"){
            const loc = Number(row.location_id);
            if(Number.isNaN(loc)) return;
            map.set(loc, [loc, row.side, row.item_id, row.description]);
        }
    });
    return map;
}

function getManualRow(side){
    const base = side === "RIGHT" ? 1 : 150;
    return [...Array(MANUAL_CELLS_PER_PAGE).keys()]
           .map(i => base + (manualRow - 1) * MANUAL_CELLS_PER_PAGE + i);
}

function loadManualGrid(){
    if(manualLoading) return;
    manualLoading = true;
    fetch("/api/locations")
    .then(r=>{
        if(!r.ok) throw new Error("Locations API failed");
        return r.json();
    })
    .then(data=>{
        manualLocationsCache = normalizeManualLocations(data);
        renderManualFromMap(manualLocationsCache);
    })
    .catch(()=>{
        setManualMsg("Unable to refresh location data", true);
        renderManualFromMap(manualLocationsCache);
    })
    .finally(()=>{ manualLoading = false; });
}

function renderManualFromMap(map){
    const rowEl = document.getElementById("manual-row");
    if(rowEl) rowEl.innerText = manualRow;

    const right = document.getElementById("manual-right");
    const left = document.getElementById("manual-left");
    if(!right || !left) return;
    right.innerHTML = "";
    left.innerHTML = "";

    getManualRow("RIGHT").forEach(n=>{
        const r = map.get(n) || [n, "RIGHT", null, null];
        const d = document.createElement("div");
        d.className = "seat " + (r[2] ? "full" : "empty");
        d.innerText = n;
        d.onclick = ()=>selectManual(r);
        right.appendChild(d);
    });

    getManualRow("LEFT").forEach(n=>{
        const r = map.get(n) || [n, "LEFT", null, null];
        const d = document.createElement("div");
        d.className = "seat " + (r[2] ? "full" : "empty");
        d.innerText = n;
        d.onclick = ()=>selectManual(r);
        left.appendChild(d);
    });

    if(manualSelected){
        const latest = map.get(Number(manualSelected[0]));
        if(latest){
            selectManual(latest, false);
        }
    }
}

function selectManual(r, forceSyncInputs = false){
    const prevLoc = manualSelected ? Number(manualSelected[0]) : null;
    document.querySelectorAll(".seat").forEach(s=>s.classList.remove("selected"));
    manualSelected = r;

    const seat = [...document.querySelectorAll(".seat")]
                .find(x=>x.innerText === String(r[0]));
    if(seat) seat.classList.add("selected");

    const sel = document.getElementById("manual-sel");
    if(sel){
        sel.innerText = `LOC ${r[0]} | ${r[2] ? "Occupied" : "Empty"}`;
    }

    const sameLocation = prevLoc === Number(r[0]);
    const shouldSyncInputs = forceSyncInputs || !sameLocation || !hasUnsavedDraftForSelected();

    if(shouldSyncInputs){
        const itemInput = document.getElementById("manual-item");
        const descInput = document.getElementById("manual-desc");
        if(itemInput) itemInput.value = r[2] || "";
        if(descInput) descInput.value = r[3] || "";
        manualDraftDirty = false;
        manualEditingLoc = Number(r[0]);
    }

    updateManualButtons();
}

function prevManual(){
    if(manualRow > 1){
        manualRow--;
        loadManualGrid();
    }
}

function nextManual(){
    if(manualRow < 11){
        manualRow++;
        loadManualGrid();
    }
}

function doManualSearch(){
    const q = (document.getElementById("manual-search")?.value || "").trim();
    if(!q) return;

    fetch("/api/search/" + encodeURIComponent(q))
    .then(r=>r.json())
    .then(x=>{
        if(!x){
            setManualMsg("No matching location/item found", true);
            return;
        }

        const loc = Number(x[0]);
        if(loc <= MANUAL_RIGHT_MAX){
            manualRow = Math.ceil(loc / MANUAL_CELLS_PER_PAGE);
        }else{
            manualRow = Math.ceil((loc - MANUAL_RIGHT_MAX) / MANUAL_CELLS_PER_PAGE);
        }

        manualSelected = x;
        loadManualGrid();
        setTimeout(()=>selectManual(x, true), 150);
    })
    .catch(()=>setManualMsg("Search failed", true));
}

function isCycleBlockedForSelection(){
    if(!manualSelected) return false;
    return manualCycleRunning && Number(manualCycleLoc) === Number(manualSelected[0]);
}

function updateManualButtons(){
    const addBtn = document.getElementById("manual-add-btn");
    const removeBtn = document.getElementById("manual-remove-btn");
    const disabled = isCycleBlockedForSelection();
    if(addBtn) addBtn.disabled = disabled;
    if(removeBtn) removeBtn.disabled = disabled;
}

function manualAdd(){
    if(!manualSelected){
        setManualMsg("Select a location first", true);
        return;
    }
    if(isCycleBlockedForSelection()){
        setManualMsg(`Cycle is running at location ${manualSelected[0]}. Manual add blocked`, true);
        return;
    }
    if(manualSelected[2]){
        setManualMsg(`Location ${manualSelected[0]} is already occupied`, true);
        return;
    }

    const item = (document.getElementById("manual-item")?.value || "").trim();
    const desc = (document.getElementById("manual-desc")?.value || "").trim();
    if(!item || !desc){
        setManualMsg("Item ID and Description are required", true);
        return;
    }

    fetch("/api/manual/add", {
        method: "POST",
        body: new URLSearchParams({
            loc: manualSelected[0],
            item: item,
            desc: desc
        })
    })
    .then(r=>r.json())
    .then(res=>{
        if(res.status === "success"){
            manualDraftDirty = false;
            setManualMsg(res.msg || "Manual add completed", false);
            loadManualGrid();
            return;
        }
        setManualMsg(res.msg || "Manual add failed", true);
    })
    .catch(()=>setManualMsg("Manual add request failed", true));
}

function manualRemove(){
    if(!manualSelected){
        setManualMsg("Select a location first", true);
        return;
    }
    if(isCycleBlockedForSelection()){
        setManualMsg(`Cycle is running at location ${manualSelected[0]}. Manual remove blocked`, true);
        return;
    }
    if(!manualSelected[2]){
        setManualMsg(`Location ${manualSelected[0]} is already empty`, true);
        return;
    }

    fetch("/api/manual/remove", {
        method: "POST",
        body: new URLSearchParams({ loc: manualSelected[0] })
    })
    .then(r=>r.json())
    .then(res=>{
        if(res.status === "success"){
            const itemInput = document.getElementById("manual-item");
            const descInput = document.getElementById("manual-desc");
            if(itemInput) itemInput.value = "";
            if(descInput) descInput.value = "";
            manualDraftDirty = false;
            setManualMsg(res.msg || "Manual remove completed", false);
            loadManualGrid();
            return;
        }
        setManualMsg(res.msg || "Manual remove failed", true);
    })
    .catch(()=>setManualMsg("Manual remove request failed", true));
}

function pollCycleStatus(){
    fetch("/api/op-status")
    .then(r=>r.json())
    .then(status=>{
        manualCycleRunning = !!status.running;
        manualCycleLoc = status.loc;
        updateCycleBadge(status);
        updateManualButtons();
    })
    .catch(()=>{
        manualCycleRunning = false;
        manualCycleLoc = null;
        setCycleBadgeUnknown();
        updateManualButtons();
    });
}

function updateCycleBadge(status){
    const badge = document.getElementById("manual-cycle-status");
    if(!badge) return;
    badge.classList.remove("plc-online", "plc-offline", "plc-unknown");

    if(status.running){
        badge.classList.add("plc-offline");
        badge.innerText = `CYCLE: RUNNING LOC ${status.loc}`;
        badge.title = status.msg || "Cycle running";
        return;
    }

    badge.classList.add("plc-online");
    badge.innerText = "CYCLE: IDLE";
    badge.title = status.msg || "No cycle running";
}

function setCycleBadgeUnknown(){
    const badge = document.getElementById("manual-cycle-status");
    if(!badge) return;
    badge.classList.remove("plc-online", "plc-offline", "plc-unknown");
    badge.classList.add("plc-unknown");
    badge.innerText = "CYCLE: UNKNOWN";
    badge.title = "Unable to read cycle status";
}

function setManualMsg(message, isError){
    const msg = document.getElementById("manual-msg");
    if(!msg) return;
    msg.innerText = message;
    msg.style.color = isError ? "#f87171" : "#4ade80";
}

function goDashboard(){
    window.location.href = "/dashboard";
}

function goReports(){
    window.location.href = "/reports";
}

function logout(){
    fetch("/logout")
    .then(()=>window.location.href = "/");
}
