let row = 1;
let selected = null;
const CELLS_PER_PAGE = 16;
const RIGHT_MAX = 149;

function loadGrid(){
    fetch("/api/locations")
    .then(r => r.json())
    .then(d => render(d))
}

function getRow(side){
    let base = side == "RIGHT" ? 1 : 150;
    return [...Array(CELLS_PER_PAGE).keys()]
           .map(i => base + (row-1)*CELLS_PER_PAGE + i);
}

function render(data){

    document.getElementById("row").innerText = row;

    let R = document.getElementById("right");
    let L = document.getElementById("left");
    R.innerHTML = "";
    L.innerHTML = "";

    // RIGHT SIDE
    getRow("RIGHT").forEach(n=>{
        let r = data.find(x=>x[0]==n);
        if(!r) return;

        let d = document.createElement("div");
        d.className = "seat " + (r[2] ? "full" : "empty");
        d.innerText = n;
        d.onclick = () => select(r);
        R.appendChild(d);
    });

    // LEFT SIDE
    getRow("LEFT").forEach(n=>{
        let r = data.find(x=>x[0]==n);
        if(!r) return;

        let d = document.createElement("div");
        d.className = "seat " + (r[2] ? "full" : "empty");
        d.innerText = n;
        d.onclick = () => select(r);
        L.appendChild(d);
    });
}

function select(r){
    selected = r;
    document.getElementById("sel").innerText = "LOC " + r[0];
}

function inward(){
    if(!selected) return alert("Select location first");

    fetch("/api/inward",{
        method:"POST",
        body:new URLSearchParams({
            loc:selected[0],
            item:document.getElementById("item").value,
            desc:document.getElementById("desc").value
        })
    }).then(()=>loadGrid())
}

function outward(){
    if(!selected) return alert("Select location first");

    fetch("/api/outward",{
        method:"POST",
        body:new URLSearchParams({
            loc:selected[0]
        })
    }).then(()=>loadGrid())
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