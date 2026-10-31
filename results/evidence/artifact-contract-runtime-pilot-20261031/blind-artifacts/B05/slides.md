---
layout: cover
transition: slide-left
---

---
theme: dark
layout: cover
transition: fade
class: text-center
---

<div class="text-[11px] tracking-[0.35em] uppercase text-blue-300/70 mb-6">Team research briefing &middot; 2023 retrospective</div>

# Embodied AI in 2023

<div class="text-2xl text-slate-300 mt-3 font-light">How web&#8209;scale models learned to perceive,<br/>plan, and act</div>

<div class="mt-12 flex items-center justify-center gap-3 text-sm">
  <span class="px-3 py-1 rounded-full border border-blue-400/40 text-blue-200">PaLM-E</span>
  <span class="px-3 py-1 rounded-full border border-indigo-400/40 text-indigo-200">RT-2</span>
  <span class="px-3 py-1 rounded-full border border-emerald-400/40 text-emerald-200">Voyager</span>
</div>

<div class="absolute bottom-10 left-0 right-0 text-xs text-slate-500">
AI Research Team &nbsp;·&nbsp; 15&#8209;minute session &nbsp;·&nbsp; arXiv 2303.03378 · 2307.15818 · 2305.16291
</div>


---
layout: default
transition: slide-left
---

<div class="text-[11px] tracking-[0.3em] uppercase text-blue-400/70 mb-2">Roadmap</div>

# What we'll cover

<div class="grid grid-cols-2 gap-x-10 gap-y-6 mt-8 text-[15px]">

<div class="flex gap-4">
  <div class="text-blue-400 font-mono text-lg leading-none pt-1">01</div>
  <div>
    <div class="font-semibold text-white">The grounding gap</div>
    <div class="text-slate-400 text-sm leading-snug">Why 2023 became the year LLMs were pushed into the physical world.</div>
    <div class="text-[11px] text-slate-500 mt-1">~2 min</div>
  </div>
</div>

<div class="flex gap-4">
  <div class="text-blue-400 font-mono text-lg leading-none pt-1">02</div>
  <div>
    <div class="font-semibold text-white">PaLM-E &mdash; perception inside the model</div>
    <div class="text-slate-400 text-sm leading-snug">Multimodal sentences, transfer across embodiments, a 562B generalist.</div>
    <div class="text-[11px] text-slate-500 mt-1">~3.5 min</div>
  </div>
</div>

<div class="flex gap-4">
  <div class="text-blue-400 font-mono text-lg leading-none pt-1">03</div>
  <div>
    <div class="font-semibold text-white">RT-2 &mdash; actions as another language</div>
    <div class="text-slate-400 text-sm leading-snug">Vision&#8209;language&#8209;action models and emergent semantic reasoning.</div>
    <div class="text-[11px] text-slate-500 mt-1">~3.5 min</div>
  </div>
</div>

<div class="flex gap-4">
  <div class="text-blue-400 font-mono text-lg leading-none pt-1">04</div>
  <div>
    <div class="font-semibold text-white">Voyager &mdash; the lifelong agent</div>
    <div class="text-slate-400 text-sm leading-snug">Curriculum, skill library, and code as an action space in Minecraft.</div>
    <div class="text-[11px] text-slate-500 mt-1">~3 min</div>
  </div>
</div>

<div class="flex gap-4">
  <div class="text-blue-400 font-mono text-lg leading-none pt-1">05</div>
  <div>
    <div class="font-semibold text-white">Synthesis &amp; comparison</div>
    <div class="text-slate-400 text-sm leading-snug">Three answers to one question &mdash; and where they disagree.</div>
    <div class="text-[11px] text-slate-500 mt-1">~2 min</div>
  </div>
</div>

<div class="flex gap-4">
  <div class="text-blue-400 font-mono text-lg leading-none pt-1">06</div>
  <div>
    <div class="font-semibold text-white">Open problems &amp; future directions</div>
    <div class="text-slate-400 text-sm leading-snug">What is still missing before these systems leave the lab.</div>
    <div class="text-[11px] text-slate-500 mt-1">~2 min</div>
  </div>
</div>

</div>

<div class="mt-8 text-xs text-slate-500 border-l-2 border-blue-500/40 pl-3">
Everything in this deck is drawn from the three papers themselves &mdash; numbers are quoted as reported by the authors.
</div>


---
layout: default
transition: slide-left
---

<div class="text-[11px] tracking-[0.3em] uppercase text-blue-400/70 mb-2">01 &middot; Context</div>

# The grounding gap

<div class="grid grid-cols-2 gap-8 mt-6">

<div class="rounded-xl border border-white/10 bg-white/[0.04] p-5">
  <div class="text-sm font-semibold text-blue-300 mb-3">What web&#8209;scale models were good at</div>
  <ul class="text-sm text-slate-300 space-y-2 leading-snug">
    <li>Reasoning, dialogue, step&#8209;by&#8209;step chains of thought</li>
    <li>Open&#8209;vocabulary recognition and visual question answering</li>
    <li>Commonsense and semantic knowledge at internet scale</li>
  </ul>
</div>

<div class="rounded-xl border border-white/10 bg-white/[0.04] p-5">
  <div class="text-sm font-semibold text-rose-300 mb-3">What embodied agents actually need</div>
  <ul class="text-sm text-slate-300 space-y-2 leading-snug">
    <li>Grounded perception: where things <em>are</em>, not just what they are</li>
    <li>Actions in Cartesian space, at control frequency</li>
    <li>Long&#8209;horizon composition and recovery from failure</li>
  </ul>
</div>

</div>

<div class="mt-6 rounded-xl border border-blue-400/30 bg-blue-500/10 p-5">
  <div class="text-sm text-slate-200 leading-relaxed">
  The 2022 recipe &mdash; keep the LLM in a box, let it emit text, and bolt on separate low&#8209;level controllers &mdash; leaves the most capable models blind to geometry.
  <span class="text-blue-200 font-semibold">The 2023 bet: put perception, and then action, inside the model itself.</span>
  </div>
</div>

<div class="mt-6 grid grid-cols-3 gap-4 text-center text-xs text-slate-400">
  <div class="border-t border-white/10 pt-3"><span class="text-slate-200 font-semibold">PaLM-E</span><br/>ground the input</div>
  <div class="border-t border-white/10 pt-3"><span class="text-slate-200 font-semibold">RT-2</span><br/>ground the output</div>
  <div class="border-t border-white/10 pt-3"><span class="text-slate-200 font-semibold">Voyager</span><br/>ground the loop</div>
</div>


---
layout: default
transition: slide-left
---

<div class="text-[11px] tracking-[0.3em] uppercase text-blue-400/70 mb-2">01 &middot; Context</div>

# Three papers, three entry points

<div class="grid grid-cols-3 gap-5 mt-8">

<div class="rounded-xl border border-blue-400/25 bg-blue-500/[0.07] p-5 flex flex-col">
  <div class="text-[10px] tracking-[0.2em] uppercase text-blue-300/80">Paper 01 &middot; Mar 2023</div>
  <div class="text-xl font-bold text-white mt-1">PaLM-E</div>
  <div class="text-[11px] text-slate-400 mb-3">Google &middot; 562B parameters</div>
  <div class="text-sm text-slate-300 leading-snug flex-1">
    An <span class="text-blue-200">embodied multimodal language model</span>: sensor data is injected into a pretrained LLM as tokens, and the model emits plans as text.
  </div>
  <div class="mt-4 pt-3 border-t border-white/10 text-[11px] text-slate-400">
    Contribution type<br/><span class="text-slate-200">a model &amp; a training recipe</span>
  </div>
</div>

<div class="rounded-xl border border-indigo-400/25 bg-indigo-500/[0.07] p-5 flex flex-col">
  <div class="text-[10px] tracking-[0.2em] uppercase text-indigo-300/80">Paper 02 &middot; Jul 2023</div>
  <div class="text-xl font-bold text-white mt-1">RT-2</div>
  <div class="text-[11px] text-slate-400 mb-3">Google DeepMind &middot; up to 55B</div>
  <div class="text-sm text-slate-300 leading-snug flex-1">
    A <span class="text-indigo-200">vision&#8209;language&#8209;action model</span>: robot actions are written as text tokens, so one network both answers questions and drives the arm.
  </div>
  <div class="mt-4 pt-3 border-t border-white/10 text-[11px] text-slate-400">
    Contribution type<br/><span class="text-slate-200">a general recipe (VLA)</span>
  </div>
</div>

<div class="rounded-xl border border-emerald-400/25 bg-emerald-500/[0.07] p-5 flex flex-col">
  <div class="text-[10px] tracking-[0.2em] uppercase text-emerald-300/80">Paper 03 &middot; May 2023</div>
  <div class="text-xl font-bold text-white mt-1">Voyager</div>
  <div class="text-[11px] text-slate-400 mb-3">NVIDIA &middot; Caltech &middot; UT Austin &middot; Stanford</div>
  <div class="text-sm text-slate-300 leading-snug flex-1">
    An <span class="text-emerald-200">open&#8209;ended embodied agent</span>: GPT&#8209;4 writes code, verifies it, and stores working skills in a growing library &mdash; no fine&#8209;tuning.
  </div>
  <div class="mt-4 pt-3 border-t border-white/10 text-[11px] text-slate-400">
    Contribution type<br/><span class="text-slate-200">an agent architecture</span>
  </div>
</div>

</div>

<div class="mt-7 text-sm text-slate-400 text-center">
Read together, they trace a single arc: <span class="text-slate-200">generic knowledge &rarr; grounded perception &rarr; grounded action &rarr; grounded self&#8209;improvement.</span>
</div>


---
layout: default
transition: slide-left
---

<div class="text-[11px] tracking-[0.3em] uppercase text-blue-400/70 mb-2">02 &middot; PaLM-E</div>

# Perception as a sentence

<div class="grid grid-cols-[1.05fr_1fr] gap-8 mt-5">

<div>
  <div class="text-sm text-slate-300 leading-relaxed">
  PaLM-E keeps the language model and changes the <em>input</em>. Images, robot states, and 3D scene representations are encoded into vectors with the same dimension as word embeddings, then interleaved with text to form a <span class="text-blue-200 font-semibold">&ldquo;multimodal sentence&rdquo;</span>.
  </div>

  <div class="mt-5 space-y-3 text-sm">
    <div class="flex gap-3">
      <div class="text-blue-400 font-mono text-xs pt-0.5">01</div>
      <div class="text-slate-300">A frozen&#8209;or&#8209;fine&#8209;tuned <span class="text-slate-100">PaLM</span> decoder does the reasoning &mdash; 8B, 62B, or 540B.</div>
    </div>
    <div class="flex gap-3">
      <div class="text-blue-400 font-mono text-xs pt-0.5">02</div>
      <div class="text-slate-300">An encoder maps one observation to <em>q</em> vectors; tokens land <span class="text-slate-100">dynamically</span> wherever the text puts them.</div>
    </div>
    <div class="flex gap-3">
      <div class="text-blue-400 font-mono text-xs pt-0.5">03</div>
      <div class="text-slate-300">The output is still <span class="text-slate-100">text</span> &mdash; an answer, or a plan that sequences low&#8209;level skills.</div>
    </div>
  </div>
</div>

<div class="rounded-xl border border-white/10 bg-slate-950/50 p-4">
  <div class="text-[10px] tracking-[0.2em] uppercase text-slate-500 mb-3">Input sequence</div>
  <div class="flex flex-wrap items-center gap-1.5 text-[13px] font-mono leading-relaxed">
    <span class="px-2 py-1 rounded bg-white/5 text-slate-300">Given</span>
    <span class="px-2 py-1 rounded bg-blue-500/25 text-blue-200 border border-blue-400/40">&lt;img&gt;</span>
    <span class="px-2 py-1 rounded bg-white/5 text-slate-300">Q: How to</span>
    <span class="px-2 py-1 rounded bg-white/5 text-slate-300">grasp</span>
    <span class="px-2 py-1 rounded bg-white/5 text-slate-300">the blue</span>
    <span class="px-2 py-1 rounded bg-white/5 text-slate-300">block?</span>
    <span class="px-2 py-1 rounded bg-white/5 text-slate-300">A:</span>
  </div>

  <div class="my-4 border-t border-dashed border-white/10"></div>

  <div class="text-[10px] tracking-[0.2em] uppercase text-slate-500 mb-2">Model output</div>
  <div class="text-[13px] text-slate-300 leading-relaxed font-mono">
    &ldquo;First grasp yellow block and place it on the table, then grasp the blue block.&rdquo;
  </div>

  <div class="mt-4 flex items-center gap-2 text-[11px] text-slate-500">
    <span class="w-2 h-2 rounded-full bg-blue-400"></span> modality token
    <span class="w-2 h-2 rounded-full bg-slate-500 ml-3"></span> text token
  </div>
</div>

</div>

<div class="mt-5 text-xs text-slate-500 border-l-2 border-blue-500/40 pl-3">
Key architectural claim: a 22B ViT plus a 540B LLM gives PaLM-E&#8209;562B &mdash; at the time, the largest vision&#8209;language model reported.
</div>
