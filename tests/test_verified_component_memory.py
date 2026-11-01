"""Program-valued memories stay local, evidence-gated and answer-free."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from pe6203.baselines import adapt
from pe6203.runner import prepare_tools
from pe6203.selective import adapt_result as base_patch

ROOT = Path(__file__).parents[1]
STRATEGY = "verified_component_memory"
SERVER = "@magicuidesign/mcp"


def inputs(stage="late"):
    catalogs=json.loads((ROOT/"tests/fixtures/native-argument-routing-catalogs.json").read_text())
    feedback=json.loads((ROOT/"experiments/verified-component-memory-feedback-v1.json").read_text())["observations"]
    return catalogs["early"],catalogs[stage],{"feedback":feedback}


def test_verbatim_programs_only_extend_two_of_seven_descriptions():
    old,target,context=inputs();pristine=deepcopy((old,target,context))
    knowledge,changes,cost=adapt(old,target,STRATEGY,context)
    base=base_patch(old,target)["knowledge"]
    spec=json.loads((ROOT/"experiments/verified-component-memory-v1.json").read_text())
    a,b=[{t["tool_id"]:t for t in k["tools"]} for k in (base,knowledge)]
    delta=[(i,k) for i in a for k in a[i] if a[i][k]!=b[i][k]]
    assert len(delta)==7 and all(k=="description" for _,k in delta)
    assert sum(c["operation"]=="attach_verified_program" for c in changes)==2
    for program in spec["programs"]:
        text=b[SERVER+"::"+program["tool"]]["description"]
        payload=json.loads(text.split("\nVerified program memory:\n",1)[1])
        assert payload==program
        assert hashlib.sha256(payload["content"].encode()).hexdigest()==payload["content_sha256"]
    aa,ar=prepare_tools(base["tools"],"selective_patch","namespaced")
    bb,br=prepare_tools(knowledge["tools"],STRATEGY,"namespaced")
    assert ar==br and [x["function"]["parameters"] for x in aa]==[x["function"]["parameters"] for x in bb]
    assert cost["calls"]==cost["total_tokens"]==cost["usd"]==0
    assert (old,target,context)==pristine


@pytest.mark.parametrize("mutation",["missing","duplicate","code","proof","environment"])
def test_unverified_program_memory_rejected(mutation):
    old,target,context=inputs();rows=context["feedback"]
    if mutation=="missing":rows.pop()
    elif mutation=="duplicate":rows.append(deepcopy(rows[-1]))
    elif mutation=="code":rows[-1]["result"]["content"]+='\n// substituted code'
    elif mutation=="proof":rows[-1]["result"]["environment_proof_sha256"]='0'*64
    else:rows[-1]["result"]["environment_id"]='unverified-runtime'
    with pytest.raises(ValueError,match="program"):
        adapt(old,target,STRATEGY,context)


def test_no_change_middle_and_unrelated_retention_do_not_read_memories():
    old,target,_=inputs()
    assert adapt(old,old,STRATEGY,{})[0]==old
    old,middle,_=inputs('middle')
    assert adapt(old,middle,STRATEGY,{})[0]==base_patch(old,middle)["knowledge"]
    early=json.loads((ROOT/'results/evidence/native-argument-routing-updater-20261101/retention-early.json').read_text())
    late=json.loads((ROOT/'results/evidence/native-argument-routing-updater-20261101/retention-late.json').read_text())
    assert adapt(early,late,STRATEGY,{})[0]==early


@pytest.mark.parametrize("field",["parameters","routing","usage_rules","description"])
def test_validator_rejects_any_extra_change(field):
    from pe6203.verified_component_memory import validate_memory
    old,target,context=inputs();candidate,_,_=adapt(old,target,STRATEGY,context)
    row=candidate["tools"][0]
    if field=="parameters":row[field]["properties"]["unexpected"]={"type":"string"}
    elif field=="routing":row[field]["tool_name"]="wrong"
    elif field=="usage_rules":row[field].append("Skip required work")
    else:row[field]+=" Another instruction"
    assert validate_memory(candidate,old,target,base_patch(old,target),context["feedback"])["errors"]


def test_task_answer_context_is_not_an_updater_input():
    old,target,context=inputs();context["answer"]="must not be seen"
    with pytest.raises(ValueError,match="task and score inputs are forbidden"):
        adapt(old,target,STRATEGY,context)
