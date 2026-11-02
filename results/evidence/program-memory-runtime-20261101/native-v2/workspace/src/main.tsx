import React from "react";
import {createRoot} from "react-dom/client";
import {AnimatedGradientText} from "./native/animated-gradient-text";
import {Meteors} from "./native/meteors";
const p=new URLSearchParams(location.search);
createRoot(document.getElementById("root")!).render(<main>
  <h1><AnimatedGradientText data-testid="gradient" colorFrom={p.get("from")||"#ff0000"} colorTo={p.get("to")||"#0000ff"}>Reusable memory canary</AnimatedGradientText></h1>
  <section data-testid="meteor-container" style={{position:"relative",height:320,overflow:"hidden",background:"#101727"}}><Meteors number={Number(p.get("count")??7)} minDelay={0} maxDelay={0} minDuration={2} maxDuration={2}/></section>
</main>);
