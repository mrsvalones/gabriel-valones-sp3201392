"use strict";
// JavaScript progressivo: formulários e navegação MPA continuam no servidor.
document.querySelectorAll("nav a").forEach(a=>{if(a.pathname===location.pathname)a.classList.add("active");});
document.querySelectorAll("[data-print]").forEach(b=>b.addEventListener("click",()=>window.print()));
document.querySelectorAll("[data-back]").forEach(b=>b.addEventListener("click",()=>history.back()));
const purchaseButton=document.querySelector("[data-add-purchase]");
if(purchaseButton)purchaseButton.addEventListener("click",()=>{const body=document.querySelector("#purchase-lines");if(body.children.length>=40)return;const row=body.firstElementChild.cloneNode(true);row.querySelectorAll("input,select").forEach(x=>x.value="");body.appendChild(row);});
const checkout=document.querySelector("#checkout");
if(checkout){
 const cents=value=>Math.round(Number(value||0)*100);
 const format=value=>(value/100).toLocaleString("pt-BR",{style:"currency",currency:"BRL"});
 const total=cents(checkout.dataset.total);
 const fields=[...checkout.querySelectorAll("[data-payment]")];
 const received=checkout.elements.received;
 function preview(){const paid=fields.reduce((sum,f)=>sum+cents(f.value),0);const change=cents(received.value)-cents(checkout.elements.cash.value);checkout.querySelector(".payment-preview").textContent=`Pagamentos: ${format(paid)} · Falta: ${format(total-paid)} · Troco: ${format(Math.max(0,change))}`;}
 checkout.querySelector("#quick-method").addEventListener("change",e=>{fields.forEach(f=>f.value=f.name===e.target.value?(total/100).toFixed(2):"0.00");received.value=e.target.value==="cash"?(total/100).toFixed(2):"0.00";preview();});
 checkout.addEventListener("input",preview);preview();
 checkout.addEventListener("submit",()=>{const b=checkout.querySelector('button[type="submit"],button.wide');if(b){b.disabled=true;b.textContent="Registrando…";}});
}
const NS="http://www.w3.org/2000/svg";
function svgNode(type,attrs,text){const e=document.createElementNS(NS,type);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));if(text!==undefined)e.textContent=text;return e;}
document.querySelectorAll("[data-chart]").forEach(svg=>{
 const data=JSON.parse(svg.dataset.chart),width=Math.max(620,data.length*28+70),height=260,left=65,top=22,bottom=42;
 const max=Math.max(1,...data.map(p=>Number(p.value))),plotH=height-top-bottom,step=(width-left-20)/Math.max(1,data.length);
 svg.setAttribute("viewBox",`0 0 ${width} ${height}`);svg.style.minWidth=width+"px";
 for(let i=0;i<=4;i++){const y=top+plotH*i/4;svg.append(svgNode("line",{x1:left,x2:width-10,y1:y,y2:y,class:"chart-grid"}));svg.append(svgNode("text",{x:left-8,y:y+4,"text-anchor":"end",class:"chart-label"},(max*(1-i/4)).toLocaleString("pt-BR",{maximumFractionDigits:0})));}
 data.forEach((p,i)=>{const h=Number(p.value)/max*plotH,x=left+i*step+5;const bar=svgNode("rect",{x,y:top+plotH-h,width:Math.max(8,step-10),height:h,rx:4,class:"chart-bar"});bar.append(svgNode("title",{},`${p.label}: R$ ${Number(p.value).toFixed(2)}`));svg.append(bar);svg.append(svgNode("text",{x:x+(step-10)/2,y:height-17,"text-anchor":"middle",class:"chart-label"},p.label));});
});
