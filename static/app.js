let row = 1;
let selected = null;
const CELLS_PER_PAGE = 16;
const RIGHT_MAX = 149;
const AUTO_REFRESH_MS = 2000;
const OP_STATUS_REFRESH_MS = 1000;
const PLC_STATUS_REFRESH_MS = 3000;
let isLoadingGrid = false;
let refreshTimer = null;
let opStatusTimer = null;
let plcStatusTimer = null;
let lastFinishedAt = null;
let operationRunning = false;
let plcConnected = false;
let locationsCache = new Map();
let dashboardInitialized = false;
let selectedMaterialType = null;
const MATERIAL_TYPE_MAP = {
    TYPE_A: "Type A material",
    TYPE_B: "Type B material",
    TYPE_C: "Type C material"
};

seedDefaultLocations();
bindDashboardInit();

function initDashboard(){
    if(dashboardInitialized) return;
    dashboardInitialized = true;

    renderFromMap(locationsCache);
    loadGrid();
    pollOperationStatus();
    pollPlcStatus();
    if(refreshTimer) return;
    refreshTimer = setInterval(loadGrid, AUTO_REFRESH_MS);
    if(!opStatusTimer){
        opStatusTimer = setInterval(pollOperationStatus, OP_STATUS_REFRESH_MS);
    }
    if(!plcStatusTimer){
        plcStatusTimer = setInterval(pollPlcStatus, PLC_STATUS_REFRESH_MS);
    }
}

function bindDashboardInit(){
    if(document.readyState === "loading"){
        document.addEventListener("DOMContentLoaded", initDashboard, { once: true });
        return;
    }
    initDashboard();
}

function loadGrid(){
    if(isLoadingGrid) return;
    isLoadingGrid = true;
    fetch("/api/locations")
    .then(r => {
        if(!r.ok) throw new Error("Locations API failed");
        return r.json();
    })
    .then(d => {
        locationsCache = normalizeLocations(d);
        renderFromMap(locationsCache);
    })
    .catch(()=>{
        setOpMsg("Auto-refresh failed", true);
        renderFromMap(locationsCache);
    })
    .finally(()=>{ isLoadingGrid = false; });
}

function getRow(side){
    let base = side == "RIGHT" ? 1 : 150;
    return [...Array(CELLS_PER_PAGE).keys()]
           .map(i => base + (row-1)*CELLS_PER_PAGE + i);
}

function render(data){
    const map = normalizeLocations(data);
    renderFromMap(map);
}

function renderFromMap(map){

    document.getElementById("row").innerText = row;

    let R = document.getElementById("right");
    let L = document.getElementById("left");
    R.innerHTML = "";
    L.innerHTML = "";

    // RIGHT SIDE
    getRow("RIGHT").forEach(n=>{
        let r = map.get(n) || [n, "RIGHT", null, null];

        let d = document.createElement("div");
        d.className = "seat " + (r[2] ? "full" : "empty");
        d.innerText = n;
        d.onclick = () => select(r);
        R.appendChild(d);
    });

    // LEFT SIDE
    getRow("LEFT").forEach(n=>{
        let r = map.get(n) || [n, "LEFT", null, null];

        let d = document.createElement("div");
        d.className = "seat " + (r[2] ? "full" : "empty");
        d.innerText = n;
        d.onclick = () => select(r);
        L.appendChild(d);
    });

    // keep selected location synced with latest DB state
    if(selected){
        let latest = map.get(Number(selected[0]));
        if(latest){
            select(latest);
        }
    }
}

function normalizeLocations(data){
    const map = new Map(locationsCache);
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

function seedDefaultLocations(){
    for(let i=1; i<=297; i++){
        const side = i <= RIGHT_MAX ? "RIGHT" : "LEFT";
        locationsCache.set(i, [i, side, null, null]);
    }
}

function inward(){
    if(!selected) return alert("Select location first");
    if(!plcConnected){
        setOpMsg("PLC is offline. Cannot start inward cycle.", true);
        return;
    }
    if(selected[2]) {
        setOpMsg(`Location ${selected[0]} is already occupied`, true);
        return;
    }

    const itemValue = document.getElementById("item").value.trim();
    const descValue = document.getElementById("desc").value.trim();
    const hasManualEntry = itemValue.length > 0 && descValue.length > 0;
    const hasTypeEntry = !!selectedMaterialType;

    if(!hasManualEntry && !hasTypeEntry){
        setOpMsg("Enter Item ID + Description, or select Type A/B/C", true);
        return;
    }

    fetch("/api/inward",{
        method:"POST",
        body:new URLSearchParams({
            loc:selected[0],
            item:itemValue,
            desc:descValue,
            material_type:selectedMaterialType || ""
        })
    })
    .then(r=>r.json())
    .then(res=>{
        if(res.status === "accepted"){
            setOpMsg(res.msg || `INWARD started for location ${selected[0]}`, false);
            setOperationButtons(true);
            pollOperationStatus();
            return;
        }
        setOpMsg(res.msg || "Inward failed", true);
    })
    .catch(()=>{
        setOpMsg("Inward request failed", true);
    });
}

function outward(){
    if(!selected) return alert("Select location first");
    if(!plcConnected){
        setOpMsg("PLC is offline. Cannot start outward cycle.", true);
        return;
    }

    fetch("/api/outward",{
        method:"POST",
        body:new URLSearchParams({
            loc:selected[0]
        })
    })
    .then(r=>r.json())
    .then(res=>{
        if(res.status === "accepted"){
            setOpMsg(res.msg || `OUTWARD started for location ${selected[0]}`, false);
            setOperationButtons(true);
            pollOperationStatus();
            return;
        }
        setOpMsg(res.msg || "Outward failed", true);
    })
    .catch(()=>{
        setOpMsg("Outward request failed", true);
    });
}

function prev(){
    if(row>1){
        row--;
        loadGrid();
    }
}

function next(){
    if(row<11){
        row++;
        loadGrid();
    }
}

function doSearch(){

    let q = document.getElementById("search").value.trim();
    if(!q) return;

    fetch("/api/search/"+q)
    .then(r=>r.json())
    .then(x=>{

        if(!x){
            setOpMsg("No matching location/item found", true);
            alert("Not found");
            return;
        }

        let loc = x[0];

        // calculate page
        if(loc <= RIGHT_MAX){
            row = Math.ceil(loc / CELLS_PER_PAGE);
        }
        else{
            row = Math.ceil((loc - RIGHT_MAX) / CELLS_PER_PAGE);
        }

        selected = x;
        loadGrid();

        // wait for grid render then highlight
        setTimeout(()=>{
            select(x);
        },150);
    });
}

function setOpMsg(message, isError){
    const msg = document.getElementById("op-msg");
    if(!msg) return;
    msg.innerText = message;
    msg.style.color = isError ? "#f87171" : "#4ade80";
}

function setOperationButtons(disabled){
    const inwardBtn = document.getElementById("inward-btn");
    const outwardBtn = document.getElementById("outward-btn");
    if(inwardBtn) inwardBtn.disabled = disabled;
    if(outwardBtn) outwardBtn.disabled = disabled;

    ["type-a", "type-b", "type-c"].forEach(id=>{
        const btn = document.getElementById(id);
        if(btn) btn.disabled = disabled;
    });
}

function updateButtonState(){
    setOperationButtons(operationRunning || !plcConnected);
}

function pollOperationStatus(){
    fetch("/api/op-status")
    .then(r=>r.json())
    .then(status=>{
        operationRunning = !!status.running;
        if(status.running){
            updateButtonState();
            const op = (status.type || "operation").toUpperCase();
            setOpMsg(`${op} in progress at location ${status.loc}`, false);
            return;
        }

        updateButtonState();

        if(status.finished_at && status.finished_at !== lastFinishedAt){
            lastFinishedAt = status.finished_at;
            setOpMsg(status.msg || "Cycle finished", status.status === "failed");
            loadGrid();
        }
    })
    .catch(()=>{});
}

function pollPlcStatus(){
    fetch("/api/plc-status")
    .then(r=>r.json())
    .then(res=>{
        plcConnected = !!res.connected;
        setPlcStatus(plcConnected, res.msg || "");
        updateButtonState();
    })
    .catch(()=>{
        plcConnected = false;
        setPlcStatus(false, "PLC status poll failed");
        updateButtonState();
    });
}

function setPlcStatus(connected, message){
    const badge = document.getElementById("plc-status");
    if(!badge) return;
    badge.classList.remove("plc-online", "plc-offline", "plc-unknown");
    if(connected){
        badge.classList.add("plc-online");
        badge.title = message;
        badge.innerText = "PLC: ONLINE";
        return;
    }
    badge.classList.add("plc-offline");
    badge.title = message;
    badge.innerText = "PLC: OFFLINE";
}

function setMaterialType(type){
    const itemInput = document.getElementById("item");
    const descInput = document.getElementById("desc");
    const description = MATERIAL_TYPE_MAP[type];

    if(!description){
        setOpMsg("Invalid material type selected", true);
        return;
    }

    selectedMaterialType = type;
    if(itemInput) itemInput.value = makeUuid();
    if(descInput) descInput.value = description;
    highlightMaterialType(type);
    setOpMsg(`${type.replace("_", " ")} selected and fields auto-filled`, false);
}

function highlightMaterialType(type){
    const types = ["TYPE_A", "TYPE_B", "TYPE_C"];
    types.forEach(t=>{
        const btn = document.getElementById(`type-${t.split("_")[1].toLowerCase()}`);
        if(!btn) return;
        btn.classList.toggle("type-selected", t === type);
    });
}

function makeUuid(){
    if(window.crypto && crypto.randomUUID){
        return crypto.randomUUID();
    }
    return "id-" + Date.now() + "-" + Math.random().toString(16).slice(2, 10);
}

function select(r){

    // remove previous highlight
    document.querySelectorAll(".seat").forEach(s=>{
        s.classList.remove("selected");
    });

    selected = r;

    // highlight clicked seat
    let seat = [...document.querySelectorAll(".seat")]
               .find(x=>x.innerText==r[0]);

    if(seat){
        seat.classList.add("selected");
    }

    document.getElementById("sel").innerText = "LOC " + r[0];
}

function logout(){
    fetch("/logout")
    .then(()=>window.location.href="/");
}

function openReports(){
    window.location.href = "/reports";
}

function openManualEntry(){
    window.location.href = "/manual-entry";
}
