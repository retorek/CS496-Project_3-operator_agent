# Operator agent: internship application tracker

A small Python agent orchestrated with LangGraph. It searches dummy internship
offers, reads them against a CV, maintains an in-memory tracker, and sends mock
applications. Both state-changing tools require human approval.

## Setup and run

Python 3.12 is recommended and was used for validation. In a VS Code PowerShell
terminal, from the project directory:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe run_demo.py
~~~

In VS Code, press Ctrl+Shift+P, choose **Python: Select Interpreter**, select
**Enter interpreter path**, and choose
~~~text
<project directory>\.venv\Scripts\python.exe
~~~
No virtual environment activation is needed for the commands above.

Other demo commands:

~~~powershell
# Scripted model: approve both writes automatically, using dummy data only.
.\.venv\Scripts\python.exe run_demo.py --yes

# Local model: Ollama must be running; each write prompts for human approval.
.\.venv\Scripts\python.exe run_demo.py --model llama3.1
~~~

The demo rejects combining --yes with --model. The default demo asks separately
before updating the tracker and before submitting the application.

## Layout

| File | Responsibility |
| --- | --- |
| agent/agent.py | StateGraph, shared state, limits, authorization, RunResult and JSONL logging |
| agent/llm.py | OllamaLLM and ScriptedLLM, both exposing complete(messages) |
| agent/tools.py | Four mock tools, in-memory tracker and duplicate submission protection |
| agent/schemas.py | Pydantic tool input schemas and readable errors |
| run_demo.py | CLI and human approval for exact actions and arguments |
| data/ | Dummy offers (o4 contains prompt injection) and a sample CV |
| tests/ | Regression, workflow, authorization, injection, demo and model interface tests |

## LangGraph workflow

The workflow uses the [LangGraph StateGraph API](https://docs.langchain.com/oss/python/langgraph/graph-api).
The model continues to return one JSON action per turn. No model adapter,
LangSmith account, persistence service, or cloud model is required.

~~~mermaid
flowchart TD
    START --> limits
    limits -->|continue| model
    limits -->|limit reached| END
    model --> parse
    parse -->|invalid or unknown action| limits
    parse -->|read tool| execute
    parse -->|write tool| approval
    parse -->|finish| finish
    approval -->|approved| execute
    approval -->|invalid or declined| limits
    approval -->|application cap| END
    execute -->|observation or tool error| limits
    execute -->|application cap| END
    finish --> END
~~~

- **limits** checks Python counters before the next model call.
- **model** calls complete(messages) and accounts for the reported token usage.
- **parse** accepts a JSON object with a string action and dictionary args.
  Only the four known tools and finish are accepted.
- **approval** validates write arguments and asks the human to authorize them.
- **execute** rechecks authorization and dispatches the tool. ToolError becomes a
  readable observation; offer contents are fenced as untrusted data.
- **finish** records the answer and ends the run.

AgentState holds messages, the raw reply, pending action and arguments, answer,
model-call count, tokens, successful submission count, steps, stop reason,
the approved request, declined requests, and the next route. Nodes return state
updates. Model output and tool output are never merged into internal graph state.
The model, tools, approval callback, and a snapshot of Config are held separately
in Python closures. Each run gets a fresh graph and fresh state.

## Public interface and approval

The positional parameters and returned RunResult remain available:

~~~python
from agent.agent import Config, run_agent

def approve(action, args):
    # Show all arguments to the human before returning True.
    print(action, args)
    return input("Approve this exact action? Type yes: ").strip().lower() == "yes"

result = run_agent(task, cv, llm, tools, approve, Config(), log_path="logs/run.jsonl")
print(result.answer, result.stop_reason, result.tokens, result.steps)
~~~

The intentional callback change is from approve(offer_id, letter) to
approve(action, args), because both update_tracker and submit_application
require approval. Read-only search_jobs and read_offer do not prompt.

Approval must return the boolean True. Other values deny the action; exceptions
propagate and prevent execution. The callback receives a deep copy of the pending
arguments. Authorization is bound to a canonical representation of the exact tool
name and every argument. The dispatcher verifies that match again before any
write, and authorization is cleared after each action. Invalid write schemas do
not prompt. An identical declined action is not prompted again within the run;
a revised action needs its own approval.

For existing submission callbacks, use the explicit adapter:

~~~python
from agent.agent import legacy_approval

approve = legacy_approval(old_approve)
# old_approve(offer_id, letter) still reviews submissions.
# All tracker writes are denied until a tracker approval callback is supplied.

approve = legacy_approval(old_approve, tracker_approve=review_tracker)
# review_tracker(action, args) must independently return True for tracker writes.
~~~

The tool call interface, model complete(messages) interface, RunResult fields,
and JSONL step fields remain unchanged. MockTools.validate now supports both
write tools. Tools must raise ToolError when an operation fails; a submission
that returns normally counts as successful, matching the existing contract.

## Python limits

Config controls application policy independently of LangGraph's recursion limit:

| Setting | Meaning |
| --- | --- |
| max_steps | Maximum model calls, including invalid replies; graph nodes do not count |
| max_applications | Maximum successful submissions; tracker updates do not consume slots |
| max_tokens | Stop before another model call when reported cumulative usage reaches the budget |

Stop reasons remain done, max_steps, max_applications, and budget. Reaching the
submission cap stops immediately after the successful tool action. Failed or
duplicate submissions do not consume slots. A zero value for any limit stops
before the first model call. Limits must be non-negative integers.

Token counts include prompt and completion tokens as reported by the model
adapter. As in the original loop, the last completion is processed and can
overshoot max_tokens because its usage is only known afterward. This is a guard
against further calls, not a strict generation-token ceiling. Invalid negative or
non-integer usage fails before the generated action is processed.

The recursion limit is set above the maximum expected node count for the
configured model-call limit. It is a framework safeguard; increasing it does not
increase the Python limits.

## Tests and security scope

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest tests/test_security.py -q
~~~

Tests use ScriptedLLM and an HTTP stub for OllamaLLM; no Ollama server or network
is needed. They cover the complete demo, logs, all stop reasons, zero limits,
a large framework recursion limit, failed and duplicate submissions, callback
compatibility, isolated runs, malformed actions, exact write approvals,
approval failures and mutations, stale approval, forged state, prompt injection,
and CLI auto-approval restrictions.

The approval guarantee applies to calls made through run_agent. MockTools.call
and its Python implementation are trusted code; directly invoking tools outside
the workflow does not enforce human approval. Do not expose private graph state
or dispatch helpers as an API for untrusted callers. The approval callback is a
trusted human interface; a caller that supplies an always-True callback chooses
automatic authorization.

Offer fencing helps identify untrusted text but cannot guarantee model obedience.
The tool allowlist, dispatcher authorization, and Python limits provide the
structural controls even if the model follows injected instructions. A model can
still write an inaccurate final summary, so tool results are the record of
completed actions. JSONL logs include tool arguments, offer text, and letters;
handle them appropriately before using real personal data.

## Future work

- Replace MockTools with real tools that preserve call, validate and ToolError contracts.
- Add a separate cover-letter node if the project requires a dedicated writing step.
- Add persistence or tracing only when needed; resuming real writes would also
  require durable authorization and idempotency beyond this in-memory demo.
